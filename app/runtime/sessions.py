"""
Runtime: create an Anthropic session and relay SSE events as async dicts.

The Anthropic SDK stream is synchronous/blocking. We run it in a background
thread and bridge to the async caller via a queue, so FastAPI's event loop
is never blocked.

SSE event dict format:
    {type: "token",      content: str}
    {type: "tool_start", name: str, input: dict}
    {type: "tool_end",   output: str}
    {type: "done"}
    {type: "error",      message: str}
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
from typing import Any, AsyncGenerator

import anthropic

from app.client import get_client
from app.config import get_settings
from app.models.chat import FileAttachment
from app.tools import execute as execute_tool

logger = logging.getLogger(__name__)

_STREAM_TIMEOUT = anthropic.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
_SENTINEL = object()


def _build_content(message: str, attachments: list[FileAttachment]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": message}]
    for att in attachments:
        content.append({"type": att.content_type, "source": {"type": "file", "file_id": att.file_id}})
    return content


def _stream_in_thread(
    message: str,
    user_id: str,
    out: queue.Queue,
    session_id: str,
    attachments: list[FileAttachment],
) -> None:
    """Blocking stream loop — runs in a daemon thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        client = get_client()

        idle = False
        first = True
        pending_tools: dict[str, Any] = {}  # event_id → agent.custom_tool_use event
        responded_tool_ids: set[str] = set()  # event_ids we've already sent results for

        while not idle:
            try:
                with client.beta.sessions.events.stream(
                    session_id, timeout=_STREAM_TIMEOUT
                ) as event_stream:
                    if first:
                        client.beta.sessions.events.send(
                            session_id,
                            events=[
                                {
                                    "type": "user.message",
                                    "content": _build_content(message, attachments),
                                }
                            ],
                        )
                        first = False

                    for event in event_stream:
                        raw = str(event)
                        logger.debug("[event] %s: %s", event.type, raw[:50])
                        if get_settings().debug:
                            out.put({"type": "token", "content": f"\n[EVT] {event.type} | {raw}\n"})

                        match event.type:
                            case "agent.message":
                                for block in event.content:
                                    if block.type == "text" and block.text:
                                        out.put({"type": "token", "content": block.text})
                                    elif file_id := getattr(block, "file_id", None):
                                        out.put({
                                            "type": "file",
                                            "file_id": file_id,
                                            "filename": getattr(block, "filename", None) or getattr(block, "name", None),
                                            "mime_type": getattr(block, "mime_type", None) or getattr(block, "media_type", None),
                                        })

                            case "agent.mcp_tool_use":
                                # Workaround: Anthropic beta backend does not honour
                                # always_allow for mcp_toolset — send explicit approval.
                                perm = getattr(event, "evaluated_permission", None)
                                if perm in (None, "ask"):
                                    try:
                                        client.beta.sessions.events.send(
                                            session_id,
                                            events=[{
                                                "type": "user.tool_confirmation",
                                                "tool_use_id": event.id,
                                                "result": "allow",
                                            }],
                                        )
                                    except Exception as conf_exc:
                                        logger.warning("[mcp_tool_use] tool_confirmation failed: %s", conf_exc)
                                out.put({
                                    "type": "tool_start",
                                    "tool_call_id": event.id,
                                    "name": getattr(event, "name", ""),
                                    "input": getattr(event, "input", {}),
                                })

                            case "agent.mcp_tool_result":
                                out.put({
                                    "type": "tool_end",
                                    "tool_call_id": getattr(event, "mcp_tool_use_id", ""),
                                    "output": str(getattr(event, "content", "")),
                                })

                            case "agent.custom_tool_use":
                                logger.info("[custom_tool_use] id=%r name=%s", event.id, event.name)
                                pending_tools[event.id] = event
                                out.put({
                                    "type": "tool_start",
                                    "tool_call_id": event.id,
                                    "name": event.name,
                                    "input": event.input,
                                })

                            case "session.status_idle":
                                if event.stop_reason.type == "requires_action":
                                    results = []
                                    confirmations = []
                                    logger.info("[requires_action] event_ids=%r pending_keys=%r responded=%r", event.stop_reason.event_ids, list(pending_tools.keys()), responded_tool_ids)
                                    for event_id in event.stop_reason.event_ids:
                                        if event_id in responded_tool_ids:
                                            # Already handled in a previous stream iteration — skip
                                            logger.info("[requires_action] skipping already-responded id=%r", event_id)
                                            continue
                                        if event_id not in pending_tools:
                                            # Not a custom tool — send MCP confirmation
                                            confirmations.append({
                                                "type": "user.tool_confirmation",
                                                "tool_use_id": event_id,
                                                "result": "allow",
                                            })
                                    if confirmations:
                                        try:
                                            client.beta.sessions.events.send(session_id, events=confirmations)
                                            logger.info("[requires_action] sent %d tool_confirmation(s)", len(confirmations))
                                        except Exception as ce:
                                            logger.warning("[requires_action] tool_confirmation failed: %s", ce)
                                        break  # restart stream to get results
                                    for event_id in event.stop_reason.event_ids:
                                        if event_id in responded_tool_ids:
                                            continue
                                        tool_event = pending_tools.pop(event_id, None)
                                        if tool_event:
                                            try:
                                                result = loop.run_until_complete(
                                                    execute_tool(tool_event.name, tool_event.input, user_id)
                                                )
                                            except Exception as tool_exc:
                                                logger.error("tool execution error [%s]: %s", tool_event.name, tool_exc)
                                                result = {"error": str(tool_exc)}
                                            out.put({"type": "tool_end", "tool_call_id": event_id, "output": json.dumps(result)})
                                            results.append({
                                                "type": "user.custom_tool_result",
                                                "custom_tool_use_id": event_id,
                                                "content": [{"type": "text", "text": json.dumps(result)}],
                                            })
                                    if results:
                                        client.beta.sessions.events.send(session_id, events=results)
                                        responded_tool_ids.update(r["custom_tool_use_id"] for r in results)
                                    # Don't break — stream stays open, agent continues after receiving results
                                else:
                                    out.put({"type": "done"})
                                    idle = True
                                    break

                            case "session.error" | "error":
                                error = getattr(event, "error", None)
                                if error:
                                    error_type = getattr(error, "type", "unknown")
                                    error_msg = getattr(error, "message", str(error))
                                    retry = getattr(error, "retry_status", None)
                                    retry_type = getattr(retry, "type", None) if retry else None
                                    if error_type == "model_rate_limited_error":
                                        msg = "模型当前繁忙，请稍后重试"
                                        if retry_type == "exhausted":
                                            msg = "模型当前繁忙，已多次重试仍失败，请稍后重试"
                                    else:
                                        msg = f"{error_type}: {error_msg}"
                                else:
                                    msg = str(event)
                                out.put({"type": "error", "message": msg})
                                idle = True
                                break

                            case "agent.thinking":
                                out.put({"type": "thinking"})

                            case _:
                                logger.info("[event] unhandled: %s", raw[:50])

            except anthropic.APITimeoutError:
                out.put({"type": "error", "message": "stream timeout — tool took >60s"})
                idle = True

            if not idle:
                time.sleep(1)

    except Exception as exc:
        out.put({"type": "error", "message": str(exc)})
    finally:
        # Drain pending tasks (e.g. Gemini client aclose) before closing loop
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()
        out.put(_SENTINEL)


async def stream(
    session_id: str,
    message: str,
    user_id: str,
    attachments: list[FileAttachment] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async generator — yields SSE event dicts, never blocks the event loop."""
    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(message, user_id, out, session_id, attachments or []),
        daemon=True,
    )
    t.start()

    loop = asyncio.get_running_loop()
    while True:
        event = await loop.run_in_executor(None, out.get)
        if event is _SENTINEL:
            break
        yield event

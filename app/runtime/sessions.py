"""
Runtime: relay Anthropic managed-agent session events as async SSE dicts.

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
import re
from typing import Any, AsyncGenerator

import anthropic

from app.client import get_async_client
from app.config import get_settings
from app.models.chat import FileAttachment
from app.tools import execute as execute_tool

logger = logging.getLogger(__name__)

_STREAM_TIMEOUT = anthropic.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)


_UPLOADS_DIR = "/mnt/session/uploads"


def _build_content(message: str, attachments: list[FileAttachment], mount_names: dict[str, str]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": message}]
    for att in attachments:
        content.append({"type": att.content_type, "source": {"type": "file", "file_id": att.file_id}})
    if attachments:
        paths = "\n".join(
            f"- {mount_names.get(att.file_id, att.filename or att.file_id)} → {_UPLOADS_DIR}/{mount_names.get(att.file_id, att.filename or att.file_id)}"
            for att in attachments
        )
        content.append({"type": "text", "text": f"\n[Attached files in sandbox:]\n{paths}"})
    return content


async def _mount_attachments(session_id: str, attachments: list[FileAttachment]) -> dict[str, str]:
    """Mount uploaded files into the session sandbox. Returns {file_id: actual_filename}.
    Retries with _1, _2 suffix on path conflicts (different files with same name).
    Same file_id conflicts (re-sent file) are silently skipped — file is already mounted."""
    client = get_async_client()

    async def _mount_one(att: FileAttachment) -> tuple[str, str]:
        base_name = att.filename or att.file_id
        stem, _, ext = base_name.rpartition(".")
        if not stem:
            stem, ext = base_name, ""
        else:
            ext = "." + ext

        for i in range(20):
            actual = f"{stem}_{i}{ext}" if i > 0 else base_name
            try:
                await client.beta.sessions.resources.add(
                    session_id,
                    type="file",
                    file_id=att.file_id,
                    mount_path=f"{_UPLOADS_DIR}/{actual}",
                )
                logger.info("[mount] file_id=%s → %s/%s", att.file_id, _UPLOADS_DIR, actual)
                return att.file_id, actual
            except anthropic.BadRequestError as exc:
                msg = str(exc)
                if "overlapping mount paths" in msg:
                    if i == 0:
                        # Could be same file already mounted — skip without renaming
                        logger.debug("[mount] path conflict file_id=%s name=%s, trying suffix", att.file_id, actual)
                        continue
                    logger.debug("[mount] path conflict file_id=%s trying %s", att.file_id, actual)
                    continue
                logger.warning("[mount] failed file_id=%s: %s", att.file_id, exc)
                return att.file_id, base_name
            except Exception as exc:
                logger.warning("[mount] failed file_id=%s: %s", att.file_id, exc)
                return att.file_id, base_name

        logger.warning("[mount] gave up after 20 retries file_id=%s", att.file_id)
        return att.file_id, base_name

    results = await asyncio.gather(*[_mount_one(att) for att in attachments])
    return dict(results)


async def stream(
    session_id: str,
    message: str,
    user_id: str,
    attachments: list[FileAttachment] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async generator — yields SSE event dicts, never blocks the event loop."""
    print(f"[stream] session_id={session_id!r} user_id={user_id!r} message={message!r} attachments={attachments!r}")
    client = get_async_client()
    pending_tools: dict[str, Any] = {}  # event_id → agent.custom_tool_use event
    sent_results: set[str] = set()      # IDs we already sent results for
    mcp_tool_ids: set[str] = set()      # IDs from agent.mcp_tool_use (Anthropic-executed)

    mount_names: dict[str, str] = {}
    if attachments:
        mount_names = await _mount_attachments(session_id, attachments)

    content = _build_content(message, attachments or [], mount_names)
    logger.info("[send] content=%s", content)

    async with await client.beta.sessions.events.stream(
        session_id, timeout=_STREAM_TIMEOUT
    ) as event_stream:
        try:
            await client.beta.sessions.events.send(
                session_id,
                events=[{"type": "user.message", "content": content}],
            )
        except anthropic.BadRequestError as exc:
            if "waiting on responses to events" in str(exc):
                # Session is idle but stuck in requires_action because a previous connection
                # dropped before tool results were sent. user.interrupt does NOT clear this
                # state — we must send dummy custom_tool_result events for all pending IDs,
                # then retry the user message.
                pending_ids = re.findall(r'sevt_\w+', str(exc))
                logger.warning("[send] session stuck requires_action, pending=%r, resolving...", pending_ids)
                try:
                    if pending_ids:
                        dummy_results = [
                            {
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": eid,
                                "content": [{"type": "text", "text": json.dumps({"error": "Connection was interrupted; retrying."})}],
                            }
                            for eid in pending_ids
                        ]
                        await client.beta.sessions.events.send(session_id, events=dummy_results)
                    else:
                        # No parseable IDs — fall back to interrupt
                        await client.beta.sessions.events.send(
                            session_id, events=[{"type": "user.interrupt"}]
                        )
                    await client.beta.sessions.events.send(
                        session_id,
                        events=[{"type": "user.message", "content": content}],
                    )
                except Exception as retry_exc:
                    logger.error("[send] recovery failed: %s", retry_exc)
                    yield {"type": "error", "message": f"会话恢复失败，请刷新重试: {retry_exc}"}
                    return
            else:
                logger.error("[send] bad request: %s", exc)
                yield {"type": "error", "message": str(exc)}
                return
        except anthropic.NotFoundError as exc:
            logger.error("[send] session not found (expired?): %s", exc)
            yield {"type": "error", "message": "会话已过期，请开启新对话"}
            return
        except anthropic.RateLimitError as exc:
            logger.error("[send] rate limited: %s", exc)
            yield {"type": "error", "message": "请求频率过高，请稍后重试"}
            return
        except anthropic.APITimeoutError as exc:
            logger.error("[send] timeout: %s", exc)
            yield {"type": "error", "message": "请求超时，请稍后重试"}
            return
        except anthropic.APIError as exc:
            logger.error("[send] API error: %s", exc)
            yield {"type": "error", "message": str(exc)}
            return

        async for event in event_stream:
            raw = str(event)
            logger.debug("[event] %s: %s", event.type, raw[:50])
            if get_settings().debug:
                yield {"type": "token", "content": f"\n[EVT] {event.type} | {raw}\n"}

            match event.type:
                case "agent.message":
                    for block in event.content:
                        if block.type == "text" and block.text:
                            yield {"type": "token", "content": block.text}
                        elif file_id := getattr(block, "file_id", None):
                            yield {
                                "type": "file",
                                "file_id": file_id,
                                "filename": getattr(block, "filename", None) or getattr(block, "name", None),
                                "mime_type": getattr(block, "mime_type", None) or getattr(block, "media_type", None),
                            }

                case "agent.tool_use":
                    yield {
                        "type": "tool_start",
                        "tool_call_id": event.id,
                        "name": getattr(event, "name", ""),
                        "input": getattr(event, "input", {}),
                    }

                case "agent.tool_result":
                    raw_content = getattr(event, "content", "")
                    if isinstance(raw_content, list):
                        output = "\n".join(
                            getattr(block, "text", "")
                            for block in raw_content
                            if getattr(block, "type", "") == "text"
                        )
                    else:
                        output = str(raw_content)
                    yield {
                        "type": "tool_end",
                        "tool_call_id": getattr(event, "tool_use_id", ""),
                        "output": output,
                    }

                case "agent.mcp_tool_use":
                    mcp_tool_ids.add(event.id)
                    yield {
                        "type": "tool_start",
                        "tool_call_id": event.id,
                        "name": getattr(event, "name", ""),
                        "input": getattr(event, "input", {}),
                    }

                case "agent.mcp_tool_result":
                    raw_content = getattr(event, "content", "")
                    logger.info("[mcp_tool_result] content type=%s value=%r", type(raw_content).__name__, str(raw_content)[:300])
                    if isinstance(raw_content, list):
                        output = "\n".join(
                            getattr(block, "text", "")
                            for block in raw_content
                            if getattr(block, "type", "") == "text"
                        )
                    else:
                        output = str(raw_content)
                    yield {
                        "type": "tool_end",
                        "tool_call_id": getattr(event, "mcp_tool_use_id", ""),
                        "output": output,
                    }

                case "agent.custom_tool_use":
                    logger.info("[custom_tool_use] id=%r name=%s", event.id, event.name)
                    pending_tools[event.id] = event
                    yield {
                        "type": "tool_start",
                        "tool_call_id": event.id,
                        "name": event.name,
                        "input": event.input,
                    }

                case "session.status_idle":
                    if event.stop_reason.type == "requires_action":
                        logger.info("[requires_action] event_ids=%r", event.stop_reason.event_ids)

                        # Compute missed_ids BEFORE popping from pending_tools.
                        # Exclude IDs we already sent results for — Anthropic fires
                        # intermediate requires_action as it processes each result
                        # in the batch one by one, so those IDs are legitimately handled.
                        missed_ids = [
                            eid
                            for eid in event.stop_reason.event_ids
                            if eid not in pending_tools and eid not in sent_results and eid not in mcp_tool_ids
                        ]
                        to_execute = [
                            (eid, pending_tools.pop(eid))
                            for eid in event.stop_reason.event_ids
                            if eid in pending_tools
                        ]

                        if missed_ids:
                            error_events = [
                                {
                                    "type": "user.custom_tool_result",
                                    "custom_tool_use_id": eid,
                                    "content": [{"type": "text", "text": json.dumps({"error": "Tool call was not received by the client; please retry."})}],
                                }
                                for eid in missed_ids
                            ]
                            try:
                                await client.beta.sessions.events.send(session_id, events=error_events)
                                logger.warning("[requires_action] sent error result for %d missed tool(s): %r", len(missed_ids), missed_ids)
                            except Exception as ce:
                                logger.warning("[requires_action] missed tool error result send failed: %s", ce)

                        if to_execute:
                            tool_inputs: dict[str, dict] = {eid: te.input for eid, te in to_execute}

                            async def _run_one(eid: str, te: Any) -> tuple[str, str, dict]:
                                try:
                                    return eid, te.name, await execute_tool(te.name, te.input, user_id, session_id=session_id)
                                except Exception as exc:
                                    logger.error("tool execution error [%s]: %s", te.name, exc)
                                    return eid, te.name, {"error": str(exc)}

                            tool_results = await asyncio.gather(*[_run_one(eid, te) for eid, te in to_execute])
                            results = []
                            for eid, tool_name, result in tool_results:
                                sent_results.add(eid)
                                yield {"type": "tool_end", "tool_call_id": eid, "output": json.dumps(result)}
                                # Emit a file event so the frontend renders a download card.
                                if tool_name == "download_file" and result.get("file_id"):
                                    yield {
                                        "type": "file",
                                        "file_id": result["file_id"],
                                        "filename": result.get("filename"),
                                        "mime_type": result.get("mime_type"),
                                    }
                                # Emit a preview event so the frontend renders an image review card.
                                if tool_name == "show_post_preview" and result.get("ok"):
                                    yield {
                                        "type": "preview",
                                        "slides": result.get("slides", []),
                                        "caption": result.get("caption", ""),
                                        "hashtags": result.get("hashtags", []),
                                    }
                                results.append({
                                    "type": "user.custom_tool_result",
                                    "custom_tool_use_id": eid,
                                    "content": [{"type": "text", "text": json.dumps(result)}],
                                })
                            try:
                                await client.beta.sessions.events.send(session_id, events=results)
                            except Exception as send_exc:
                                logger.error("[requires_action] failed to send tool results: %s", send_exc)
                                yield {"type": "error", "message": f"工具结果发送失败: {send_exc}"}
                                return
                        # stream stays open — Anthropic continues on the same connection

                    else:
                        yield {"type": "done"}
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
                    yield {"type": "error", "message": msg}
                    break

                case "agent.thinking":
                    yield {"type": "thinking"}

                case _:
                    logger.info("[event] unhandled: %s", raw[:50])

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
import queue
import threading
import time
from typing import Any, AsyncGenerator

import httpx

from app.client import get_client
from app.tools import execute as execute_tool

_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
_SENTINEL = object()


def _stream_in_thread(
    message: str,
    user_id: str,
    out: queue.Queue,
    session_id: str,
) -> None:
    """Blocking stream loop — runs in a daemon thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        client = get_client()

        idle = False
        first = True
        pending_tools: dict[str, Any] = {}  # event_id → agent.custom_tool_use event

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
                                    "content": [{"type": "text", "text": message}],
                                }
                            ],
                        )
                        first = False

                    for event in event_stream:
                        match event.type:
                            case "agent.message":
                                for block in event.content:
                                    if block.type == "text" and block.text:
                                        out.put({"type": "token", "content": block.text})

                            case "agent.mcp_tool_use":
                                out.put({
                                    "type": "tool_start",
                                    "name": getattr(event, "name", ""),
                                    "input": getattr(event, "input", {}),
                                })

                            case "agent.mcp_tool_result":
                                out.put({
                                    "type": "tool_end",
                                    "output": str(getattr(event, "content", "")),
                                })

                            case "agent.custom_tool_use":
                                pending_tools[event.id] = event
                                out.put({
                                    "type": "tool_start",
                                    "name": event.name,
                                    "input": event.input,
                                })

                            case "session.status_idle":
                                if event.stop_reason.type == "requires_action":
                                    results = []
                                    for event_id in event.stop_reason.event_ids:
                                        tool_event = pending_tools.pop(event_id, None)
                                        if tool_event:
                                            result = loop.run_until_complete(
                                                execute_tool(tool_event.name, tool_event.input, user_id)
                                            )
                                            out.put({"type": "tool_end", "output": json.dumps(result)})
                                            results.append({
                                                "type": "user.custom_tool_result",
                                                "custom_tool_use_id": event_id,
                                                "content": [{"type": "text", "text": json.dumps(result)}],
                                            })
                                    if results:
                                        client.beta.sessions.events.send(session_id, events=results)
                                    break  # restart stream loop
                                else:
                                    out.put({"type": "done"})
                                    idle = True
                                    break

                            case "session.error" | "error":
                                out.put({"type": "error", "message": str(event)})
                                idle = True
                                break

            except httpx.ReadTimeout:
                out.put({"type": "error", "message": "stream timeout — tool took >60s"})
                idle = True

            if not idle:
                time.sleep(1)

    except Exception as exc:
        out.put({"type": "error", "message": str(exc)})
    finally:
        loop.close()
        out.put(_SENTINEL)


def create_session(agent_id: str, env_id: str) -> str:
    """Create a new Anthropic session, return its ID. Call once per conversation."""
    client = get_client()
    session = client.beta.sessions.create(agent=agent_id, environment_id=env_id)
    return session.id


async def stream(
    session_id: str,
    message: str,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """Async generator — yields SSE event dicts, never blocks the event loop."""
    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(message, user_id, out, session_id),
        daemon=True,
    )
    t.start()

    loop = asyncio.get_running_loop()
    while True:
        event = await loop.run_in_executor(None, out.get)
        if event is _SENTINEL:
            break
        yield event

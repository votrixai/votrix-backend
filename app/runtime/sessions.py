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
import queue
import threading
import time
from typing import AsyncGenerator

import httpx

from app.client import get_client

_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
_SENTINEL = object()


def _stream_in_thread(
    agent_id: str,
    env_id: str,
    message: str,
    out: queue.Queue,
) -> None:
    """Blocking stream loop — runs in a daemon thread."""
    try:
        client = get_client()

        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
        )

        idle = False
        first = True

        while not idle:
            try:
                with client.beta.sessions.events.stream(
                    session.id, timeout=_STREAM_TIMEOUT
                ) as event_stream:
                    if first:
                        client.beta.sessions.events.send(
                            session.id,
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

                            case "session.status_idle":
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
        out.put(_SENTINEL)


async def stream(
    agent_id: str,
    env_id: str,
    message: str,
) -> AsyncGenerator[dict, None]:
    """Async generator — yields SSE event dicts, never blocks the event loop."""
    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(agent_id, env_id, message, out),
        daemon=True,
    )
    t.start()

    loop = asyncio.get_event_loop()
    while True:
        event = await loop.run_in_executor(None, out.get)
        if event is _SENTINEL:
            break
        yield event

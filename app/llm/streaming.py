"""SSE event formatting for FastAPI StreamingResponse.

Converts LangGraph's astream_events (v2) into the Server-Sent Events format
consumed by the frontend.

Event types:
  {"type": "message_chunk", "content": "..."}     — LLM token
  {"type": "tool_call", "tool": "...", "input": {}} — tool invocation started
  {"type": "tool_result", "tool": "...", "output": "..."} — tool finished
  {"type": "done"}                                 — graph completed
  {"type": "error", "message": "..."}              — unrecoverable error
"""

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)


async def stream_graph_events(
    graph,
    input_state: dict,
    config: dict,
) -> AsyncIterator[str]:
    """Stream graph execution as Server-Sent Events.

    Each yielded string is formatted as: "data: {json}\\n\\n"
    Wraps the entire stream in try/except — errors become error events,
    never crash the response stream.
    """
    try:
        async for event in graph.astream_events(input_state, config=config, version="v2"):
            payload = _format_stream_event(event)
            if payload is not None:
                yield f"data: {json.dumps(payload)}\n\n"
    except Exception as e:
        logger.error(f"Graph stream error: {type(e).__name__}: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def _format_stream_event(event: dict) -> dict | None:
    """Convert a single astream_events event to our SSE payload schema.

    Maps:
      "on_chat_model_stream" → message_chunk
      "on_tool_start"        → tool_call
      "on_tool_end"          → tool_result
      everything else        → None (skip)
    """
    kind = event.get("event")

    if kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        if not chunk:
            return None
        content = getattr(chunk, "content", None)
        if not content:
            return None

        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Anthropic-style content blocks
            text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            return None

        return {"type": "message_chunk", "content": text} if text else None

    if kind == "on_tool_start":
        return {
            "type": "tool_call",
            "tool": event.get("name"),
            "input": event.get("data", {}).get("input") or {},
        }

    if kind == "on_tool_end":
        output = event.get("data", {}).get("output")
        return {
            "type": "tool_result",
            "tool": event.get("name"),
            "output": str(output) if output is not None else "",
        }

    return None

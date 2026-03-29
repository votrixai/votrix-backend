"""POST /chat/stream — HTTP streaming chat (Vercel AI SDK data stream protocol).

Migrated from ai-core chat_stream_router.py. Uses org_id instead of host_id.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, ToolMessage

from app.context.build_context import build_assistant_context_for_stream
from app.context.assistant_context import AssistantContext
from app.db.queries import sessions as sessions_q
from app.llm.graph import ChatLangGraphHandler
from app.models.chat import ChatStreamRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _ds_part(code: str, value: Any) -> str:
    return f"{code}:{json.dumps(value, ensure_ascii=False)}\n"


async def run_one_chat_turn(
    ctx: AssistantContext,
    user_text: str,
    chat_handler: ChatLangGraphHandler,
    request_id: int = 0,
    on_partial_reply: Optional[Callable[[str], Awaitable[None]]] = None,
    on_tool_event: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> str:
    """Run one LLM turn. Shared by stream and (future) WS handler. Returns reply_text."""
    intermediate_steps = []
    try:
        reply_text, intermediate_steps = await chat_handler.ainvoke(
            ctx=ctx,
            user_text=user_text,
            request_id=request_id,
            on_partial_reply=on_partial_reply,
            on_tool_event=on_tool_event,
        )
    except Exception as e:
        logger.error("LLM turn failed: %s", e)
        reply_text = "Sorry, something went wrong. Please try again."

    reply_text = reply_text or ""

    # Record to ChatManager
    try:
        cm = ctx.chat_manager
        cm.record_user_message(request_id=request_id, user_message=user_text)
        for msg in intermediate_steps:
            if isinstance(msg, AIMessage):
                tc = [
                    {"id": t.get("id", "") if isinstance(t, dict) else getattr(t, "id", ""),
                     "name": t.get("name", "") if isinstance(t, dict) else getattr(t, "name", ""),
                     "args": t.get("args", {}) if isinstance(t, dict) else getattr(t, "args", {}),
                     "type": "tool_call"}
                    for t in (msg.tool_calls or [])
                ]
                cm.record_agent_message(request_id=request_id, ai_message=msg.content if isinstance(msg.content, str) else "", tool_calls=tc or None)
            elif isinstance(msg, ToolMessage):
                cm.record_tool_message(request_id=request_id, tool_call_id=msg.tool_call_id or "", func_name="", content=msg.content or "")
        cm.record_agent_message(request_id=request_id, ai_message=reply_text, tool_calls=None)
    except Exception as e:
        logger.error("ChatManager replay failed: %s", e)

    return reply_text


async def _stream_chat_ds(
    ctx: AssistantContext,
    user_text: str,
    message_id: str,
) -> AsyncGenerator[str, None]:
    """Run LangGraph and yield Vercel AI SDK data stream lines."""
    usage_empty = {"promptTokens": 0, "completionTokens": 0}
    yield _ds_part("f", {"messageId": message_id})

    queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
    reply_holder: List[str] = []
    tool_events_seen: List[bool] = [False]
    seq_counter: List[int] = [1]
    ingest_tasks: List[asyncio.Task] = []

    async def on_partial(text: str) -> None:
        await queue.put(_ds_part("0", text))

    async def on_tool_event(event_type_name: str, event_title: str, body_json: str) -> None:
        et = "ai_agent_message" if event_type_name == "ai_agent" else "tool_result"
        ingest_tasks.append(asyncio.create_task(
            sessions_q.log_event(ctx.session_id, seq_counter[0], et, body_json, event_title)
        ))
        seq_counter[0] += 1

        try:
            body = json.loads(body_json)
        except Exception:
            return

        if event_type_name == "ai_agent":
            tool_events_seen[0] = True
            await queue.put(_ds_part("e", {"finishReason": "tool-calls", "usage": usage_empty}))
            await queue.put(_ds_part("f", {"messageId": message_id}))
            for tc in body.get("tool_calls") or []:
                await queue.put(_ds_part("9", {
                    "toolCallId": tc.get("id", ""),
                    "toolName": tc.get("name", ""),
                    "args": tc.get("args") or {},
                }))
        else:
            await queue.put(_ds_part("a", {
                "toolCallId": body.get("tool_call_id", ""),
                "toolName": body.get("name", ""),
                "result": body.get("content", ""),
            }))

    async def run_turn() -> None:
        handler = ChatLangGraphHandler()
        # Log user message at seq=0
        ingest_tasks.append(asyncio.create_task(
            sessions_q.log_event(ctx.session_id, 0, "user_message", user_text)
        ))
        reply_text = await run_one_chat_turn(
            ctx=ctx,
            user_text=user_text,
            chat_handler=handler,
            request_id=0,
            on_partial_reply=on_partial,
            on_tool_event=on_tool_event,
        )
        reply_holder.append(reply_text or "")
        agent_body = json.dumps({"content": reply_text or "", "tool_calls": []}, ensure_ascii=False)
        ingest_tasks.append(asyncio.create_task(
            sessions_q.log_event(ctx.session_id, seq_counter[0], "ai_agent_message", agent_body)
        ))

        if tool_events_seen[0] and reply_text:
            await queue.put(_ds_part("0", reply_text))
        await queue.put(None)

    task = asyncio.create_task(run_turn())

    try:
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                if task.done():
                    break
                continue
            if chunk is None:
                break
            yield chunk

        if not task.done():
            await task

        if not tool_events_seen[0] and reply_holder and reply_holder[0]:
            yield _ds_part("0", reply_holder[0])
    except Exception as e:
        logger.exception("chat/stream generator error: %s", e)
        yield _ds_part("3", str(e))
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    if ingest_tasks:
        await asyncio.gather(*ingest_tasks, return_exceptions=True)

    usage = {"promptTokens": 0, "completionTokens": 0}
    yield _ds_part("d", {"finishReason": "stop", "usage": usage})
    yield _ds_part("e", {"finishReason": "stop", "usage": usage})


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    """Stream chat reply in Vercel AI SDK UI Message Stream Protocol."""
    if not request.session_id or not request.agent_id or not request.org_id:
        raise HTTPException(status_code=400, detail="session_id, agent_id, org_id are required")

    user_text = ""
    for m in reversed(request.messages or []):
        if (m.role or "").strip().lower() == "user":
            user_text = (m.content or "").strip()
            break
    if not user_text:
        raise HTTPException(status_code=400, detail="At least one user message is required")

    # Ensure session exists
    await sessions_q.create_session(request.session_id, request.org_id, request.agent_id, request.channel_type or "web")

    try:
        ctx = await build_assistant_context_for_stream(
            session_id=request.session_id,
            agent_id=request.agent_id,
            org_id=request.org_id,
            channel_type=request.channel_type or "web",
            user_name=request.user_name,
        )
    except Exception as e:
        logger.exception("build_assistant_context_for_stream failed: %s", e)
        raise HTTPException(status_code=502, detail="Failed to build chat context") from e

    message_id = f"msg_{uuid.uuid4().hex}"

    async def generate() -> AsyncGenerator[str, None]:
        async for line in _stream_chat_ds(ctx, user_text, message_id):
            yield line

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

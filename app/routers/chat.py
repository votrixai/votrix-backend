"""
Chat endpoint — SSE streaming.

POST /agents/{agent_id}/chat
Response: text/event-stream

SSE event format:
    data: {"type": "token", "content": "..."}
    data: {"type": "tool_start", "tool_call_id": "...", "name": "..."}
    data: {"type": "tool_end", "tool_call_id": "..."}
    data: {"type": "done"}
    data: {"type": "error", "message": "..."}
"""
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q
from app.db.queries import sessions as sessions_q
from app.llm.engine.agent_engine import AgentEngine
from app.models.chat import ChatRequest
from app.models.session import SessionEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["chat"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/{agent_id}/chat")
async def chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    db_session: AsyncSession = Depends(get_session),
):
    t_start = time.perf_counter()

    agent = await agents_q.get_agent(db_session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Ensure session row exists before streaming starts.
    await sessions_q.upsert_session(db_session, body.session_id, agent_id, body.user_id)

    # Record the user's message.
    await sessions_q.append_event(
        db_session,
        body.session_id,
        event_type=SessionEventType.user_message,
        event_body=body.message,
    )
    logger.info(
        "User message agent_id=%s session_id=%s: %s",
        agent_id,
        body.session_id,
        body.message[:200].replace("\n", " "),
    )

    engine = AgentEngine(agent_id, body.user_id, body.session_id, db_session)
    await engine.setup(agent)

    logger.info(
        "chat_setup agent_id=%s session_id=%s setup_ms=%.0f",
        agent_id,
        body.session_id,
        (time.perf_counter() - t_start) * 1000,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        ai_tokens: list[str] = []

        try:
            async for event in engine.astream(body.message):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if isinstance(content, str):
                        frag = content
                    elif isinstance(content, list):
                        frag = "".join(
                            b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    else:
                        frag = ""
                    if frag:
                        ai_tokens.append(frag)
                        yield _sse({"type": "token", "content": frag})

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    await sessions_q.append_event(
                        db_session,
                        body.session_id,
                        event_type=SessionEventType.tool_start,
                        event_title=tool_name,
                        event_body=json.dumps(tool_input),
                    )
                    yield _sse({
                        "type": "tool_start",
                        "tool_call_id": event.get("run_id", ""),
                        "name": tool_name,
                    })

                elif kind == "on_tool_end":
                    tool_output = event["data"].get("output", "")
                    await sessions_q.append_event(
                        db_session,
                        body.session_id,
                        event_type=SessionEventType.tool_end,
                        event_title=event["name"],
                        event_body=str(tool_output),
                    )
                    yield _sse({
                        "type": "tool_end",
                        "tool_call_id": event.get("run_id", ""),
                    })

            # Persist the complete AI reply after streaming finishes.
            reply_text = "".join(ai_tokens)
            logger.info(
                "AI reply agent_id=%s session_id=%s (%d chars): %s",
                agent_id,
                body.session_id,
                len(reply_text),
                reply_text[:400].replace("\n", " "),
            )
            if reply_text:
                await sessions_q.append_event(
                    db_session,
                    body.session_id,
                    event_type=SessionEventType.ai_message,
                    event_body=reply_text,
                )

            yield _sse({"type": "done"})

        except Exception as e:
            logger.exception(
                "Chat stream failed agent_id=%s session_id=%s",
                agent_id,
                body.session_id,
            )
            await sessions_q.append_event(
                db_session,
                body.session_id,
                event_type=SessionEventType.error,
                event_body=str(e),
            )
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

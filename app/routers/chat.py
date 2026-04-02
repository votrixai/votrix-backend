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
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q
from app.llm.engine.agent_engine import AgentEngine
from app.models.chat import ChatRequest

router = APIRouter(prefix="/agents", tags=["chat"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/{agent_id}/chat")
async def chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    db_session: AsyncSession = Depends(get_session),
):
    agent = await agents_q.get_agent(db_session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    engine = AgentEngine(agent_id, body.user_id, body.session_id, db_session)
    await engine.setup(agent)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in engine.astream(body.message):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token and isinstance(token, str):
                        yield _sse({"type": "token", "content": token})

                elif kind == "on_tool_start":
                    yield _sse({
                        "type": "tool_start",
                        "tool_call_id": event.get("run_id", ""),
                        "name": event["name"],
                    })

                elif kind == "on_tool_end":
                    yield _sse({
                        "type": "tool_end",
                        "tool_call_id": event.get("run_id", ""),
                    })

            yield _sse({"type": "done"})

        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

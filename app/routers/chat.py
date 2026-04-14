"""
Chat endpoint — SSE streaming via Anthropic managed sessions.

POST /agents/{agent_id}/chat

Request body: { user_id, session_id, message }

SSE event format:
    data: {"type": "token",      "content": "..."}
    data: {"type": "tool_start", "name": "...", "input": {...}}
    data: {"type": "tool_end",   "output": "..."}
    data: {"type": "done"}
    data: {"type": "error",      "message": "..."}
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session, session_scope
from app.db.queries import sessions as sessions_q
from app.db.queries import users as users_q
from app.models.chat import ChatRequest
from app.runtime import sessions as runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["chat"])


@router.post("/{agent_id}/chat")
async def chat(
    agent_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    # Validate user
    user = await users_q.get_user(db, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Require provisioning before chat
    if not user.agent_id:
        raise HTTPException(
            status_code=409,
            detail=f"User agent not provisioned — call POST /users/{body.user_id}/provision first",
        )

    db_session = await sessions_q.get_session(db, body.session_id)
    if db_session is None or not db_session.session_id:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found — call POST /users/{body.user_id}/sessions first",
        )
    await sessions_q.append_event(db, body.session_id, "user_message", body.message)

    async def event_stream() -> AsyncGenerator[str, None]:
        ai_tokens: list[str] = []
        try:
            async for event in runtime.stream(db_session.session_id, body.message, str(user.id)):
                if event["type"] == "token":
                    ai_tokens.append(event["content"])
                elif event["type"] == "done":
                    reply = "".join(ai_tokens)
                    if reply:
                        async with session_scope() as s:
                            await sessions_q.append_event(s, body.session_id, "ai_message", reply)

                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.exception("chat stream failed session_id=%s", body.session_id)
            async with session_scope() as s:
                await sessions_q.append_event(s, body.session_id, "error", str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

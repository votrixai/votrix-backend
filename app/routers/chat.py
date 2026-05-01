"""
Chat endpoint — SSE streaming via Anthropic managed sessions.

POST /chat

Request body: { session_id, message }

SSE event format:
    data: {"type": "token",      "content": "..."}
    data: {"type": "tool_start", "name": "...", "input": {...}}
    data: {"type": "tool_end",   "output": "..."}
    data: {"type": "done"}
    data: {"type": "error",      "message": "..."}
"""

import json
from typing import AsyncGenerator

import structlog

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session, session_scope
from app.db.queries import sessions as sessions_q
from app.db.queries import workspaces as workspaces_q
from app.management import sessions as management_sessions
from app.models.chat import ChatRequest
from app.runtime import sessions as runtime

logger = structlog.get_logger()

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    db_session = await sessions_q.get_session(db, body.session_id)
    if db_session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found — call POST /sessions first",
        )
    if not await workspaces_q.is_member(db, db_session.workspace_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    await sessions_q.append_event(db, body.session_id, "user_message", body.message)
    if body.attachments:
        await sessions_q.append_event(
            db,
            body.session_id,
            "user_attachments",
            json.dumps([a.model_dump() for a in body.attachments]),
        )

    provider_session_id = db_session.provider_session_id
    session_id = db_session.id

    composio_session_id = db_session.composio_session_id

    async def event_stream() -> AsyncGenerator[str, None]:
        ai_tokens: list[str] = []
        try:
            async for event in runtime.stream(
                provider_session_id,
                body.message,
                str(current_user.id),
                body.attachments,
                composio_session_id=composio_session_id,
            ):
                if event["type"] == "token":
                    ai_tokens.append(event["content"])
                elif event["type"] == "file":
                    async with session_scope() as s:
                        await sessions_q.append_event(
                            s,
                            session_id,
                            "ai_file",
                            json.dumps({
                                "file_id": event.get("file_id"),
                                "filename": event.get("filename"),
                                "mime_type": event.get("mime_type"),
                            }),
                        )
                elif event["type"] == "preview":
                    payload = {k: v for k, v in event.items() if k != "type"}
                    async with session_scope() as s:
                        await sessions_q.append_event(
                            s,
                            session_id,
                            "ai_preview",
                            json.dumps(payload),
                        )
                elif event["type"] == "error":
                    async with session_scope() as s:
                        await sessions_q.append_event(s, session_id, "error", event.get("message", ""))
                elif event["type"] == "done":
                    reply = "".join(ai_tokens)
                    if reply:
                        async with session_scope() as s:
                            await sessions_q.append_event(s, session_id, "ai_message", reply)
                    if not db_session.title:
                        title = await management_sessions.get_provider_session_title(
                            provider_session_id,
                        )
                        if not title:
                            title = body.message[:100]
                        if title:
                            async with session_scope() as s:
                                await sessions_q.update_title(s, session_id, title)
                            db_session.title = title

                raw = json.dumps(event)
                logger.debug("[stream] %s", raw[:50])
                yield f"data: {raw}\n\n"

        except Exception as e:
            logger.exception("chat stream failed session_id=%s", session_id)
            async with session_scope() as s:
                await sessions_q.append_event(s, session_id, "error", str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

"""
Session history routes.

GET  /users/{user_id}/sessions              list sessions for a user
GET  /sessions/{session_id}                 get session + events
DELETE /sessions/{session_id}               delete session
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.models.session import SessionDetailResponse, SessionEventResponse, SessionResponse

router = APIRouter(tags=["sessions"])


@router.get("/users/{user_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    rows = await sessions_q.list_sessions(db, user_id)
    return [
        SessionResponse(id=r.id, user_id=r.user_id, agent_slug=r.agent_slug, created_at=r.created_at)
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    events = await sessions_q.get_events(db, session_id)
    return SessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        agent_slug=session.agent_slug,
        created_at=session.created_at,
        events=[
            SessionEventResponse(
                event_index=e.event_index,
                type=e.type,
                title=e.title,
                body=e.body,
            )
            for e in events
        ],
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    deleted = await sessions_q.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

"""
Session routes.

POST   /users/{user_id}/sessions            create session (allocates Anthropic session)
GET    /users/{user_id}/sessions            list sessions for a user
GET    /sessions/{session_id}               get session + events
DELETE /sessions/{session_id}               delete session
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.db.queries import users as users_q
from app.management.environments import get_or_create as get_env_id
from app.models.session import SessionCreateResponse, SessionDetailResponse, SessionEventResponse, SessionResponse
from app.runtime.sessions import create_session

router = APIRouter(tags=["sessions"])


@router.post("/users/{user_id}/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    user = await users_q.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.agent_id:
        raise HTTPException(
            status_code=409,
            detail=f"User agent not provisioned — call POST /users/{user_id}/provision first",
        )

    env_id = get_env_id()
    provider_session_id = create_session(user.agent_id, env_id)

    session_uuid = uuid.uuid4()
    db_session = await sessions_q.create_session(db, session_uuid, user_id)
    await sessions_q.save_provider_session_id(db, session_uuid, provider_session_id)

    return SessionCreateResponse(
        id=db_session.id,
        user_id=db_session.user_id,
        session_id=provider_session_id,
        created_at=db_session.created_at,
    )


@router.get("/users/{user_id}/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    rows = await sessions_q.list_sessions(db, user_id)
    return [
        SessionResponse(id=r.id, user_id=r.user_id, created_at=r.created_at)
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

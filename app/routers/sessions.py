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
from app.management.environments import create_session
from app.management.provisioning import create_user_agent, _read_config
from app.models.session import SessionCreateRequest, SessionCreateResponse, SessionDetailResponse, SessionEventResponse, SessionResponse

router = APIRouter(tags=["sessions"])


@router.post("/users/{user_id}/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session_endpoint(
    user_id: uuid.UUID,
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    user = await users_q.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    config = _read_config(body.agent_id)
    env_id = config["envId"]

    anthropic_agent_id = create_user_agent(body.agent_id, str(user_id), user.display_name)
    provider_session_id = create_session(anthropic_agent_id, env_id)

    session_uuid = uuid.uuid4()
    db_session = await sessions_q.create_session(db, session_uuid, user_id, body.display_name)
    await sessions_q.save_provider_session_id(db, session_uuid, provider_session_id)

    return SessionCreateResponse(
        id=db_session.id,
        user_id=db_session.user_id,
        display_name=db_session.display_name,
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

"""
Session routes.

POST   /sessions                    create session (requires agent_slug)
GET    /sessions                    list sessions for current user (optional ?agent_slug=)
GET    /sessions/{session_id}       get session + events
PATCH  /sessions/{session_id}       rename session
DELETE /sessions/{session_id}       delete session
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.db.queries import user_agents as user_agents_q
from app.db.queries import users as users_q
from app.management.environments import create_session
from app.management.provisioning import create_user_agent, _read_config
from app.models.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionEventResponse,
    SessionResponse,
    SessionUpdateRequest,
)

router = APIRouter(tags=["sessions"])


async def _get_or_provision_agent(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_slug: str,
    display_name: str,
) -> str:
    """Return the Anthropic managed agent id for (user, slug), provisioning on cache miss."""
    cached = await user_agents_q.get(db, user_id, agent_slug)
    if cached:
        return cached.anthropic_agent_id

    anthropic_agent_id = create_user_agent(agent_slug, str(user_id), display_name)
    await user_agents_q.create(db, user_id, agent_slug, anthropic_agent_id)
    return anthropic_agent_id


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    user = await users_q.get_user(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate agent_slug is a real template (raises FileNotFoundError otherwise)
    try:
        config = _read_config(body.agent_slug)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent_slug}'")
    env_id = config["envId"]

    anthropic_agent_id = await _get_or_provision_agent(
        db, current_user.id, body.agent_slug, user.display_name
    )
    provider_session_id = create_session(anthropic_agent_id, env_id)

    session_uuid = uuid.uuid4()
    db_session = await sessions_q.create_session(
        db,
        session_uuid,
        current_user.id,
        body.display_name,
        agent_slug=body.agent_slug,
        agent_id=anthropic_agent_id,
    )
    await sessions_q.save_provider_session_id(db, session_uuid, provider_session_id)

    return SessionCreateResponse(
        id=db_session.id,
        user_id=db_session.user_id,
        display_name=db_session.display_name,
        agent_slug=db_session.agent_slug,
        session_id=provider_session_id,
        created_at=db_session.created_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    agent_slug: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    rows = await sessions_q.list_sessions(db, current_user.id, agent_slug=agent_slug)
    return [
        SessionResponse(
            id=r.id,
            user_id=r.user_id,
            display_name=r.display_name,
            agent_slug=r.agent_slug,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to current user")
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


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: uuid.UUID,
    body: SessionUpdateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to current user")
    updated = await sessions_q.update_display_name(db, session_id, body.display_name)
    assert updated is not None
    return SessionResponse(
        id=updated.id,
        user_id=updated.user_id,
        display_name=updated.display_name,
        agent_slug=updated.agent_slug,
        created_at=updated.created_at,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to current user")
    await sessions_q.delete_session(db, session_id)

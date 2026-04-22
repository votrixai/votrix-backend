"""
Session routes.

POST   /sessions                    create session (requires agent_slug)
GET    /sessions                    list sessions for current user (optional ?agent_slug=)
GET    /sessions/{session_id}       get session + events
DELETE /sessions/{session_id}       delete session
"""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.config import get_settings
from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.db.queries import user_agents as user_agents_q
from app.db.queries import users as users_q
from app.management import sessions as management_sessions
from app.management.environments import create_session
from app.management.provisioning import create_user_agent, _read_config
from app.models.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionEventResponse,
    SessionFileResponse,
    SessionResponse,
)

router = APIRouter(tags=["sessions"])


async def _get_or_provision_agent(
    db: AsyncSession,
    user_id,
    agent_slug: str,
    display_name: str,
) -> str:
    force = get_settings().force_reprovision
    agent_id = await asyncio.to_thread(
        create_user_agent, agent_slug, str(user_id), display_name, force=force
    )
    existing = await user_agents_q.get(db, user_id, agent_slug)
    if existing:
        existing.agent_id = agent_id
        await db.commit()
    else:
        await user_agents_q.create(db, user_id, agent_slug, agent_id)
    return agent_id


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    user = await users_q.get_user(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        config = _read_config(body.agent_slug)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent_slug}'")
    env_id = config["envId"]

    try:
        agent_id = await _get_or_provision_agent(
            db, current_user.id, body.agent_slug, user.display_name
        )
    except RuntimeError as exc:
        import logging, traceback
        logging.getLogger(__name__).error(
            "provisioning failed slug=%s user=%s: %s\n%s",
            body.agent_slug, current_user.id, exc, traceback.format_exc(),
        )
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        import logging, traceback
        logging.getLogger(__name__).error(
            "provisioning unexpected error slug=%s user=%s: %s\n%s",
            body.agent_slug, current_user.id, exc, traceback.format_exc(),
        )
        raise

    provider_session_id = create_session(agent_id, env_id)

    db_session = await sessions_q.create_session(
        db,
        provider_session_id,
        current_user.id,
        agent_slug=body.agent_slug,
        agent_id=agent_id,
    )

    return SessionCreateResponse(
        id=db_session.id,
        user_id=db_session.user_id,
        agent_slug=db_session.agent_slug,
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
            provider_session_title=r.provider_session_title,
            agent_slug=r.agent_slug,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
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


@router.get("/sessions/{session_id}/files", response_model=list[SessionFileResponse])
async def list_session_files(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    """Return all downloadable files produced in a session."""
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to current user")

    events = await sessions_q.get_events(db, session_id)
    files: list[SessionFileResponse] = []
    for e in events:
        if e.type != "ai_file":
            continue
        try:
            data = json.loads(e.body)
        except (json.JSONDecodeError, TypeError):
            continue
        fid = data.get("file_id")
        if fid:
            files.append(SessionFileResponse(
                file_id=fid,
                filename=data.get("filename"),
                mime_type=data.get("mime_type"),
            ))
    return files


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to current user")
    if session.id:
        await asyncio.to_thread(
            management_sessions.delete_provider_session, session.id
        )
    await sessions_q.delete_session(db, session_id)

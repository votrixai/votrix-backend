"""
Session routes.

POST   /sessions                    create session (requires agent_slug)
GET    /sessions                    list sessions for current user (optional ?agent_slug=)
GET    /sessions/{session_id}       get session + events
DELETE /sessions/{session_id}       delete session
"""

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.db.queries import user_agents as user_agents_q
from app.management.agent_files import upload_config_files
from app.management import sessions as management_sessions
from app.management.environments import create_session, get_or_create as create_env
from app.management.memory_stores import get_or_create as get_or_create_memory_store
from app.management.provisioning import create_user_agent, _read_config
from app.models.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionEventResponse,
    SessionFileResponse,
    SessionResponse,
)

logger = structlog.get_logger()

router = APIRouter(tags=["sessions"])


async def _get_or_provision_agent(
    db: AsyncSession,
    user_id,
    agent_slug: str,
) -> str:
    existing = await user_agents_q.get(db, user_id, agent_slug)
    if existing:
        return existing.agent_id
    agent_id = await create_user_agent(agent_slug, str(user_id))
    await user_agents_q.create(db, user_id, agent_slug, agent_id)
    return agent_id


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    try:
        config = _read_config(body.agent_slug)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent_slug}'")
    env_id = config.get("envId") or await create_env()

    try:
        agent_id = await _get_or_provision_agent(
            db, current_user.id, body.agent_slug
        )
    except RuntimeError as exc:
        logger.exception("provisioning failed", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("provisioning unexpected error", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise

    files_config = config.get("files", [])
    try:
        resources = await upload_config_files(body.agent_slug, files_config)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("file upload failed", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise HTTPException(status_code=502, detail=f"Failed to upload configured files: {exc}")

    memory_config = config.get("memoryConfig")
    store_id = await get_or_create_memory_store(db, current_user.id, body.agent_slug, memory_config)
    if store_id:
        resources.append({
            "type": "memory_store",
            "memory_store_id": store_id,
            "access": "read_write",
            "instructions": memory_config["instructions"],
        })


    provider_session_id = await create_session(agent_id, env_id, resources=resources)

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
        await management_sessions.delete_provider_session(session.id)
    await sessions_q.delete_session(db, session_id)

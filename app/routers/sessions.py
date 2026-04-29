"""
Session routes.

POST   /sessions                    create session (requires agent_slug)
GET    /sessions                    list sessions for current user's workspace
GET    /sessions/{session_id}       get session + events
DELETE /sessions/{session_id}       delete session
"""

import json
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session
from app.db.queries import agent_blueprints as blueprints_q
from app.db.queries import agent_employees as employees_q
from app.db.queries import sessions as sessions_q
from app.db.queries import workspaces as workspaces_q
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


async def _get_workspace_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    ws = await workspaces_q.get_user_default_workspace(db, user_id)
    if not ws:
        raise HTTPException(status_code=404, detail="No workspace found for user")
    return ws.id


async def _get_or_provision_blueprint(
    db: AsyncSession,
    agent_slug: str,
) -> uuid.UUID:
    config = _read_config(agent_slug)
    existing_agent_id = config.get("agentId")

    if existing_agent_id:
        bp = await blueprints_q.get_by_provider_id(db, existing_agent_id)
        if bp:
            return bp.id

    provider_agent_id = existing_agent_id or await create_user_agent(agent_slug)
    bp = await blueprints_q.create(
        db,
        provider_agent_id=provider_agent_id,
        display_name=config.get("name", agent_slug),
    )
    return bp.id


async def _get_or_create_employee(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    agent_blueprint_id: uuid.UUID,
) -> uuid.UUID:
    existing = await employees_q.get(db, workspace_id, agent_blueprint_id)
    if existing:
        return existing.id
    employee = await employees_q.create(db, workspace_id, agent_blueprint_id)
    return employee.id


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

    workspace_id = await _get_workspace_id(db, current_user.id)
    env_id = config.get("envId") or await create_env()

    try:
        blueprint_id = await _get_or_provision_blueprint(db, body.agent_slug)
    except RuntimeError as exc:
        logger.exception("provisioning failed", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("provisioning unexpected error", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise

    employee_id = await _get_or_create_employee(db, workspace_id, blueprint_id)

    bp = await blueprints_q.get(db, blueprint_id)
    agent_id = bp.provider_agent_id

    files_config = config.get("files", [])
    try:
        resources = await upload_config_files(body.agent_slug, files_config)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("file upload failed", agent_slug=body.agent_slug, user_id=str(current_user.id))
        raise HTTPException(status_code=502, detail=f"Failed to upload configured files: {exc}")

    for mc in config.get("memoryConfigs", []):
        store_id = await get_or_create_memory_store(db, employee_id, mc)
        if store_id:
            resources.append({
                "type": "memory_store",
                "memory_store_id": store_id,
                "access": "read_write",
                "instructions": mc["instructions"],
            })

    provider_session_id = await create_session(agent_id, env_id, resources=resources)

    db_session = await sessions_q.create_session(
        db,
        provider_session_id,
        workspace_id,
        agent_blueprint_id=blueprint_id,
    )

    return SessionCreateResponse(
        id=db_session.id,
        workspace_id=db_session.workspace_id,
        provider_session_id=db_session.provider_session_id,
        agent_blueprint_id=db_session.agent_blueprint_id,
        created_at=db_session.created_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    workspace_id = await _get_workspace_id(db, current_user.id)
    rows = await sessions_q.list_sessions(db, workspace_id)
    return [
        SessionResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            title=r.title,
            agent_blueprint_id=r.agent_blueprint_id,
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
    if not await workspaces_q.is_member(db, session.workspace_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    events = await sessions_q.get_events(db, session_id)
    return SessionDetailResponse(
        id=session.id,
        workspace_id=session.workspace_id,
        agent_blueprint_id=session.agent_blueprint_id,
        created_at=session.created_at,
        events=[
            SessionEventResponse(
                event_index=e.event_index,
                event_type=e.event_type,
                title=e.title,
                body=e.body,
            )
            for e in events
        ],
    )


@router.get("/sessions/{session_id}/files", response_model=list[SessionFileResponse])
async def list_session_files(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not await workspaces_q.is_member(db, session.workspace_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    events = await sessions_q.get_events(db, session_id)
    files: list[SessionFileResponse] = []
    for e in events:
        if e.event_type != "ai_file":
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
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    session = await sessions_q.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not await workspaces_q.is_member(db, session.workspace_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    await management_sessions.delete_provider_session(session.provider_session_id)
    await sessions_q.delete_session(db, session_id)

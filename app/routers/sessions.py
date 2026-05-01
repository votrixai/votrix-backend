"""
Session routes.

All endpoints require the X-Workspace-Id header (resolved by require_workspace).
Cross-tenant access returns 404 — we do not distinguish "missing" from "not yours".

POST   /sessions                    create session (agent must be enabled for workspace)
GET    /sessions                    list sessions for the active workspace
GET    /sessions/{session_id}       get session + events
DELETE /sessions/{session_id}       delete session
"""

import json
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import WorkspaceContext, require_workspace
from app.db.engine import get_session
from app.db.queries import agent_blueprints as blueprints_q
from app.db.queries import agent_employee_memory_stores as stores_q
from app.db.queries import agent_employees as employees_q
from app.db.queries import sessions as sessions_q
from app.integrations.composio import create_composio_session
from app.management import sessions as management_sessions
from app.management.environments import create_session
from app.management.provisioning import _read_config
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


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreateRequest,
    db: AsyncSession = Depends(get_session),
    ctx: WorkspaceContext = Depends(require_workspace),
):
    try:
        config = _read_config(body.agent_slug)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown agent '{body.agent_slug}'")

    raw_id = config.get("agentId")
    if not raw_id:
        raise HTTPException(status_code=422, detail=f"Agent '{body.agent_slug}' has no agentId in config.json")
    try:
        blueprint_id = uuid.UUID(raw_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Agent '{body.agent_slug}' has invalid agentId")

    bp = await blueprints_q.get(db, blueprint_id)
    if not bp:
        raise HTTPException(status_code=422, detail=f"Agent '{body.agent_slug}' has not been provisioned yet")

    employee = await employees_q.get(db, ctx.workspace_id, blueprint_id)
    if not employee:
        raise HTTPException(status_code=422, detail=f"Agent '{body.agent_slug}' is not enabled for this workspace")

    env_id = config.get("envId")
    if not env_id:
        raise HTTPException(status_code=422, detail=f"Agent '{body.agent_slug}' has no envId in config.json")

    db_stores = await stores_q.list_by_employee(db, employee.id)
    config_by_name = {mc["name"]: mc for mc in config.get("memoryConfigs", [])}
    resources = [
        {
            "type": "memory_store",
            "memory_store_id": s.provider_memory_store_id,
            "access": "read_write",
            "instructions": config_by_name[s.name]["instructions"],
        }
        for s in db_stores
        if s.name in config_by_name
    ]

    provider_session_id = await create_session(bp.provider_agent_id, env_id, resources=resources)

    raw_integrations = config.get("integrations", [])
    integrations = [i["slug"] for i in raw_integrations]
    connected_accounts = {
        i["slug"]: i["connected_account_id"]
        for i in raw_integrations
        if i.get("connected_account_id")
    }
    composio_session_id = await create_composio_session(
        str(ctx.workspace_id),
        integrations,
        connected_accounts=connected_accounts or None,
    )

    db_session = await sessions_q.create_session(
        db,
        provider_session_id,
        ctx.workspace_id,
        agent_blueprint_id=blueprint_id,
        composio_session_id=composio_session_id,
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
    ctx: WorkspaceContext = Depends(require_workspace),
):
    rows = await sessions_q.list_sessions(db, ctx.workspace_id)
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
    ctx: WorkspaceContext = Depends(require_workspace),
):
    session = await sessions_q.get_session(db, session_id)
    if not session or session.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Session not found")
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
    ctx: WorkspaceContext = Depends(require_workspace),
):
    session = await sessions_q.get_session(db, session_id)
    if not session or session.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Session not found")

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
    ctx: WorkspaceContext = Depends(require_workspace),
):
    session = await sessions_q.get_session(db, session_id)
    if not session or session.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Session not found")
    await management_sessions.delete_provider_session(session.provider_session_id)
    await sessions_q.delete_session(db, session_id)

"""Blueprint agent CRUD API.

Routes:
  POST   /orgs/{org_id}/agents          — create agent (org-scoped)
  GET    /orgs/{org_id}/agents          — list agents (org-scoped)
  GET    /agents/{agent_id}             — get agent detail
  PATCH  /agents/{agent_id}             — update agent
  DELETE /agents/{agent_id}             — delete agent
"""

import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q, blueprint_files, orgs as orgs_q
from app.db.queries.blueprint_files import _derive_fields
from app.db.models.blueprint_agents import BlueprintAgent
from app.models.agent import (
    AgentDetailResponse,
    AgentIntegration,
    AgentSummaryResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

_404 = {404: {"description": "Agent not found"}}
_400 = {400: {"description": "Bad request"}}

_DEFAULT_BLUEPRINT_FILES_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Loaded once at startup via load_default_blueprint_files()
_default_blueprint_cache: list[dict] | None = None


def load_default_blueprint_files() -> None:
    """Read prompt files from disk into memory. Called once at app startup."""
    global _default_blueprint_cache
    if not _DEFAULT_BLUEPRINT_FILES_DIR.is_dir():
        _default_blueprint_cache = []
        return

    rows: list[dict] = []
    for disk_path in sorted(_DEFAULT_BLUEPRINT_FILES_DIR.rglob("*")):
        virtual = "/" + str(disk_path.relative_to(_DEFAULT_BLUEPRINT_FILES_DIR))
        name = disk_path.name
        if disk_path.is_dir():
            rows.append({
                "path": virtual,
                "name": name,
                "type": "directory",
                "content": "",
                "storage_path": None,
                "mime_type": "",
                "created_by": "system",
                **_derive_fields(virtual, name),
            })
        elif disk_path.is_file():
            content = disk_path.read_text(encoding="utf-8")
            suffix = disk_path.suffix.lower()
            mime = "application/json" if suffix == ".json" else "text/markdown"
            rows.append({
                "path": virtual,
                "name": name,
                "type": "file",
                "content": content,
                "storage_path": None,
                "mime_type": mime,
                "created_by": "system",
                **_derive_fields(virtual, name, content),
            })
    _default_blueprint_cache = rows
    logger.info("Loaded %d default blueprint files from disk", len(rows))


async def _to_detail(session: AsyncSession, agent: BlueprintAgent) -> AgentDetailResponse:
    integs = await agents_q.get_agent_integrations(session, agent.id)
    return AgentDetailResponse(
        id=str(agent.id),
        org_id=str(agent.org_id),
        display_name=agent.display_name,
        model=agent.model,
        integrations=[
            AgentIntegration(
                integration_slug=i.integration_slug,
                deferred=i.deferred,
                enabled_tool_slugs=list(i.enabled_tool_slugs or []),
            )
            for i in integs
        ],
        deleted_at=agent.deleted_at,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("/orgs/{org_id}/agents", response_model=AgentDetailResponse, status_code=201,
             summary="Create agent")
async def create_agent(
    org_id: uuid.UUID,
    body: CreateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new blueprint agent; copy all files from the prompts/ tree into its folder."""
    kwargs: dict = {}
    if body.display_name:
        kwargs["display_name"] = body.display_name
    if body.model:
        kwargs["model"] = body.model
    if body.integrations is not None:
        kwargs["integrations"] = body.integrations

    if not await orgs_q.get_org(session, org_id):
        raise HTTPException(status_code=404, detail="Org not found")

    row = await agents_q.create_agent(session, org_id, **kwargs)

    if _default_blueprint_cache:
        new_id = row.id
        bulk_rows = [{"blueprint_agent_id": new_id, **entry} for entry in _default_blueprint_cache]
        await blueprint_files.bulk_insert(session, bulk_rows)

    return await _to_detail(session, row)


@router.get("/orgs/{org_id}/agents", response_model=List[AgentSummaryResponse], summary="List agents")
async def list_agents(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """List all blueprint agents in an org."""
    rows = await agents_q.list_agents(session, org_id)
    return [
        AgentSummaryResponse(
            id=str(r.id),
            display_name=r.display_name,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/agents/{agent_id}", response_model=AgentDetailResponse, summary="Get agent", responses=_404)
async def get_agent(agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Return full agent detail including integrations."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return await _to_detail(session, row)


@router.patch("/agents/{agent_id}", response_model=AgentDetailResponse, summary="Update agent",
              responses={**_404, **_400})
async def update_agent(
    agent_id: uuid.UUID,
    body: UpdateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Partial update — display_name, model, integrations (full replacement)."""
    updates = {}
    if body.display_name is not None:
        updates["display_name"] = body.display_name
    if body.model is not None:
        updates["model"] = body.model

    if updates:
        row = await agents_q.update_agent(session, agent_id, **updates)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        row = await agents_q.get_agent(session, agent_id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

    if body.integrations is not None:
        await agents_q.replace_agent_integrations(session, agent_id, body.integrations)

    return await _to_detail(session, row)


@router.delete("/agents/{agent_id}", status_code=204, summary="Delete agent", responses=_404)
async def delete_agent(
    agent_id: uuid.UUID,
    soft: bool = Query(False, description="Soft delete — hide from lists but keep files"),
    session: AsyncSession = Depends(get_session),
):
    """Delete a blueprint agent. Use ?soft=true to soft-delete (hide but keep files)."""
    if soft:
        deleted = await agents_q.soft_delete_agent(session, agent_id)
    else:
        deleted = await agents_q.delete_agent(session, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")

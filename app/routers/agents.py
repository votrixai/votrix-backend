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
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q, blueprint_files
from app.models.agent import (
    AgentDetail,
    AgentSummary,
    CreateAgentRequest,
    UpdateAgentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

_404 = {404: {"description": "Agent not found"}}
_400 = {400: {"description": "Bad request"}}


def _to_detail(row: dict) -> AgentDetail:
    return AgentDetail(
        id=str(row.get("id", "")),
        org_id=str(row.get("org_id", "")),
        name=row.get("name", ""),
        integrations=row.get("integrations", []),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("/orgs/{org_id}/agents", response_model=AgentDetail, status_code=201,
             summary="Create agent",
             responses={404: {"description": "Seed source agent not found"}})
async def create_agent(
    org_id: uuid.UUID,
    body: CreateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new blueprint agent. Optionally seed from an existing agent."""
    kwargs = {}
    if body.name:
        kwargs["name"] = body.name
    if body.integrations is not None:
        kwargs["integrations"] = [i.model_dump() for i in body.integrations]

    if body.seed_from:
        source = await agents_q.get_agent(session, body.seed_from)
        if not source:
            raise HTTPException(status_code=404, detail=f"Seed source agent '{body.seed_from}' not found")
        if "integrations" not in kwargs:
            kwargs["integrations"] = source.get("integrations", [])
        if "name" not in kwargs:
            kwargs["name"] = source.get("name", "")

    row = await agents_q.create_agent(session, org_id, **kwargs)

    if body.seed_from:
        source_id = uuid.UUID(body.seed_from)
        new_id = row["id"]
        source_files = await blueprint_files.tree(session, source_id)
        for f in source_files:
            if f["type"] == "directory":
                await blueprint_files.mkdir(session, new_id, f["path"])
            else:
                content_row = await blueprint_files.read_file(session, source_id, f["path"])
                if content_row:
                    await blueprint_files.write_file(
                        session, new_id, f["path"],
                        content_row.get("content", ""),
                        mime_type=content_row.get("mime_type", "text/markdown"),
                    )

    return _to_detail(row)


@router.get("/orgs/{org_id}/agents", response_model=List[AgentSummary], summary="List agents")
async def list_agents(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """List all blueprint agents in an org."""
    rows = await agents_q.list_agents(session, org_id)
    return [AgentSummary(id=str(r["id"]), name=r["name"], created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]


@router.get("/agents/{agent_id}", response_model=AgentDetail, summary="Get agent", responses=_404)
async def get_agent(agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Return full agent detail including integrations."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_detail(row)


@router.patch("/agents/{agent_id}", response_model=AgentDetail, summary="Update agent",
              responses={**_404, **_400})
async def update_agent(
    agent_id: uuid.UUID,
    body: UpdateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Partial update — name and/or integrations."""
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.integrations is not None:
        updates["integrations"] = [i.model_dump() for i in body.integrations]

    if updates:
        row = await agents_q.update_agent(session, agent_id, **updates)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        row = await agents_q.get_agent(session, agent_id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

    return _to_detail(row)


@router.delete("/agents/{agent_id}", status_code=204, summary="Delete agent", responses=_404)
async def delete_agent(agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Delete a blueprint agent and all its files (cascade)."""
    deleted = await agents_q.delete_agent(session, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")

"""Agent CRUD API.

Routes:
  POST   /orgs/{org_id}/agents                              — create agent
  GET    /orgs/{org_id}/agents                              — list agents
  GET    /orgs/{org_id}/agents/{agent_id}                   — get agent detail
  PATCH  /orgs/{org_id}/agents/{agent_id}                   — update agent
  DELETE /orgs/{org_id}/agents/{agent_id}                   — delete agent
"""

import logging
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

router = APIRouter()

@router.post("/orgs/{org_id}/agents", response_model=AgentDetail, status_code=201)
async def create_agent(
    org_id: str,
    body: CreateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new agent. Optionally seed from an existing agent."""
    existing = await agents_q.get_agent(session, org_id, body.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{body.agent_id}' already exists in org '{org_id}'")

    kwargs = {}
    if body.agent_name is not None:
        kwargs["agent_name"] = body.agent_name
    if body.integrations is not None:
        kwargs["integrations"] = [i.model_dump() for i in body.integrations]

    if body.seed_from:
        source = await agents_q.get_agent(session, org_id, body.seed_from)
        if not source:
            raise HTTPException(status_code=404, detail=f"Seed source agent '{body.seed_from}' not found")
        if "integrations" not in kwargs:
            kwargs["integrations"] = source.get("integrations", [])
        if "agent_name" not in kwargs:
            kwargs["agent_name"] = source.get("agent_name", "")

    row = await agents_q.create_agent(session, org_id, body.agent_id, **kwargs)

    if body.seed_from:
        source_files = await blueprint_files.tree(session, org_id, body.seed_from)
        for f in source_files:
            if f["type"] == "directory":
                await blueprint_files.mkdir(session, org_id, body.agent_id, f["path"])
            else:
                content_row = await blueprint_files.read_file(session, org_id, body.seed_from, f["path"])
                if content_row:
                    await blueprint_files.write_file(
                        session, org_id, body.agent_id, f["path"],
                        content_row.get("content", ""),
                        mime_type=content_row.get("mime_type", "text/markdown"),
                    )

    return _to_detail(row)


@router.get("/orgs/{org_id}/agents", response_model=List[AgentSummary])
async def list_agents(org_id: str, session: AsyncSession = Depends(get_session)):
    """List all agents in an org."""
    rows = await agents_q.list_agents(session, org_id)
    return [AgentSummary(**r) for r in rows]


@router.get("/orgs/{org_id}/agents/{agent_id}", response_model=AgentDetail)
async def get_agent(org_id: str, agent_id: str, session: AsyncSession = Depends(get_session)):
    """Get full agent detail."""
    row = await agents_q.get_agent(session, org_id, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_detail(row)


@router.patch("/orgs/{org_id}/agents/{agent_id}", response_model=AgentDetail)
async def update_agent(
    org_id: str,
    agent_id: str,
    body: UpdateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update agent name and/or integrations."""
    existing = await agents_q.get_agent(session, org_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.agent_name is not None:
        await agents_q.set_agent_name(session, org_id, agent_id, body.agent_name)
    if body.integrations is not None:
        await agents_q.set_agent_integrations(
            session, org_id, agent_id, [i.model_dump() for i in body.integrations]
        )

    row = await agents_q.get_agent(session, org_id, agent_id)
    return _to_detail(row)


@router.delete("/orgs/{org_id}/agents/{agent_id}", status_code=204)
async def delete_agent(org_id: str, agent_id: str, session: AsyncSession = Depends(get_session)):
    """Delete an agent and all its files (cascade)."""
    existing = await agents_q.get_agent(session, org_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agents_q.delete_agent(session, org_id, agent_id)


def _to_detail(row: dict) -> AgentDetail:
    return AgentDetail(
        org_id=row.get("org_id", ""),
        agent_id=row.get("agent_id", ""),
        agent_name=row.get("agent_name", ""),
        integrations=row.get("integrations", []),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )

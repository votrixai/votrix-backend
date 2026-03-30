"""Blueprint agent CRUD API.

Routes:
  POST   /orgs/{org_id}/agents                — create agent
  GET    /orgs/{org_id}/agents                — list agents
  GET    /orgs/{org_id}/agents/{slug}          — get agent detail
  PATCH  /orgs/{org_id}/agents/{slug}          — update agent
  DELETE /orgs/{org_id}/agents/{slug}          — delete agent
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
    """Create a new blueprint agent. Optionally seed from an existing agent."""
    existing = await agents_q.get_agent(session, org_id, body.slug)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{body.slug}' already exists in org '{org_id}'")

    kwargs = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.integrations is not None:
        kwargs["integrations"] = [i.model_dump() for i in body.integrations]

    if body.seed_from:
        source = await agents_q.get_agent(session, org_id, body.seed_from)
        if not source:
            raise HTTPException(status_code=404, detail=f"Seed source agent '{body.seed_from}' not found")
        if "integrations" not in kwargs:
            kwargs["integrations"] = source.get("integrations", [])
        if "name" not in kwargs:
            kwargs["name"] = source.get("name", "")

    row = await agents_q.create_agent(session, org_id, body.slug, **kwargs)

    if body.seed_from:
        source = await agents_q.get_agent(session, org_id, body.seed_from)
        source_id = source["id"]
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


@router.get("/orgs/{org_id}/agents", response_model=List[AgentSummary])
async def list_agents(org_id: str, session: AsyncSession = Depends(get_session)):
    """List all blueprint agents in an org."""
    rows = await agents_q.list_agents(session, org_id)
    return [AgentSummary(id=str(r["id"]), slug=r["slug"], name=r["name"], created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]


@router.get("/orgs/{org_id}/agents/{slug}", response_model=AgentDetail)
async def get_agent(org_id: str, slug: str, session: AsyncSession = Depends(get_session)):
    """Get full agent detail."""
    row = await agents_q.get_agent(session, org_id, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_detail(row)


@router.patch("/orgs/{org_id}/agents/{slug}", response_model=AgentDetail)
async def update_agent(
    org_id: str,
    slug: str,
    body: UpdateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update agent name and/or integrations."""
    existing = await agents_q.get_agent(session, org_id, slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.name is not None:
        await agents_q.set_agent_name(session, org_id, slug, body.name)
    if body.integrations is not None:
        await agents_q.set_agent_integrations(
            session, existing["id"], [i.model_dump() for i in body.integrations]
        )

    row = await agents_q.get_agent(session, org_id, slug)
    return _to_detail(row)


@router.delete("/orgs/{org_id}/agents/{slug}", status_code=204)
async def delete_agent(org_id: str, slug: str, session: AsyncSession = Depends(get_session)):
    """Delete a blueprint agent and all its files (cascade)."""
    existing = await agents_q.get_agent(session, org_id, slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agents_q.delete_agent(session, org_id, slug)


def _to_detail(row: dict) -> AgentDetail:
    return AgentDetail(
        id=str(row.get("id", "")),
        org_id=row.get("org_id", ""),
        slug=row.get("slug", ""),
        name=row.get("name", ""),
        integrations=row.get("integrations", []),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )

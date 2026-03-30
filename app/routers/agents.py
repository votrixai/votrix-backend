"""Agent CRUD API.

Routes:
  POST   /orgs/{org_id}/agents                              — create agent
  GET    /orgs/{org_id}/agents                              — list agents
  GET    /orgs/{org_id}/agents/{agent_id}                   — get agent detail
  PATCH  /orgs/{org_id}/agents/{agent_id}                   — update agent
  DELETE /orgs/{org_id}/agents/{agent_id}                   — delete agent
  GET    /orgs/{org_id}/agents/{agent_id}/prompts/{section} — get one prompt section
  PUT    /orgs/{org_id}/agents/{agent_id}/prompts/{section} — update one prompt section
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q, blueprint_files
from app.models.agent import (
    AgentDetail,
    AgentPrompts,
    AgentSummary,
    CreateAgentRequest,
    UpdateAgentRequest,
    UpdatePromptSectionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SECTIONS = {"identity", "soul", "agents", "user", "tools", "bootstrap"}
_PROMPT_COLS = {
    "identity": "prompt_identity",
    "soul": "prompt_soul",
    "agents": "prompt_agents",
    "user": "prompt_user",
    "tools": "prompt_tools",
    "bootstrap": "prompt_bootstrap",
}


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
    if body.prompts:
        for key, col in _PROMPT_COLS.items():
            val = getattr(body.prompts, key, "")
            if val:
                kwargs[col] = val
    if body.registry:
        kwargs["registry"] = body.registry

    if body.seed_from:
        source = await agents_q.get_agent(session, org_id, body.seed_from)
        if not source:
            raise HTTPException(status_code=404, detail=f"Seed source agent '{body.seed_from}' not found")
        for key, col in _PROMPT_COLS.items():
            if col not in kwargs:
                kwargs[col] = source.get(col, "")
        if "registry" not in kwargs:
            kwargs["registry"] = source.get("registry", {})

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
    """Get full agent detail including prompts and registry."""
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
    """Update agent prompts and/or registry."""
    existing = await agents_q.get_agent(session, org_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")

    if body.prompts:
        for key, col in _PROMPT_COLS.items():
            val = getattr(body.prompts, key, None)
            if val is not None:
                await agents_q.set_prompt_section(session, org_id, agent_id, key, val)

    if body.registry is not None:
        await agents_q.set_registry(session, org_id, agent_id, body.registry)

    row = await agents_q.get_agent(session, org_id, agent_id)
    return _to_detail(row)


@router.delete("/orgs/{org_id}/agents/{agent_id}", status_code=204)
async def delete_agent(org_id: str, agent_id: str, session: AsyncSession = Depends(get_session)):
    """Delete an agent and all its files (cascade)."""
    existing = await agents_q.get_agent(session, org_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agents_q.delete_agent(session, org_id, agent_id)


@router.get("/orgs/{org_id}/agents/{agent_id}/prompts/{section}")
async def get_prompt_section(
    org_id: str, agent_id: str, section: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single prompt section content."""
    if section not in _VALID_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section. Must be one of: {', '.join(sorted(_VALID_SECTIONS))}")
    sections = await agents_q.get_prompt_sections(session, org_id, agent_id)
    if not sections:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"section": section, "content": sections.get(section, "")}


@router.put("/orgs/{org_id}/agents/{agent_id}/prompts/{section}")
async def update_prompt_section(
    org_id: str, agent_id: str, section: str,
    body: UpdatePromptSectionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a single prompt section."""
    if section not in _VALID_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section. Must be one of: {', '.join(sorted(_VALID_SECTIONS))}")
    existing = await agents_q.get_agent(session, org_id, agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agents_q.set_prompt_section(session, org_id, agent_id, section, body.content)
    return {"section": section, "content": body.content}


def _to_detail(row: dict) -> AgentDetail:
    prompts = AgentPrompts(
        identity=row.get("prompt_identity", ""),
        soul=row.get("prompt_soul", ""),
        agents=row.get("prompt_agents", ""),
        user=row.get("prompt_user", ""),
        tools=row.get("prompt_tools", ""),
        bootstrap=row.get("prompt_bootstrap", ""),
    )
    return AgentDetail(
        org_id=row.get("org_id", ""),
        agent_id=row.get("agent_id", ""),
        prompts=prompts,
        registry=row.get("registry", {}),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )

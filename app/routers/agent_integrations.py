"""Agent integration management API.

Routes:
  GET    /agents/{agent_id}/integrations                   — list integrations enabled for this agent
  PUT    /agents/{agent_id}/integrations/{integration_id}  — add or replace an integration
  DELETE /agents/{agent_id}/integrations/{integration_id}  — remove an integration

Validation on PUT:
  1. slug must exist in registry or Composio cache
  2. slug must be activated in the agent's org (or be "platform" which is always allowed)
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q, orgs as orgs_q
from app.models.agent import AgentIntegration, UpsertAgentIntegrationRequest
from app.tools import composio_cache
from app.tools.registry import get_integration

router = APIRouter(prefix="/agents", tags=["agent-integrations"])

_PLATFORM_SLUG = "platform"


async def _validate_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_id: str,
) -> None:
    """Raise 404/403 if the integration can't be used by this agent."""
    # 1. Slug must exist
    if not get_integration(integration_id) and not composio_cache.slug_exists(integration_id):
        raise HTTPException(status_code=404, detail=f"Integration '{integration_id}' not found")

    # 2. platform is always allowed — skip org check
    if integration_id == _PLATFORM_SLUG:
        return

    # 3. Must be in the org's activated list
    agent = await agents_q.get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    org_slugs = await orgs_q.get_org_integration_slugs(session, agent["org_id"])
    if integration_id not in org_slugs:
        raise HTTPException(
            status_code=403,
            detail=f"Integration '{integration_id}' is not activated for this org",
        )


@router.get("/{agent_id}/integrations", response_model=List[AgentIntegration])
async def list_agent_integrations(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all integrations enabled for this agent."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return row.get("integrations", [])


@router.put("/{agent_id}/integrations/{integration_id}", response_model=AgentIntegration)
async def upsert_agent_integration(
    agent_id: uuid.UUID,
    integration_id: str,
    body: UpsertAgentIntegrationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Add or replace an integration on this agent."""
    await _validate_integration(session, agent_id, integration_id)

    item = await agents_q.upsert_agent_integration(
        session, agent_id, integration_id, body.deferred, body.enabled_tool_ids
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return item


@router.delete("/{agent_id}/integrations/{integration_id}", status_code=204)
async def delete_agent_integration(
    agent_id: uuid.UUID,
    integration_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Remove an integration from this agent."""
    deleted = await agents_q.delete_agent_integration(session, agent_id, integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent or integration not found")

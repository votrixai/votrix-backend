"""Blueprint agent ↔ integration management API.

Routes:
  GET    /agents/{agent_id}/integrations                              — list integrations enabled for this agent
  POST   /agents/{agent_id}/integrations/{integration_id}             — enable an integration
  DELETE /agents/{agent_id}/integrations/{integration_id}             — disable an integration
  GET    /agents/{agent_id}/integrations/{integration_id}/tools       — list enabled tools
  POST   /agents/{agent_id}/integrations/{integration_id}/tools/{tool_id} — enable a tool
  DELETE /agents/{agent_id}/integrations/{integration_id}/tools/{tool_id} — disable a tool
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q
from app.db.queries import blueprint_agent_integrations as bai_q
from app.models.agent_integration import (
    BlueprintAgentIntegrationDetail,
    BlueprintAgentIntegrationToolDetail,
)
from app.db.queries import agents as agents_q, orgs as orgs_q
from app.models.agent import AgentIntegration, UpsertAgentIntegrationRequest
from app.config import get_settings
from app.integrations.providers.composio import toolkit_exists
from app.integrations.registry import get_integration

router = APIRouter(prefix="/agents", tags=["agent-integrations"])



async def _validate_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_id: str,
) -> None:
    """Raise 404/403 if the integration can't be used by this agent."""
    # 1. Slug must exist (registry or live Composio SDK check)
    if not get_integration(integration_id) and not await toolkit_exists(get_settings().composio_api_key, integration_id):
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


@router.get("/{agent_id}/integrations", response_model=List[AgentIntegration],
            summary="List agent integrations",
            responses={404: {"description": "Agent not found"}})
async def list_agent_integrations(
    agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all integrations enabled for this agent."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    links = await bai_q.list_agent_integrations(session, agent_id)
    return links


@router.post("/{agent_id}/integrations/{integration_id}",
             response_model=BlueprintAgentIntegrationDetail,
             status_code=201,
             summary="Enable integration on agent",
             responses={404: {"description": "Agent not found"}})
async def enable_agent_integration(
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Enable an integration on this agent."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    link = await bai_q.enable_integration(session, agent_id, integration_id)
    return link


@router.delete("/{agent_id}/integrations/{integration_id}", status_code=204,
               summary="Disable integration on agent",
               responses={404: {"description": "Agent or integration not found"}})
async def disable_agent_integration(
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Disable an integration on this agent."""
    deleted = await bai_q.disable_integration(session, agent_id, integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent or integration link not found")


@router.get("/{agent_id}/integrations/{integration_id}/tools",
            response_model=List[BlueprintAgentIntegrationToolDetail],
            summary="List enabled tools for agent integration",
            responses={404: {"description": "Agent integration link not found"}})
async def list_enabled_tools(
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List tools enabled on this agent-integration link."""
    links = await bai_q.list_agent_integrations(session, agent_id)
    link = next((l for l in links if str(l["agent_integration_id"]) == str(integration_id)), None)
    if not link:
        raise HTTPException(status_code=404, detail="Integration not enabled on this agent")
    return await bai_q.list_enabled_tools(session, link["id"])


@router.post("/{agent_id}/integrations/{integration_id}/tools/{tool_id}",
             response_model=BlueprintAgentIntegrationToolDetail,
             status_code=201,
             summary="Enable tool on agent integration",
             responses={404: {"description": "Agent integration link not found"}})
async def enable_tool(
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    tool_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Enable a tool on this agent-integration link."""
    links = await bai_q.list_agent_integrations(session, agent_id)
    link = next((l for l in links if str(l["agent_integration_id"]) == str(integration_id)), None)
    if not link:
        raise HTTPException(status_code=404, detail="Integration not enabled on this agent")
    result = await bai_q.enable_tool(session, link["id"], tool_id)
    return result


@router.delete("/{agent_id}/integrations/{integration_id}/tools/{tool_id}",
               status_code=204,
               summary="Disable tool on agent integration",
               responses={404: {"description": "Tool link not found"}})
async def disable_tool(
    agent_id: uuid.UUID,
    integration_id: uuid.UUID,
    tool_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Disable a tool on this agent-integration link."""
    links = await bai_q.list_agent_integrations(session, agent_id)
    link = next((l for l in links if str(l["agent_integration_id"]) == str(integration_id)), None)
    if not link:
        raise HTTPException(status_code=404, detail="Integration not enabled on this agent")
    deleted = await bai_q.disable_tool(session, link["id"], tool_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tool not enabled")

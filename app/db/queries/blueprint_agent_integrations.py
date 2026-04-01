"""CRUD for blueprint_agent_integrations and blueprint_agent_integration_tools join tables."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_agent_integrations import BlueprintAgentIntegration
from app.db.models.blueprint_agent_integration_tools import BlueprintAgentIntegrationTool


# ---------------------------------------------------------------------------
# Blueprint ↔ Integration links
# ---------------------------------------------------------------------------

def _link_to_dict(row: BlueprintAgentIntegration) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in BlueprintAgentIntegration.__table__.columns}


async def list_agent_integrations(
    session: AsyncSession, agent_id: uuid.UUID
) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(BlueprintAgentIntegration).where(
            BlueprintAgentIntegration.blueprint_agent_id == agent_id
        )
    )
    return [_link_to_dict(r) for r in result.scalars().all()]


async def get_agent_integration(
    session: AsyncSession, link_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    result = await session.execute(
        select(BlueprintAgentIntegration).where(BlueprintAgentIntegration.id == link_id)
    )
    row = result.scalar_one_or_none()
    return _link_to_dict(row) if row else None


async def enable_integration(
    session: AsyncSession, agent_id: uuid.UUID, integration_id: uuid.UUID
) -> Dict[str, Any]:
    """Link an integration to a blueprint agent. Returns existing link if already present."""
    existing = await session.execute(
        select(BlueprintAgentIntegration).where(
            BlueprintAgentIntegration.blueprint_agent_id == agent_id,
            BlueprintAgentIntegration.agent_integration_id == integration_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        return _link_to_dict(row)

    obj = BlueprintAgentIntegration(
        blueprint_agent_id=agent_id, agent_integration_id=integration_id
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _link_to_dict(obj)


async def disable_integration(
    session: AsyncSession, agent_id: uuid.UUID, integration_id: uuid.UUID
) -> bool:
    """Remove an integration link (cascades to enabled tools). Returns False if not found."""
    result = await session.execute(
        delete(BlueprintAgentIntegration).where(
            BlueprintAgentIntegration.blueprint_agent_id == agent_id,
            BlueprintAgentIntegration.agent_integration_id == integration_id,
        )
    )
    await session.commit()
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Enabled tools on a blueprint-agent-integration link
# ---------------------------------------------------------------------------

def _tool_link_to_dict(row: BlueprintAgentIntegrationTool) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in BlueprintAgentIntegrationTool.__table__.columns}


async def list_enabled_tools(
    session: AsyncSession, link_id: uuid.UUID
) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(BlueprintAgentIntegrationTool).where(
            BlueprintAgentIntegrationTool.blueprint_agent_integration_id == link_id
        )
    )
    return [_tool_link_to_dict(r) for r in result.scalars().all()]


async def enable_tool(
    session: AsyncSession, link_id: uuid.UUID, tool_id: uuid.UUID
) -> Dict[str, Any]:
    """Enable a tool on a blueprint-agent-integration link. Returns existing if already present."""
    existing = await session.execute(
        select(BlueprintAgentIntegrationTool).where(
            BlueprintAgentIntegrationTool.blueprint_agent_integration_id == link_id,
            BlueprintAgentIntegrationTool.agent_integration_tool_id == tool_id,
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        return _tool_link_to_dict(row)

    obj = BlueprintAgentIntegrationTool(
        blueprint_agent_integration_id=link_id, agent_integration_tool_id=tool_id
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _tool_link_to_dict(obj)


async def disable_tool(
    session: AsyncSession, link_id: uuid.UUID, tool_id: uuid.UUID
) -> bool:
    result = await session.execute(
        delete(BlueprintAgentIntegrationTool).where(
            BlueprintAgentIntegrationTool.blueprint_agent_integration_id == link_id,
            BlueprintAgentIntegrationTool.agent_integration_tool_id == tool_id,
        )
    )
    await session.commit()
    return result.rowcount > 0

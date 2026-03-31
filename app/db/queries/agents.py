"""Agent queries — CRUD for blueprint_agents."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_agents import BlueprintAgent


def _row_to_dict(row: BlueprintAgent) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in BlueprintAgent.__table__.columns}


async def get_agent(session: AsyncSession, agent_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    stmt = select(BlueprintAgent).where(BlueprintAgent.id == agent_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    return _row_to_dict(row)


async def create_agent(session: AsyncSession, org_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    integrations = kwargs.pop("integrations", None) or []
    obj = BlueprintAgent(org_id=org_id, integrations=integrations, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _row_to_dict(obj)


async def update_agent(session: AsyncSession, agent_id: uuid.UUID, **kwargs) -> Optional[Dict[str, Any]]:
    stmt = (
        update(BlueprintAgent)
        .where(BlueprintAgent.id == agent_id)
        .values(**kwargs)
        .returning(BlueprintAgent)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    await session.commit()
    return _row_to_dict(row)


async def list_agents(session: AsyncSession, org_id: uuid.UUID) -> List[Dict[str, Any]]:
    stmt = (
        select(BlueprintAgent.id, BlueprintAgent.name, BlueprintAgent.created_at, BlueprintAgent.updated_at)
        .where(BlueprintAgent.org_id == org_id)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def delete_agent(session: AsyncSession, agent_id: uuid.UUID) -> bool:
    stmt = delete(BlueprintAgent).where(BlueprintAgent.id == agent_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Per-integration operations (operate on the JSONB list in-place)
# ---------------------------------------------------------------------------

async def upsert_agent_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_id: str,
    deferred: bool,
    enabled_tool_ids: List[str],
) -> Optional[Dict[str, Any]]:
    """Add or replace a single integration entry on the agent. Returns the upserted item, or None if agent not found."""
    result = await session.execute(select(BlueprintAgent).where(BlueprintAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return None

    new_item = {"integration_id": integration_id, "deferred": deferred, "enabled_tool_ids": enabled_tool_ids}
    updated = [i for i in (agent.integrations or []) if i.get("integration_id") != integration_id]
    updated.append(new_item)

    await session.execute(
        update(BlueprintAgent)
        .where(BlueprintAgent.id == agent_id)
        .values(integrations=updated)
    )
    await session.commit()
    return new_item


async def delete_agent_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_id: str,
) -> bool:
    """Remove a single integration from the agent. Returns False if agent or integration not found."""
    result = await session.execute(select(BlueprintAgent).where(BlueprintAgent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return False

    current = agent.integrations or []
    updated = [i for i in current if i.get("integration_id") != integration_id]
    if len(updated) == len(current):
        return False

    await session.execute(
        update(BlueprintAgent)
        .where(BlueprintAgent.id == agent_id)
        .values(integrations=updated)
    )
    await session.commit()
    return True

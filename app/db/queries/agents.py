"""Agent queries — CRUD for blueprint_agents."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_agents import BlueprintAgent
from app.db.models.agent_integrations import AgentIntegration


def _row_to_dict(row: BlueprintAgent) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in BlueprintAgent.__table__.columns}


async def get_agent(session: AsyncSession, agent_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    stmt = select(BlueprintAgent).where(BlueprintAgent.id == agent_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    data = _row_to_dict(row)
    data["integrations"] = await get_agent_integrations(session, row.id)
    return data


async def create_agent(session: AsyncSession, org_id: uuid.UUID, **kwargs) -> Dict[str, Any]:
    integrations = kwargs.pop("integrations", None) or []
    obj = BlueprintAgent(org_id=org_id, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    if integrations:
        await set_agent_integrations(session, obj.id, integrations)
    data = _row_to_dict(obj)
    data["integrations"] = await get_agent_integrations(session, obj.id)
    return data


async def get_agent_integrations(
    session: AsyncSession, blueprint_agent_id: uuid.UUID
) -> List[Dict[str, Any]]:
    stmt = select(AgentIntegration).where(AgentIntegration.blueprint_agent_id == blueprint_agent_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "blueprint_agent_id": str(r.blueprint_agent_id),
            "integration_slug": r.integration_slug,
        }
        for r in rows
    ]


async def set_agent_integrations(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, integrations: List[Dict[str, Any]]
) -> None:
    await session.execute(
        delete(AgentIntegration).where(AgentIntegration.blueprint_agent_id == blueprint_agent_id)
    )
    for item in integrations or []:
        stmt = (
            insert(AgentIntegration)
            .values(
                blueprint_agent_id=blueprint_agent_id,
                integration_slug=item.get("integration_slug", ""),
            )
            .on_conflict_do_nothing(
                index_elements=["blueprint_agent_id", "integration_slug"],
            )
        )
        await session.execute(stmt)
    await session.commit()


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
    data = _row_to_dict(row)
    data["integrations"] = await get_agent_integrations(session, row.id)
    return data


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

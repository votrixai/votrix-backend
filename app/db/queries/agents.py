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


async def get_agent(session: AsyncSession, org_id: uuid.UUID, slug: str = "default") -> Optional[Dict[str, Any]]:
    stmt = select(BlueprintAgent).where(BlueprintAgent.org_id == org_id, BlueprintAgent.slug == slug)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    data = _row_to_dict(row)
    data["integrations"] = await get_agent_integrations(session, row.id)
    return data


async def create_agent(session: AsyncSession, org_id: uuid.UUID, slug: str = "default", **kwargs) -> Dict[str, Any]:
    integrations = kwargs.pop("integrations", None) or []
    obj = BlueprintAgent(org_id=org_id, slug=slug, **kwargs)
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
            "integration_id": r.integration_id,
            "enabled_tool_ids": list(r.enabled_tool_ids or []),
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
                integration_id=item.get("integration_id", ""),
                enabled_tool_ids=item.get("enabled_tool_ids", []) or [],
            )
            .on_conflict_do_update(
                index_elements=["blueprint_agent_id", "integration_id"],
                set_={"enabled_tool_ids": item.get("enabled_tool_ids", []) or []},
            )
        )
        await session.execute(stmt)
    await session.commit()


async def set_agent_name(session: AsyncSession, org_id: uuid.UUID, slug: str, name: str) -> None:
    stmt = (
        update(BlueprintAgent)
        .where(BlueprintAgent.org_id == org_id, BlueprintAgent.slug == slug)
        .values(name=name)
    )
    await session.execute(stmt)
    await session.commit()


async def list_agents(session: AsyncSession, org_id: uuid.UUID) -> List[Dict[str, Any]]:
    stmt = (
        select(BlueprintAgent.id, BlueprintAgent.slug, BlueprintAgent.name, BlueprintAgent.created_at, BlueprintAgent.updated_at)
        .where(BlueprintAgent.org_id == org_id)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def delete_agent(session: AsyncSession, org_id: uuid.UUID, slug: str) -> None:
    stmt = delete(BlueprintAgent).where(BlueprintAgent.org_id == org_id, BlueprintAgent.slug == slug)
    await session.execute(stmt)
    await session.commit()

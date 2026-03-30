"""Agent queries — CRUD for agent_config."""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig
from app.db.models.agent_integration import AgentIntegration


def _row_to_dict(row: AgentConfig) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in AgentConfig.__table__.columns}


async def get_agent(session: AsyncSession, org_id: str, agent_id: str = "default") -> Optional[Dict[str, Any]]:
    stmt = select(AgentConfig).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    data = _row_to_dict(row)
    data["integrations"] = await get_agent_integrations(session, org_id, agent_id)
    return data


async def create_agent(session: AsyncSession, org_id: str, agent_id: str = "default", **kwargs) -> Dict[str, Any]:
    integrations = kwargs.pop("integrations", None) or []
    obj = AgentConfig(org_id=org_id, agent_id=agent_id, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    if integrations:
        await set_agent_integrations(session, org_id, agent_id, integrations)
    data = _row_to_dict(obj)
    data["integrations"] = await get_agent_integrations(session, org_id, agent_id)
    return data


async def get_agent_integrations(
    session: AsyncSession, org_id: str, agent_id: str = "default"
) -> List[Dict[str, Any]]:
    stmt = select(AgentIntegration).where(AgentIntegration.agent_id == agent_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "agent_id": r.agent_id,
            "integration_id": r.integration_id,
            "enabled_tool_ids": list(r.enabled_tool_ids or []),
        }
        for r in rows
    ]


async def set_agent_integrations(
    session: AsyncSession, org_id: str, agent_id: str, integrations: List[Dict[str, Any]]
) -> None:
    await session.execute(
        delete(AgentIntegration).where(AgentIntegration.agent_id == agent_id)
    )
    for item in integrations or []:
        stmt = (
            insert(AgentIntegration)
            .values(
                agent_id=agent_id,
                integration_id=item.get("integration_id", ""),
                enabled_tool_ids=item.get("enabled_tool_ids", []) or [],
            )
            .on_conflict_do_update(
                index_elements=["agent_id", "integration_id"],
                set_={"enabled_tool_ids": item.get("enabled_tool_ids", []) or []},
            )
        )
        await session.execute(stmt)
    await session.commit()


async def set_agent_name(session: AsyncSession, org_id: str, agent_id: str, agent_name: str) -> None:
    stmt = (
        update(AgentConfig)
        .where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
        .values(agent_name=agent_name)
    )
    await session.execute(stmt)
    await session.commit()


async def list_agents(session: AsyncSession, org_id: str) -> List[Dict[str, Any]]:
    stmt = (
        select(AgentConfig.agent_id, AgentConfig.agent_name, AgentConfig.created_at, AgentConfig.updated_at)
        .where(AgentConfig.org_id == org_id)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def delete_agent(session: AsyncSession, org_id: str, agent_id: str) -> None:
    stmt = delete(AgentConfig).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    await session.execute(stmt)
    await session.commit()

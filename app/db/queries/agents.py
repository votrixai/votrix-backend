"""Agent queries — CRUD for agent_config table + prompt sections + registry."""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig

_PROMPT_COLS = {
    "identity": "prompt_identity",
    "soul": "prompt_soul",
    "agents": "prompt_agents",
    "user": "prompt_user",
    "tools": "prompt_tools",
    "bootstrap": "prompt_bootstrap",
}


def _row_to_dict(row: AgentConfig) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in AgentConfig.__table__.columns}


async def get_agent(session: AsyncSession, org_id: str, agent_id: str = "default") -> Optional[Dict[str, Any]]:
    stmt = select(AgentConfig).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return _row_to_dict(row) if row else None


async def create_agent(session: AsyncSession, org_id: str, agent_id: str = "default", **kwargs) -> Dict[str, Any]:
    obj = AgentConfig(org_id=org_id, agent_id=agent_id, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _row_to_dict(obj)


async def get_prompt_sections(session: AsyncSession, org_id: str, agent_id: str = "default") -> Dict[str, str]:
    cols = [getattr(AgentConfig, col) for col in _PROMPT_COLS.values()]
    stmt = select(*cols).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    result = await session.execute(stmt)
    row = result.mappings().first()
    if not row:
        return {}
    return {key: row.get(col, "") for key, col in _PROMPT_COLS.items()}


async def set_prompt_section(session: AsyncSession, org_id: str, agent_id: str, section: str, content: str) -> None:
    col = _PROMPT_COLS.get(section)
    if not col:
        raise ValueError(f"Unknown prompt section: {section}")
    stmt = (
        update(AgentConfig)
        .where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
        .values(**{col: content})
    )
    await session.execute(stmt)
    await session.commit()


async def get_registry(session: AsyncSession, org_id: str, agent_id: str = "default") -> Dict[str, Any]:
    stmt = select(AgentConfig.registry).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row or {}


async def set_registry(session: AsyncSession, org_id: str, agent_id: str, registry: Dict[str, Any]) -> None:
    stmt = (
        update(AgentConfig)
        .where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
        .values(registry=registry)
    )
    await session.execute(stmt)
    await session.commit()


async def set_registry_field(session: AsyncSession, org_id: str, agent_id: str, field: str, value: Any) -> None:
    """Update a single top-level field in the registry JSONB."""
    reg = await get_registry(session, org_id, agent_id)
    reg[field] = value
    await set_registry(session, org_id, agent_id, reg)


async def list_agents(session: AsyncSession, org_id: str) -> List[Dict[str, Any]]:
    stmt = (
        select(AgentConfig.agent_id, AgentConfig.created_at, AgentConfig.updated_at)
        .where(AgentConfig.org_id == org_id)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def delete_agent(session: AsyncSession, org_id: str, agent_id: str) -> None:
    stmt = delete(AgentConfig).where(AgentConfig.org_id == org_id, AgentConfig.agent_id == agent_id)
    await session.execute(stmt)
    await session.commit()

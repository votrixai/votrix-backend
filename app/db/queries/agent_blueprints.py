"""Agent blueprint queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_blueprints import AgentBlueprint


async def get_by_provider_id(db: AsyncSession, provider_agent_id: str) -> AgentBlueprint | None:
    result = await db.execute(
        select(AgentBlueprint).where(AgentBlueprint.provider_agent_id == provider_agent_id)
    )
    return result.scalar_one_or_none()


async def get(db: AsyncSession, blueprint_id: uuid.UUID) -> AgentBlueprint | None:
    result = await db.execute(
        select(AgentBlueprint).where(AgentBlueprint.id == blueprint_id)
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    provider_agent_id: str,
    display_name: str,
    provider: str = "anthropic",
) -> AgentBlueprint:
    row = AgentBlueprint(
        provider_agent_id=provider_agent_id,
        display_name=display_name,
        provider=provider,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

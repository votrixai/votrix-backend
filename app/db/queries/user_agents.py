"""Per-user per-template Anthropic agent cache."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_agents import UserAgent


async def get(db: AsyncSession, user_id: uuid.UUID, agent_slug: str) -> UserAgent | None:
    result = await db.execute(
        select(UserAgent).where(
            UserAgent.user_id == user_id,
            UserAgent.agent_slug == agent_slug,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_slug: str,
    anthropic_agent_id: str,
) -> UserAgent:
    row = UserAgent(
        user_id=user_id,
        agent_slug=agent_slug,
        anthropic_agent_id=anthropic_agent_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

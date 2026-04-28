"""DB queries for user_agent_memory_stores."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory_stores import UserAgentMemoryStore


async def get(db: AsyncSession, user_id: uuid.UUID, agent_slug: str) -> UserAgentMemoryStore | None:
    result = await db.execute(
        select(UserAgentMemoryStore).where(
            UserAgentMemoryStore.user_id == user_id,
            UserAgentMemoryStore.agent_slug == agent_slug,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_slug: str,
    store_id: str,
) -> UserAgentMemoryStore:
    row = UserAgentMemoryStore(
        store_id=store_id,
        user_id=user_id,
        agent_slug=agent_slug,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

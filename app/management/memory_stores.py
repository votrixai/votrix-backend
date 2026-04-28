"""Memory store provisioning — get or create a per-user-agent memory store."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.client import get_async_client
from app.db.queries import memory_stores as memory_stores_q


async def get_or_create(
    db: AsyncSession,
    user_id: uuid.UUID,
    agent_slug: str,
    memory_config: dict | None,
) -> str | None:
    """
    Return the store_id for this user+agent, creating it on Anthropic if needed.
    Returns None if the agent has no memoryConfig.
    """
    if not memory_config:
        return None

    existing = await memory_stores_q.get(db, user_id, agent_slug)
    if existing:
        return existing.store_id

    client = get_async_client()
    store = await client.beta.memory_stores.create(
        name=memory_config["name"],
        description=memory_config["description"],
    )

    await memory_stores_q.create(db, user_id, agent_slug, store.id)
    return store.id

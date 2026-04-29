"""Memory store provisioning — get or create a per-employee memory store."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.client import get_async_client
from app.db.queries import agent_employee_memory_stores as stores_q


async def get_or_create(
    db: AsyncSession,
    agent_employee_id: uuid.UUID,
    memory_config: dict | None,
) -> str | None:
    """
    Return the provider store_id for this agent employee, creating it on Anthropic if needed.
    Returns None if the agent has no memoryConfig.
    """
    if not memory_config:
        return None

    existing = await stores_q.get(db, agent_employee_id)
    if existing:
        return existing.provider_memory_store_id

    client = get_async_client()
    store = await client.beta.memory_stores.create(
        name=memory_config["name"],
        description=memory_config["description"],
    )

    await stores_q.create(db, agent_employee_id, store.id, name=memory_config["name"])
    return store.id

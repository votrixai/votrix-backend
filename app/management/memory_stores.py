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
    Return the provider store_id for this agent employee + config name,
    creating it on Anthropic if needed.
    Returns None if memory_config is falsy.
    """
    if not memory_config:
        return None

    name = memory_config["name"]
    existing = await stores_q.get_by_employee_and_name(db, agent_employee_id, name)
    if existing:
        return existing.provider_memory_store_id

    client = get_async_client()
    store = await client.beta.memory_stores.create(
        name=name,
        description=memory_config.get("description", ""),
    )

    await stores_q.create(db, agent_employee_id, store.id, name=name)
    return store.id

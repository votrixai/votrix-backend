"""Memory store provisioning — create, update, archive, and sync stores."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.client import get_async_client
from app.db.queries import agent_employee_memory_stores as stores_q
from app.db.queries import agent_employees as employees_q

logger = structlog.get_logger()


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


async def sync_memory_stores_for_blueprint(
    db: AsyncSession,
    blueprint_id: uuid.UUID,
    memory_configs: list[dict],
) -> dict:
    """
    Sync memory stores for all agent_employees of a given blueprint.

    For each employee:
      - configs with a name matching an existing DB store → update via API
      - configs with no matching store → create via API + DB
      - DB stores with no matching config name → archive via API + delete from DB
    """
    client = get_async_client()
    employees = await employees_q.list_by_blueprint(db, blueprint_id)
    config_names = {mc["name"] for mc in memory_configs}
    config_by_name = {mc["name"]: mc for mc in memory_configs}

    stats = {"created": 0, "updated": 0, "archived": 0}

    for employee in employees:
        db_stores = await stores_q.list_by_employee(db, employee.id)
        db_store_by_name = {s.name: s for s in db_stores}

        # Update existing stores whose name matches a config
        for name, store in db_store_by_name.items():
            if name not in config_names:
                continue
            mc = config_by_name[name]
            await client.beta.memory_stores.update(
                store.provider_memory_store_id,
                name=mc["name"],
                description=mc.get("description", ""),
            )
            stats["updated"] += 1
            logger.info("memory_store updated", store_id=store.provider_memory_store_id, name=name)

        # Create new stores for configs not yet in DB
        for mc in memory_configs:
            if mc["name"] in db_store_by_name:
                continue
            store = await client.beta.memory_stores.create(
                name=mc["name"],
                description=mc.get("description", ""),
            )
            await stores_q.create(db, employee.id, store.id, name=mc["name"])
            stats["created"] += 1
            logger.info("memory_store created", store_id=store.id, name=mc["name"])

        # Archive stores no longer in config
        for name, store in db_store_by_name.items():
            if name in config_names:
                continue
            await client.beta.memory_stores.archive(store.provider_memory_store_id)
            await stores_q.delete(db, store.id)
            stats["archived"] += 1
            logger.info("memory_store archived", store_id=store.provider_memory_store_id, name=name)

    return stats

"""Agent employee memory store queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_employee_memory_stores import AgentEmployeeMemoryStore


async def get(db: AsyncSession, agent_employee_id: uuid.UUID) -> AgentEmployeeMemoryStore | None:
    result = await db.execute(
        select(AgentEmployeeMemoryStore).where(
            AgentEmployeeMemoryStore.agent_employee_id == agent_employee_id,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    agent_employee_id: uuid.UUID,
    provider_memory_store_id: str,
    name: str = "",
) -> AgentEmployeeMemoryStore:
    row = AgentEmployeeMemoryStore(
        agent_employee_id=agent_employee_id,
        provider_memory_store_id=provider_memory_store_id,
        name=name,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

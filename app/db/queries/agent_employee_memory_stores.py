"""Agent employee memory store queries."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_employee_memory_stores import AgentEmployeeMemoryStore


async def get_by_employee_and_name(
    db: AsyncSession, agent_employee_id: uuid.UUID, name: str
) -> AgentEmployeeMemoryStore | None:
    result = await db.execute(
        select(AgentEmployeeMemoryStore).where(
            AgentEmployeeMemoryStore.agent_employee_id == agent_employee_id,
            AgentEmployeeMemoryStore.name == name,
        )
    )
    return result.scalar_one_or_none()


async def list_by_employee(
    db: AsyncSession, agent_employee_id: uuid.UUID
) -> Sequence[AgentEmployeeMemoryStore]:
    result = await db.execute(
        select(AgentEmployeeMemoryStore).where(
            AgentEmployeeMemoryStore.agent_employee_id == agent_employee_id,
        )
    )
    return result.scalars().all()


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


async def delete(db: AsyncSession, store_id: uuid.UUID) -> None:
    result = await db.execute(
        select(AgentEmployeeMemoryStore).where(AgentEmployeeMemoryStore.id == store_id)
    )
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()

"""Agent employee queries."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_employees import AgentEmployee


async def list_by_blueprint(
    db: AsyncSession, agent_blueprint_id: uuid.UUID
) -> Sequence[AgentEmployee]:
    result = await db.execute(
        select(AgentEmployee).where(
            AgentEmployee.agent_blueprint_id == agent_blueprint_id,
        )
    )
    return result.scalars().all()


async def get(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    agent_blueprint_id: uuid.UUID,
) -> AgentEmployee | None:
    result = await db.execute(
        select(AgentEmployee).where(
            AgentEmployee.workspace_id == workspace_id,
            AgentEmployee.agent_blueprint_id == agent_blueprint_id,
        )
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    agent_blueprint_id: uuid.UUID,
) -> AgentEmployee:
    row = AgentEmployee(
        workspace_id=workspace_id,
        agent_blueprint_id=agent_blueprint_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

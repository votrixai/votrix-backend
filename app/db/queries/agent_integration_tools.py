"""CRUD for the agent_integration_tools catalog table."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_integration_tools import AgentIntegrationTool


def _row_to_dict(row: AgentIntegrationTool) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in AgentIntegrationTool.__table__.columns}


async def list_tools(
    session: AsyncSession, integration_id: uuid.UUID
) -> List[Dict[str, Any]]:
    result = await session.execute(
        select(AgentIntegrationTool).where(
            AgentIntegrationTool.agent_integration_id == integration_id
        )
    )
    return [_row_to_dict(r) for r in result.scalars().all()]


async def get_tool(session: AsyncSession, tool_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    result = await session.execute(
        select(AgentIntegrationTool).where(AgentIntegrationTool.id == tool_id)
    )
    row = result.scalar_one_or_none()
    return _row_to_dict(row) if row else None


async def create_tool(
    session: AsyncSession, integration_id: uuid.UUID, **kwargs
) -> Dict[str, Any]:
    obj = AgentIntegrationTool(agent_integration_id=integration_id, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _row_to_dict(obj)


async def update_tool(
    session: AsyncSession, tool_id: uuid.UUID, **kwargs
) -> Optional[Dict[str, Any]]:
    stmt = (
        update(AgentIntegrationTool)
        .where(AgentIntegrationTool.id == tool_id)
        .values(**kwargs)
        .returning(AgentIntegrationTool)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    await session.commit()
    return _row_to_dict(row)


async def delete_tool(session: AsyncSession, tool_id: uuid.UUID) -> bool:
    result = await session.execute(
        delete(AgentIntegrationTool).where(AgentIntegrationTool.id == tool_id)
    )
    await session.commit()
    return result.rowcount > 0

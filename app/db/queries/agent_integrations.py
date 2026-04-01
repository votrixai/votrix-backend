"""CRUD for the agent_integrations catalog table."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_integrations import AgentIntegration


def _row_to_dict(row: AgentIntegration) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in AgentIntegration.__table__.columns}


async def list_integrations(session: AsyncSession) -> List[Dict[str, Any]]:
    result = await session.execute(select(AgentIntegration))
    return [_row_to_dict(r) for r in result.scalars().all()]


async def get_integration(session: AsyncSession, integration_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    result = await session.execute(
        select(AgentIntegration).where(AgentIntegration.id == integration_id)
    )
    row = result.scalar_one_or_none()
    return _row_to_dict(row) if row else None


async def get_integration_by_slug(session: AsyncSession, slug: str) -> Optional[Dict[str, Any]]:
    result = await session.execute(
        select(AgentIntegration).where(AgentIntegration.slug == slug)
    )
    row = result.scalar_one_or_none()
    return _row_to_dict(row) if row else None


async def create_integration(session: AsyncSession, **kwargs) -> Dict[str, Any]:
    obj = AgentIntegration(**kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _row_to_dict(obj)


async def update_integration(
    session: AsyncSession, integration_id: uuid.UUID, **kwargs
) -> Optional[Dict[str, Any]]:
    stmt = (
        update(AgentIntegration)
        .where(AgentIntegration.id == integration_id)
        .values(**kwargs)
        .returning(AgentIntegration)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    await session.commit()
    return _row_to_dict(row)


async def delete_integration(session: AsyncSession, integration_id: uuid.UUID) -> bool:
    result = await session.execute(
        delete(AgentIntegration).where(AgentIntegration.id == integration_id)
    )
    await session.commit()
    return result.rowcount > 0

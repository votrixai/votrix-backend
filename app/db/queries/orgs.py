"""DAO functions for the orgs table."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.orgs import Org


async def create_org(
    session: AsyncSession,
    *,
    display_name: str = "",
    timezone: str = "UTC",
    metadata: dict | None = None,
) -> Org:
    obj = Org(
        display_name=display_name,
        timezone=timezone,
        metadata_=metadata or {},
    )
    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    return obj


async def get_org(session: AsyncSession, org_id: uuid.UUID) -> Org | None:
    stmt = select(Org).where(Org.id == org_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_orgs(session: AsyncSession) -> list[Org]:
    stmt = select(Org).order_by(Org.created_at)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_org(session: AsyncSession, org_id: uuid.UUID, **kwargs) -> Org | None:
    if "metadata" in kwargs:
        kwargs["metadata_"] = kwargs.pop("metadata")
    stmt = (
        update(Org)
        .where(Org.id == org_id)
        .values(**kwargs)
        .returning(Org)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_org(session: AsyncSession, org_id: uuid.UUID) -> bool:
    stmt = delete(Org).where(Org.id == org_id)
    result = await session.execute(stmt)
    return result.rowcount > 0

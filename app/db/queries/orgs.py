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


# ---------------------------------------------------------------------------
# Per-org integration list (stores activated slugs)
# ---------------------------------------------------------------------------

async def get_org_integration_slugs(session: AsyncSession, org_id: uuid.UUID) -> list[str]:
    """Return the list of integration slugs activated for this org."""
    org = await get_org(session, org_id)
    return list(org.integrations or []) if org else []


async def add_org_integration(session: AsyncSession, org_id: uuid.UUID, slug: str) -> Org | None:
    """Add slug to org's integration list (no-op if already present). Returns updated org."""
    org = await get_org(session, org_id)
    if not org:
        return None
    current = list(org.integrations or [])
    if slug in current:
        return org
    current.append(slug)
    stmt = update(Org).where(Org.id == org_id).values(integrations=current).returning(Org)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def remove_org_integration(session: AsyncSession, org_id: uuid.UUID, slug: str) -> bool:
    """Remove slug from org's integration list. Returns False if org or slug not found."""
    org = await get_org(session, org_id)
    if not org:
        return False
    current = list(org.integrations or [])
    if slug not in current:
        return False
    current.remove(slug)
    await session.execute(update(Org).where(Org.id == org_id).values(integrations=current))
    return True

"""DAO functions for the orgs table."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_agents import BlueprintAgent
from app.db.models.blueprint_files import BlueprintFile
from app.db.models.end_user_accounts import EndUserAccount
from app.db.models.orgs import Org
from app.db.models.user_files import UserFile
from app.storage import BUCKET, delete_file as storage_delete


async def create_org(
    session: AsyncSession,
    *,
    display_name: str = "",
    timezone: str = "UTC",
    metadata: dict | None = None,
    integrations: list[str] | None = None,
) -> Org:
    obj = Org(
        display_name=display_name,
        timezone=timezone,
        metadata_=metadata or {},
        integrations=integrations or [],
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
    """Delete an org and clean up any Storage objects before DB cascade."""
    # Collect agent IDs and user IDs that belong to this org
    agent_ids = (
        await session.execute(
            select(BlueprintAgent.id).where(BlueprintAgent.org_id == org_id)
        )
    ).scalars().all()
    user_ids = (
        await session.execute(
            select(EndUserAccount.id).where(EndUserAccount.org_id == org_id)
        )
    ).scalars().all()

    # Clean up blueprint_files storage
    if agent_ids:
        bp_storage = (
            await session.execute(
                select(BlueprintFile.storage_path)
                .where(BlueprintFile.blueprint_agent_id.in_(agent_ids), BlueprintFile.storage_path.is_not(None))
            )
        ).scalars().all()
        for sp in bp_storage:
            await storage_delete(BUCKET, sp)

    # Clean up user_files storage
    if user_ids:
        uf_storage = (
            await session.execute(
                select(UserFile.storage_path)
                .where(UserFile.user_account_id.in_(user_ids), UserFile.storage_path.is_not(None))
            )
        ).scalars().all()
        for sp in uf_storage:
            await storage_delete(BUCKET, sp)

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

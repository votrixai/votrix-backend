"""DAO functions for the end_user_accounts table.

Return shapes (DAO; HTTP layer uses ``app.models.end_user_account``):

    ``create_end_user_account``, ``get_end_user_account``,
    ``list_end_user_accounts``, ``update_end_user_account``
        → :class:`app.db.models.end_user_accounts.EndUserAccount`
        OR ``None`` where a single-row lookup/update misses.

    ``delete_end_user_account``
        → ``bool`` — row deleted or not (callers should ``commit``).
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.end_user_accounts import EndUserAccount
from app.db.models.user_files import UserFile
from app.storage import BUCKET, delete_file as storage_delete


async def create_end_user_account(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    display_name: str = "",
    sandbox: bool = False,
) -> EndUserAccount:
    obj = EndUserAccount(
        org_id=org_id,
        display_name=display_name,
        sandbox=sandbox,
    )
    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    return obj


async def get_end_user_account(
    session: AsyncSession, user_id: uuid.UUID
) -> Optional[EndUserAccount]:
    stmt = select(EndUserAccount).where(EndUserAccount.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_end_user_accounts(
    session: AsyncSession, org_id: uuid.UUID
) -> List[EndUserAccount]:
    stmt = (
        select(EndUserAccount)
        .where(EndUserAccount.org_id == org_id)
        .order_by(EndUserAccount.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_end_user_account(
    session: AsyncSession, user_id: uuid.UUID, **kwargs
) -> Optional[EndUserAccount]:
    stmt = (
        update(EndUserAccount)
        .where(EndUserAccount.id == user_id)
        .values(**kwargs)
        .returning(EndUserAccount)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_end_user_account(
    session: AsyncSession, user_id: uuid.UUID
) -> bool:
    """Delete a user account and clean up any Storage objects before DB cascade."""
    storage_stmt = (
        select(UserFile.storage_path)
        .where(UserFile.user_account_id == user_id, UserFile.storage_path.is_not(None))
    )
    for sp in (await session.execute(storage_stmt)).scalars().all():
        await storage_delete(BUCKET, sp)

    stmt = delete(EndUserAccount).where(EndUserAccount.id == user_id)
    result = await session.execute(stmt)
    return result.rowcount > 0

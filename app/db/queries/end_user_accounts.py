"""DAO functions for the end_user_accounts table."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.end_user_accounts import EndUserAccount


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
    stmt = delete(EndUserAccount).where(EndUserAccount.id == user_id)
    result = await session.execute(stmt)
    return result.rowcount > 0

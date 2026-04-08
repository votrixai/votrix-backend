"""DAO functions for user_notifications."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notifications import UserNotification


async def create_notification(
    session: AsyncSession,
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    title: str,
    body: str,
    type: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> UserNotification:
    row = UserNotification(
        user_id=user_id,
        agent_id=agent_id,
        title=title,
        body=body,
        type=type,
        extra_metadata=metadata,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
) -> List[UserNotification]:
    stmt = (
        select(UserNotification)
        .where(UserNotification.user_id == user_id)
    )
    if unread_only:
        stmt = stmt.where(UserNotification.read == False)  # noqa: E712
    stmt = stmt.order_by(UserNotification.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def mark_read(
    session: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    stmt = (
        update(UserNotification)
        .where(UserNotification.id == notification_id, UserNotification.user_id == user_id)
        .values(read=True)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def mark_all_read(
    session: AsyncSession,
    user_id: uuid.UUID,
    agent_id: Optional[uuid.UUID] = None,
) -> int:
    stmt = (
        update(UserNotification)
        .where(UserNotification.user_id == user_id, UserNotification.read == False)  # noqa: E712
    )
    if agent_id:
        stmt = stmt.where(UserNotification.agent_id == agent_id)
    stmt = stmt.values(read=True)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount

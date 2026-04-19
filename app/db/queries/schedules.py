from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schedules import Schedule


async def create_schedule(
    db: AsyncSession,
    session_id: str,
    user_id: uuid.UUID,
    cron_expr: str,
    timezone_str: str,
    message: str,
    description: str | None,
    next_run_at: datetime,
) -> Schedule:
    schedule = Schedule(
        session_id=session_id,
        user_id=user_id,
        cron_expr=cron_expr,
        timezone=timezone_str,
        message=message,
        description=description,
        next_run_at=next_run_at,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_schedule(db: AsyncSession, schedule_id: uuid.UUID) -> Schedule | None:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    return result.scalar_one_or_none()


async def list_by_user(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Schedule]:
    result = await db.execute(
        select(Schedule)
        .where(Schedule.user_id == user_id, Schedule.is_active.is_(True))
        .order_by(Schedule.created_at.desc())
    )
    return result.scalars().all()


async def delete_schedule(db: AsyncSession, schedule_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    schedule = await get_schedule(db, schedule_id)
    if not schedule or schedule.user_id != user_id:
        return False
    await db.delete(schedule)
    await db.commit()
    return True


async def get_due(db: AsyncSession) -> Sequence[Schedule]:
    """Return all active schedules whose next_run_at is in the past."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Schedule).where(
            Schedule.is_active.is_(True),
            Schedule.next_run_at <= now,
        )
    )
    return result.scalars().all()


async def advance(db: AsyncSession, schedule: Schedule, next_run_at: datetime) -> None:
    """Update next_run_at after a successful fire."""
    schedule.next_run_at = next_run_at
    await db.commit()

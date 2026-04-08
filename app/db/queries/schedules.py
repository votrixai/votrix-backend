"""DAO functions for user_agent_schedules."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from croniter import croniter
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.schedules import UserAgentSchedule

_VALID_MINUTES = {0, 15, 30, 45}
_STALE_THRESHOLD_SECONDS = 1800  # 30 minutes — skip stale jobs rather than firing late


def _validate_cron(expr: str) -> str:
    """Raise ValueError if expr is invalid or minute field is not a 15-min boundary."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (expected 5 fields): {expr!r}")
    minute_field = parts[0]
    # Allow */15 and */30 in addition to fixed values
    if minute_field not in ("*/15", "*/30"):
        try:
            minute_val = int(minute_field)
        except ValueError:
            raise ValueError(
                f"Minute field must be 0, 15, 30, 45, */15, or */30. Got: {minute_field!r}"
            )
        if minute_val not in _VALID_MINUTES:
            raise ValueError(
                f"Minute field must be one of {sorted(_VALID_MINUTES)}. Got: {minute_val}"
            )
    if not croniter.is_valid(expr):
        raise ValueError(f"Invalid cron expression: {expr!r}")
    return expr


def _next_run(cron_expr: str, after: Optional[datetime] = None) -> datetime:
    base = after or datetime.now(timezone.utc)
    it = croniter(cron_expr, base)
    return it.get_next(datetime)


async def create_schedule(
    session: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    cron_expr: str,
    message: str,
    description: str = "",
) -> UserAgentSchedule:
    from app.db.queries.sessions import upsert_session

    _validate_cron(cron_expr)

    # Each job gets one persistent session — all firings share the same thread
    session_id = uuid.uuid4()
    await upsert_session(session, session_id, agent_id, user_id)

    row = UserAgentSchedule(
        agent_id=agent_id,
        user_id=user_id,
        message=message,
        cron_expr=cron_expr,
        description=description,
        enabled=True,
        session_id=session_id,
        next_run_at=_next_run(cron_expr),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_schedules(
    session: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> List[UserAgentSchedule]:
    stmt = (
        select(UserAgentSchedule)
        .where(
            UserAgentSchedule.agent_id == agent_id,
            UserAgentSchedule.user_id == user_id,
        )
        .order_by(UserAgentSchedule.created_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def disable_schedule(
    session: AsyncSession,
    schedule_id: uuid.UUID,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    stmt = (
        update(UserAgentSchedule)
        .where(
            UserAgentSchedule.id == schedule_id,
            UserAgentSchedule.agent_id == agent_id,
            UserAgentSchedule.user_id == user_id,
        )
        .values(enabled=False)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def delete_schedule(
    session: AsyncSession,
    schedule_id: uuid.UUID,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    stmt = delete(UserAgentSchedule).where(
        UserAgentSchedule.id == schedule_id,
        UserAgentSchedule.agent_id == agent_id,
        UserAgentSchedule.user_id == user_id,
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def claim_due_jobs(session: AsyncSession) -> List[UserAgentSchedule]:
    """
    Fetch all jobs due now using SELECT FOR UPDATE SKIP LOCKED.
    Safe to call from multiple concurrent instances — each job is claimed by exactly one.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(UserAgentSchedule)
        .where(
            UserAgentSchedule.enabled == True,  # noqa: E712
            UserAgentSchedule.next_run_at <= now,
        )
        .with_for_update(skip_locked=True)
    )
    return list((await session.execute(stmt)).scalars().all())


async def mark_job_done(
    session: AsyncSession,
    job: UserAgentSchedule,
) -> None:
    """Advance next_run_at to the next occurrence after now."""
    now = datetime.now(timezone.utc)
    job.last_run_at = now
    job.next_run_at = _next_run(job.cron_expr, after=now)
    await session.commit()


def is_stale(job: UserAgentSchedule) -> bool:
    """Return True if the job is more than 30 minutes overdue (e.g. server was down)."""
    now = datetime.now(timezone.utc)
    delta = (now - job.next_run_at).total_seconds()
    return delta > _STALE_THRESHOLD_SECONDS

"""
Internal cron endpoint — called by Cloud Scheduler every minute.

POST /internal/cron/tick
"""

from __future__ import annotations

import uuid
import zoneinfo
from datetime import datetime, timezone

import structlog
from croniter import croniter
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session, session_scope
from app.db.queries import schedules as schedules_q
from app.db.queries import sessions as sessions_q
from app.runtime import sessions as runtime

logger = structlog.get_logger()

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/cron/tick")
async def cron_tick(db: AsyncSession = Depends(get_session)):
    due = await schedules_q.get_due(db)
    schedule_ids = [s.id for s in due]
    fired = 0
    errors = 0

    for sid in schedule_ids:
        try:
            await _fire(sid)
            fired += 1
        except Exception:
            logger.exception("cron fire failed schedule_id=%s", sid)
            errors += 1

    return {"fired": fired, "errors": errors}


async def _fire(schedule_id: uuid.UUID) -> None:
    async with session_scope() as db:
        schedule = await schedules_q.get_schedule(db, schedule_id)
        if not schedule:
            return
        cron_expression = schedule.cron_expression
        tz_str = schedule.timezone
        message = schedule.message

    tz = zoneinfo.ZoneInfo(tz_str)
    next_run_at = croniter(cron_expression, datetime.now(tz)).get_next(datetime)
    next_run_at = next_run_at.astimezone(timezone.utc)

    async with session_scope() as db:
        schedule_fresh = await schedules_q.get_schedule(db, schedule_id)
        if schedule_fresh:
            await schedules_q.advance(db, schedule_fresh, next_run_at)

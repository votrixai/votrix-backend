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
        session = await sessions_q.get_session(db, schedule.session_id)
        if not session:
            logger.warning("cron skip: session not found schedule_id=%s", schedule_id)
            return
        await sessions_q.append_event(db, session.id, "user_message", schedule.message)
        # capture locals before session closes
        session_id = session.id
        user_id = str(schedule.user_id)
        message = schedule.message
        cron_expr = schedule.cron_expr
        tz_str = schedule.timezone

    ai_tokens: list[str] = []
    async for event in runtime.stream(session_id, message, user_id):
        if event["type"] == "token":
            ai_tokens.append(event["content"])

    reply = "".join(ai_tokens)

    tz = zoneinfo.ZoneInfo(tz_str)
    next_run_at = croniter(cron_expr, datetime.now(tz)).get_next(datetime)
    next_run_at = next_run_at.astimezone(timezone.utc)

    async with session_scope() as db:
        if reply:
            await sessions_q.append_event(db, session_id, "ai_message", reply)
        schedule_fresh = await schedules_q.get_schedule(db, schedule_id)
        if schedule_fresh:
            await schedules_q.advance(db, schedule_fresh, next_run_at)

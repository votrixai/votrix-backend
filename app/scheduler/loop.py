"""Polling scheduler loop — runs every 15 minutes, fires due cron jobs."""

import asyncio
import logging

from app.db.engine import session_scope
from app.db.queries import schedules as schedules_q
from app.scheduler.runner import run_job

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 900  # 15 minutes in seconds


async def scheduler_loop() -> None:
    """
    Background task started at app startup.

    Every 15 minutes:
      1. Open a DB session and claim all due jobs (FOR UPDATE SKIP LOCKED).
      2. Fire each job concurrently (each job gets its own session inside run_job).
      3. Sleep until the next poll.

    SKIP LOCKED ensures that if multiple backend instances are running,
    each due job is claimed and executed by exactly one instance.
    """
    logger.info("Scheduler loop started (poll interval: %ds)", _POLL_INTERVAL)

    while True:
        try:
            async with session_scope() as db:
                jobs = await schedules_q.claim_due_jobs(db)

            if jobs:
                logger.info("Scheduler: %d job(s) due", len(jobs))
                await asyncio.gather(*(run_job(job) for job in jobs))
            else:
                logger.debug("Scheduler: no jobs due")

        except Exception:
            logger.exception("Scheduler poll error — will retry next cycle")

        await asyncio.sleep(_POLL_INTERVAL)

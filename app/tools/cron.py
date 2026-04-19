"""
Cron tools — schedule recurring messages to the agent.
"""

from __future__ import annotations

import uuid
import zoneinfo
from datetime import datetime, timezone

from croniter import croniter

from app.db.engine import session_scope
from app.db.queries import schedules as schedules_q

DEFINITIONS = [
    {
        "type": "custom",
        "name": "cron_create",
        "description": (
            "Create a recurring scheduled job. "
            "The platform will send `message` to this conversation at the times defined by `cron_expr`. "
            "Returns a job_id for future management."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cron_expr": {
                    "type": "string",
                    "description": (
                        "Standard 5-field cron expression. "
                        "Examples: '0 8 * * *' (daily 08:00), '0 9 * * 1' (Monday 09:00)."
                    ),
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name, e.g. 'Asia/Shanghai', 'America/New_York'. Must confirm with user before using.",
                },
                "message": {
                    "type": "string",
                    "description": "Message sent to the agent when the job fires.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this job does.",
                },
            },
            "required": ["cron_expr", "timezone", "message"],
        },
    },
    {
        "type": "custom",
        "name": "cron_delete",
        "description": "Delete a scheduled job by its job_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "UUID of the job to delete."},
            },
            "required": ["job_id"],
        },
    },
    {
        "type": "custom",
        "name": "cron_list",
        "description": "List all active scheduled jobs for the current user.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    if name == "cron_create":
        return await _create(input, user_id, session_id)
    if name == "cron_delete":
        return await _delete(input, user_id)
    if name == "cron_list":
        return await _list(user_id)
    return {"error": f"Unknown cron tool: {name}"}


async def _create(input: dict, user_id: str, session_id: str | None) -> dict:
    if not session_id:
        return {"error": "session_id is required to create a cron job"}

    cron_expr = input["cron_expr"]
    timezone_str = input["timezone"]
    message = input["message"]
    description = input.get("description")

    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except zoneinfo.ZoneInfoNotFoundError:
        return {"error": f"Unknown timezone: {timezone_str}"}

    try:
        now_tz = datetime.now(tz)
        next_run_local = croniter(cron_expr, now_tz).get_next(datetime)
        next_run_at = next_run_local.astimezone(timezone.utc)
    except Exception as e:
        return {"error": f"Invalid cron expression: {e}"}

    async with session_scope() as db:
        schedule = await schedules_q.create_schedule(
            db,
            session_id=session_id,
            user_id=uuid.UUID(user_id),
            cron_expr=cron_expr,
            timezone_str=timezone_str,
            message=message,
            description=description,
            next_run_at=next_run_at,
        )

    return {
        "job_id": str(schedule.id),
        "next_run_at": next_run_at.isoformat(),
        "description": description,
    }


async def _delete(input: dict, user_id: str) -> dict:
    job_id = input["job_id"]
    try:
        schedule_id = uuid.UUID(job_id)
    except ValueError:
        return {"error": f"Invalid job_id: {job_id}"}

    async with session_scope() as db:
        deleted = await schedules_q.delete_schedule(db, schedule_id, uuid.UUID(user_id))

    if not deleted:
        return {"error": "Job not found or does not belong to this user"}
    return {"deleted": job_id}


async def _list(user_id: str) -> dict:
    async with session_scope() as db:
        schedules = await schedules_q.list_by_user(db, uuid.UUID(user_id))

    return {
        "jobs": [
            {
                "job_id": str(s.id),
                "cron_expr": s.cron_expr,
                "timezone": s.timezone,
                "message": s.message,
                "description": s.description,
                "next_run_at": s.next_run_at.isoformat(),
            }
            for s in schedules
        ]
    }

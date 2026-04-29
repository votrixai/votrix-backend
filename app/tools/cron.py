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
            "The platform will send `message` at the times defined by `cron_expression`. "
            "Returns a job_id for future management."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cron_expression": {
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
            "required": ["cron_expression", "timezone", "message"],
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
        "description": "List all active scheduled jobs.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def handle(name: str, input: dict, **kwargs) -> dict:
    if name == "cron_create":
        return await _create(input)
    if name == "cron_delete":
        return await _delete(input)
    if name == "cron_list":
        return await _list()
    return {"error": f"Unknown cron tool: {name}"}


async def _create(input: dict) -> dict:
    cron_expression = input["cron_expression"]
    timezone_str = input["timezone"]
    message = input["message"]
    description = input.get("description")

    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except zoneinfo.ZoneInfoNotFoundError:
        return {"error": f"Unknown timezone: {timezone_str}"}

    try:
        now_tz = datetime.now(tz)
        next_run_local = croniter(cron_expression, now_tz).get_next(datetime)
        next_run_at = next_run_local.astimezone(timezone.utc)
    except Exception as e:
        return {"error": f"Invalid cron expression: {e}"}

    async with session_scope() as db:
        schedule = await schedules_q.create_schedule(
            db,
            cron_expression=cron_expression,
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


async def _delete(input: dict) -> dict:
    job_id = input["job_id"]
    try:
        schedule_id = uuid.UUID(job_id)
    except ValueError:
        return {"error": f"Invalid job_id: {job_id}"}

    async with session_scope() as db:
        deleted = await schedules_q.delete_schedule(db, schedule_id)

    if not deleted:
        return {"error": "Job not found"}
    return {"deleted": job_id}


async def _list() -> dict:
    async with session_scope() as db:
        schedules = await schedules_q.list_active(db)

    return {
        "jobs": [
            {
                "job_id": str(s.id),
                "cron_expression": s.cron_expression,
                "timezone": s.timezone,
                "message": s.message,
                "description": s.description,
                "next_run_at": s.next_run_at.isoformat(),
            }
            for s in schedules
        ]
    }

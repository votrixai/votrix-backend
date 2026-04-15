"""
Cron tools — schedule recurring messages to the agent.

Handlers are stubs until the schedules DB table is implemented.
"""

from __future__ import annotations

import uuid

DEFINITIONS = [
    {
        "type": "custom",
        "name": "cron_create",
        "description": (
            "Create a recurring scheduled job. "
            "The platform will send `message` to this agent at the times defined by `cron_expr`. "
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
                "message": {
                    "type": "string",
                    "description": "Message sent to the agent when the job fires.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what this job does.",
                },
            },
            "required": ["cron_expr", "message"],
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


async def handle(name: str, input: dict, user_id: str) -> dict:
    if name == "cron_create":
        return {"status": True, "job_id": str(uuid.uuid4()), "message": "Job scheduled (stub)"}
    if name == "cron_delete":
        return {"status": True, "message": "Job deleted (stub)"}
    if name == "cron_list":
        return {"status": True, "jobs": []}
    return {"error": f"Unknown cron tool: {name}"}

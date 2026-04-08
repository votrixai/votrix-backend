"""Schedule management endpoints.

GET    /users/{user_id}/agents/{agent_id}/schedules
DELETE /users/{user_id}/agents/{agent_id}/schedules/{schedule_id}
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import schedules as schedules_q

router = APIRouter(prefix="/users", tags=["schedules"])


class ScheduleResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    user_id: uuid.UUID
    session_id: Optional[uuid.UUID]
    message: str
    cron_expr: str
    description: str
    enabled: bool
    next_run_at: str
    last_run_at: Optional[str]

    @classmethod
    def from_orm(cls, row) -> "ScheduleResponse":
        return cls(
            id=row.id,
            agent_id=row.agent_id,
            user_id=row.user_id,
            session_id=row.session_id,
            message=row.message,
            cron_expr=row.cron_expr,
            description=row.description,
            enabled=row.enabled,
            next_run_at=row.next_run_at.isoformat(),
            last_run_at=row.last_run_at.isoformat() if row.last_run_at else None,
        )


@router.get(
    "/{user_id}/agents/{agent_id}/schedules",
    response_model=List[ScheduleResponse],
    summary="List scheduled jobs for a user+agent pair",
)
async def list_schedules(
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    jobs = await schedules_q.list_schedules(db, agent_id, user_id)
    return [ScheduleResponse.from_orm(j) for j in jobs]


@router.delete(
    "/{user_id}/agents/{agent_id}/schedules/{schedule_id}",
    summary="Delete a scheduled job",
)
async def delete_schedule(
    user_id: uuid.UUID,
    agent_id: uuid.UUID,
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    deleted = await schedules_q.delete_schedule(db, schedule_id, agent_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": True}

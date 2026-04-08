"""Notification REST endpoints.

GET   /users/{user_id}/notifications               — list (newest first)
PATCH /users/{user_id}/notifications/{id}/read     — mark one read
PATCH /users/{user_id}/notifications/read-all      — mark all read
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import notifications as notifications_q

router = APIRouter(prefix="/users", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    body: str
    type: str
    read: bool
    metadata: Optional[Dict[str, Any]]
    created_at: str

    @classmethod
    def from_orm(cls, row) -> "NotificationResponse":
        return cls(
            id=row.id,
            agent_id=row.agent_id,
            title=row.title,
            body=row.body,
            type=row.type,
            read=row.read,
            metadata=row.extra_metadata,
            created_at=row.created_at.isoformat(),
        )


@router.get(
    "/{user_id}/notifications",
    response_model=List[NotificationResponse],
    summary="List notifications for a user",
)
async def list_notifications(
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    rows = await notifications_q.list_notifications(db, user_id, unread_only=unread_only, limit=limit)
    return [NotificationResponse.from_orm(r) for r in rows]


@router.patch(
    "/{user_id}/notifications/{notification_id}/read",
    summary="Mark a notification as read",
)
async def mark_read(
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    ok = await notifications_q.mark_read(db, notification_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"read": True}


@router.patch(
    "/{user_id}/notifications/read-all",
    summary="Mark all notifications as read",
)
async def mark_all_read(
    user_id: uuid.UUID,
    agent_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_session),
):
    count = await notifications_q.mark_all_read(db, user_id, agent_id=agent_id)
    return {"marked_read": count}

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    anthropic_session_id: str
    created_at: datetime


class SessionEventResponse(BaseModel):
    event_index: int
    type: str
    title: str | None
    body: str


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID

    created_at: datetime
    events: list[SessionEventResponse]

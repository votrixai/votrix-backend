import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionCreateRequest(BaseModel):
    agent_id: str       # template slug, e.g. "marketing-agent"
    display_name: str   # human-readable session name


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    session_id: str
    created_at: datetime


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
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

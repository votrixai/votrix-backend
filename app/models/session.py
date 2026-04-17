import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    agent_slug: str = Field(..., description="Agent template slug, e.g. 'marketing-agent'")


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    agent_slug: str | None
    session_id: str
    created_at: datetime


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_session_title: str | None = None
    agent_slug: str | None = None
    created_at: datetime


class SessionEventResponse(BaseModel):
    event_index: int
    type: str
    title: str | None
    body: str


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    agent_slug: str | None = None
    created_at: datetime
    events: list[SessionEventResponse]

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    agent_slug: str = Field(..., description="Agent template slug, e.g. 'marketing-agent'")


class SessionCreateResponse(BaseModel):
    id: str  # Anthropic provider session ID
    user_id: uuid.UUID
    agent_slug: str | None
    created_at: datetime


class SessionResponse(BaseModel):
    id: str
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
    id: str
    user_id: uuid.UUID
    agent_slug: str | None = None
    created_at: datetime
    events: list[SessionEventResponse]

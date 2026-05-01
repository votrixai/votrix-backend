import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    agent_slug: str = Field(..., description="Agent template slug, e.g. 'marketing-agent'")


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    provider_session_id: str
    agent_blueprint_id: uuid.UUID | None = None
    created_at: datetime


class SessionResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str | None = None
    agent_blueprint_id: uuid.UUID | None = None
    created_at: datetime


class SessionEventResponse(BaseModel):
    event_index: int
    event_type: str
    title: str | None
    body: str


class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_blueprint_id: uuid.UUID | None = None
    created_at: datetime
    events: list[SessionEventResponse]


class SessionFileResponse(BaseModel):
    file_id: str
    filename: str | None = None
    mime_type: str | None = None

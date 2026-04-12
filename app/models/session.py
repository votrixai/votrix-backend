import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Internal session models (used by sessions router)
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
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


# ---------------------------------------------------------------------------
# Anthropic Managed Agents — session schemas
# ---------------------------------------------------------------------------

class SessionStatus(StrEnum):
    rescheduling = "rescheduling"
    running = "running"
    idle = "idle"
    terminated = "terminated"


class Session(BaseModel):
    id: str
    status: SessionStatus
    agent_id: str
    environment_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateSessionRequest(BaseModel):
    agent: str          # agent_id
    environment_id: str


class SessionListResponse(BaseModel):
    data: list[Session]
    next_page: str | None = None

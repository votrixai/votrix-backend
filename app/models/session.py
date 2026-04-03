"""Pydantic models for session history API."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SessionEventType(str, Enum):
    user_message = "user_message"
    ai_message = "ai_message"
    tool_start = "tool_start"
    tool_end = "tool_end"
    error = "error"
    snapshot = "snapshot"


class SessionEventResponse(BaseModel):
    """One event inside a session — mirrors proto SessionEvent."""
    id: str
    sequence_no: int
    event_type: SessionEventType
    event_title: Optional[str] = None   # tool name, snapshot label, etc.
    event_body: str                      # message text / tool args+result / snapshot JSON
    occurred_at: datetime
    created_at: datetime


class SessionResponse(BaseModel):
    """Full session with its events — mirrors proto Session."""
    id: str
    agent_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    events: List[SessionEventResponse] = Field(default_factory=list)


class SessionSummaryResponse(BaseModel):
    """Lightweight session info for list endpoints."""
    id: str
    agent_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    event_count: int = 0


class SessionListResponse(BaseModel):
    sessions: List[SessionSummaryResponse]
    total: int
    page_offset: int
    page_size: int

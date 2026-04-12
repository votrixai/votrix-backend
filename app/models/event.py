"""Anthropic Managed Agents — event schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Content blocks
# ---------------------------------------------------------------------------

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


# ---------------------------------------------------------------------------
# User events (sent TO the agent)
# ---------------------------------------------------------------------------

class UserMessageEvent(BaseModel):
    type: Literal["user.message"] = "user.message"
    content: list[TextBlock]


class UserInterruptEvent(BaseModel):
    type: Literal["user.interrupt"] = "user.interrupt"


class SendEventsRequest(BaseModel):
    events: list[UserMessageEvent | UserInterruptEvent]


# ---------------------------------------------------------------------------
# Agent events (received FROM the agent)
# ---------------------------------------------------------------------------

class AgentMessageEvent(BaseModel):
    type: Literal["agent.message"] = "agent.message"
    id: str
    content: list[TextBlock]
    processed_at: datetime | None = None


class AgentToolUseEvent(BaseModel):
    type: Literal["agent.tool_use"] = "agent.tool_use"
    id: str
    name: str
    input: dict[str, Any]
    processed_at: datetime | None = None


class AgentToolResultEvent(BaseModel):
    type: Literal["agent.tool_result"] = "agent.tool_result"
    id: str
    tool_use_id: str
    content: list[TextBlock] | None = None
    is_error: bool = False
    processed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Session status events
# ---------------------------------------------------------------------------

class SessionStatusRunningEvent(BaseModel):
    type: Literal["session.status_running"] = "session.status_running"
    id: str
    processed_at: datetime | None = None


class SessionStatusIdleEvent(BaseModel):
    type: Literal["session.status_idle"] = "session.status_idle"
    id: str
    processed_at: datetime | None = None


class ErrorDetail(BaseModel):
    message: str


class SessionErrorEvent(BaseModel):
    type: Literal["session.error"] = "session.error"
    id: str
    error: ErrorDetail | None = None
    processed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Event list response
# ---------------------------------------------------------------------------

SessionEvent = (
    AgentMessageEvent
    | AgentToolUseEvent
    | AgentToolResultEvent
    | SessionStatusRunningEvent
    | SessionStatusIdleEvent
    | SessionErrorEvent
)


class EventListResponse(BaseModel):
    data: list[SessionEvent]
    next_page: str | None = None

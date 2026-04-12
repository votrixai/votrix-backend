"""Conversation sessions and events."""

import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Provider-agnostic session ID — set once created, used for reconnects
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI provider snapshotted at session creation (e.g. "anthropic")
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Managed agent ID snapshotted at session creation
    agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class SessionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "session_events"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # user_message | ai_message | tool_start | tool_end | error
    type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

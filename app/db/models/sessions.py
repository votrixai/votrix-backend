"""Conversation sessions and events."""

import uuid

from sqlalchemy import ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Anthropic session id — used for reconnects
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI provider snapshotted at session creation (e.g. "anthropic")
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Anthropic managed agent id snapshotted at session creation
    agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Agent template slug (e.g. "marketing-agent") — used for sidebar filtering
    agent_slug: Mapped[str | None] = mapped_column(Text, nullable=True)


class SessionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "session_events"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # user_message | ai_message | tool_start | tool_end | error
    type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

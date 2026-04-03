"""ORM models for session history: sessions + session_events tables."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One conversation thread between a user and an agent."""
    __tablename__ = "sessions"
    _short_id_prefix = "sess"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    events: Mapped[List["SessionEvent"]] = relationship(
        "SessionEvent",
        cascade="all, delete-orphan",
        order_by="SessionEvent.sequence_no",
        lazy="noload",  # never eagerly loaded; callers fetch explicitly
    )


class SessionEvent(UUIDPrimaryKeyMixin, Base):
    """One recorded event within a session."""
    __tablename__ = "session_events"
    _short_id_prefix = "ev"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)   # SessionEventType value
    event_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

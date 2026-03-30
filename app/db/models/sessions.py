"""ORM models for sessions + session_events tables."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    end_user_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    channel_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="web")
    labels: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SessionEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "session_events"
    __table_args__ = (
        UniqueConstraint("session_id", "seq"),
        Index("idx_session_events_lookup", "session_id", "seq"),
    )

    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    event_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

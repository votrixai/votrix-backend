"""Recurring scheduled jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Schedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schedules"

    session_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    cron_expr: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

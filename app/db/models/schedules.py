"""Recurring scheduled jobs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Schedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schedules"

    cron_expression: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

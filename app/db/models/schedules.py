"""ORM model for the user_agent_schedules table."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserAgentSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_agent_schedules"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("end_user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The message sent to the agent when the job fires, e.g. "[cron] 内容创作"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Standard cron expression, minute field must be 0/15/30/45
    cron_expr: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Each job owns one persistent session — all firings of this job send to the same thread
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Scheduler polls WHERE next_run_at <= NOW() — keep this indexed
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

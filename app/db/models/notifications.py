"""ORM model for user_notifications table."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserNotification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("end_user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # e.g. "cron_content", "cron_review", "cron_analytics"
    type: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Free-form metadata: session_id, job_id, file paths, counts, etc.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

"""Per-user per-template provisioned Anthropic agent cache."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, UUIDPrimaryKeyMixin


class UserAgent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_agents"
    __table_args__ = (UniqueConstraint("user_id", "agent_slug", name="uq_user_agents_user_slug"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_slug: Mapped[str] = mapped_column(Text, nullable=False)
    anthropic_agent_id: Mapped[str] = mapped_column(Text, nullable=False)

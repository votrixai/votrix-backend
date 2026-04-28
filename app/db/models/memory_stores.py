"""Per-user per-agent memory store mapping."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class UserAgentMemoryStore(Base):
    __tablename__ = "user_agent_memory_stores"
    __table_args__ = (UniqueConstraint("user_id", "agent_slug", name="uq_memory_stores_user_slug"),)

    store_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_slug: Mapped[str] = mapped_column(Text, nullable=False)

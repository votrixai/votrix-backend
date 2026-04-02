"""ORM model for the end_user_agents table (many-to-many)."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EndUserAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "end_user_agents"
    _short_id_prefix = "link"
    __table_args__ = (
        UniqueConstraint("end_user_account_id", "blueprint_agent_id"),
    )

    end_user_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_user_accounts.id", ondelete="CASCADE"), nullable=False
    )
    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False
    )

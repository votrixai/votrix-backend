"""ORM model for the blueprint_agents table."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.db.models.blueprint_agent_integrations import BlueprintAgentIntegration

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agents"
    _short_id_prefix = "agent"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    model: Mapped[str] = mapped_column(Text, nullable=False, server_default="claude-sonnet-4-6")

    enabled_integrations: Mapped[List["BlueprintAgentIntegration"]] = relationship(
        "BlueprintAgentIntegration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

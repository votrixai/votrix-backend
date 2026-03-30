"""ORM model for the blueprint_agents table."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent_integrations import AgentIntegration


class BlueprintAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agents"
    __table_args__ = (
        UniqueConstraint("org_id", "slug"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    integrations: Mapped[List["AgentIntegration"]] = relationship(
        "AgentIntegration",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

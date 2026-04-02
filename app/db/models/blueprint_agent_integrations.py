"""ORM model for the blueprint_agent_integrations table."""

import uuid

from sqlalchemy import ARRAY, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agent_integrations"
    __table_args__ = (
        UniqueConstraint(
            "blueprint_agent_id", "integration_slug",
            name="uq_blueprint_agent_integration_slug",
        ),
    )

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    integration_slug: Mapped[str] = mapped_column(Text, nullable=False)
    deferred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    enabled_tool_slugs: Mapped[list] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )


"""ORM model for the blueprint_agent_tools table."""

import uuid

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgentTool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agent_tools"
    _short_id_prefix = "bat"
    __table_args__ = (
        UniqueConstraint(
            "blueprint_agent_id", "tool_id",
            name="uq_blueprint_agent_tool",
        ),
        Index("ix_bat_tool_id", "tool_id"),
        Index("ix_bat_integration_slug", "integration_slug"),
    )

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_id: Mapped[str] = mapped_column(Text, nullable=False)
    integration_slug: Mapped[str] = mapped_column(Text, nullable=False)

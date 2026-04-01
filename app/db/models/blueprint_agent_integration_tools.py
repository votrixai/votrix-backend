"""ORM model for the blueprint_agent_integration_tools join table."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgentIntegrationTool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agent_integration_tools"
    _short_id_prefix = "bat"
    __table_args__ = (
        UniqueConstraint(
            "blueprint_agent_integration_id", "agent_integration_tool_id",
            name="uq_blueprint_agent_integration_tool",
        ),
    )

    blueprint_agent_integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agent_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_integration_tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_integration_tools.id", ondelete="CASCADE"),
        nullable=False,
    )

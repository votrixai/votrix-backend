"""ORM model for the blueprint_agent_integrations join table."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agent_integrations"
    _short_id_prefix = "bai"
    __table_args__ = (
        UniqueConstraint(
            "blueprint_agent_id", "agent_integration_id",
            name="uq_blueprint_agent_integration",
        ),
    )

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprint_agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )

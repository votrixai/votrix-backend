"""ORM model for per-agent integration entries."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_integrations"
    __table_args__ = (UniqueConstraint("blueprint_agent_id", "integration_slug"),)

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False
    )
    integration_slug: Mapped[str] = mapped_column(Text, nullable=False)

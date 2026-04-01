"""ORM model for the agent_integration_tools table (tools belonging to an integration)."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentIntegrationTool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_integration_tools"
    _short_id_prefix = "tool"
    __table_args__ = (
        UniqueConstraint("agent_integration_id", "slug", name="uq_integration_tool_slug"),
    )

    agent_integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

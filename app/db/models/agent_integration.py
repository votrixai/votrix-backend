"""ORM model for per-agent integration entries (docs/tools.md §2 AgentIntegration)."""

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_integrations"
    __table_args__ = (UniqueConstraint("agent_id", "integration_id"),)

    agent_id: Mapped[str] = mapped_column(
        Text, ForeignKey("agent_config.agent_id", ondelete="CASCADE"), nullable=False
    )
    integration_id: Mapped[str] = mapped_column(Text, nullable=False)
    enabled_tool_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )

"""ORM model for the agent_config table."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.agent_integration import AgentIntegration


class AgentConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_config"
    __table_args__ = (
        UniqueConstraint("org_id", "agent_id"),
        UniqueConstraint("agent_id"),
    )

    org_id: Mapped[str] = mapped_column(
        Text, ForeignKey("orgs.org_id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    agent_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    integrations: Mapped[List["AgentIntegration"]] = relationship(
        "AgentIntegration",
        primaryjoin="AgentConfig.agent_id == foreign(AgentIntegration.agent_id)",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

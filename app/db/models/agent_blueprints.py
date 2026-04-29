"""Per-template provisioned Anthropic agent cache."""

import enum
import uuid

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin


class AgentProvider(str, enum.Enum):
    anthropic = "anthropic"


class AgentBlueprint(TimestampMixin, Base):
    __tablename__ = "agent_blueprints"

    # Caller-provided UUID from config.agentId — stable, never auto-generated
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provider_agent_id: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[AgentProvider] = mapped_column(
        Text, nullable=False, server_default=AgentProvider.anthropic.value
    )

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="blueprint")
    agent_employees: Mapped[list["AgentEmployee"]] = relationship("AgentEmployee", back_populates="blueprint")

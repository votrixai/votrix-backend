"""Per-template provisioned Anthropic agent cache."""

import enum

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentProvider(str, enum.Enum):
    anthropic = "anthropic"


class AgentBlueprint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_blueprints"

    provider_agent_id: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[AgentProvider] = mapped_column(
        Text, nullable=False, server_default=AgentProvider.anthropic.value
    )

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="blueprint")
    agent_employees: Mapped[list["AgentEmployee"]] = relationship("AgentEmployee", back_populates="blueprint")

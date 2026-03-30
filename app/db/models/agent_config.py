"""ORM model for the agent_config table."""

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

_DEFAULT_REGISTRY = """{
    "bootstrap_complete": false,
    "modules": {},
    "connections": {},
    "timezone": "UTC"
  }"""


class AgentConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_config"
    __table_args__ = (
        UniqueConstraint("org_id", "agent_id"),
    )

    org_id: Mapped[str] = mapped_column(
        Text, ForeignKey("orgs.org_id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")

    prompt_identity: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prompt_soul: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prompt_agents: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prompt_user: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prompt_tools: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prompt_bootstrap: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    registry: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text(f"'{_DEFAULT_REGISTRY}'::jsonb")
    )

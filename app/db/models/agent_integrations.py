"""ORM model for the agent_integrations table (global integration catalog)."""

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_integrations"
    _short_id_prefix = "integ"

    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    provider_slug: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    provider_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

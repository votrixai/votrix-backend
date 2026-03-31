"""ORM model for the blueprint_agents table."""

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BlueprintAgent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_agents"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    integrations: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")

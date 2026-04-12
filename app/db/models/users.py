"""End user accounts."""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Which agent template this user is connected to
    agent_slug: Mapped[str] = mapped_column(Text, nullable=False)
    # Anthropic per-user managed agent ID — set once by POST /users/{id}/provision
    anthropic_agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)

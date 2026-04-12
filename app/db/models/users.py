"""End user accounts."""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    # Provider-agnostic managed agent ID — set once by POST /users/{id}/provision
    agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI provider (e.g. "anthropic")
    provider: Mapped[str] = mapped_column(Text, nullable=False, server_default="anthropic")

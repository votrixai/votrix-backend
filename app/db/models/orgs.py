"""ORM model for the orgs table."""

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Org(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orgs"

    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="UTC")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

"""ORM model for the guidelines table."""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Guideline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "guidelines"

    guideline_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

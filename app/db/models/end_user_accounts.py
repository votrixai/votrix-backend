"""ORM model for the end_user_accounts table."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EndUserAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "end_user_accounts"
    __table_args__ = (
        UniqueConstraint("org_id", "end_user_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    end_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    sandbox: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

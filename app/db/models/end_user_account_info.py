"""ORM model for the end_user_account_info table."""

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EndUserAccountInfo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "end_user_account_info"
    __table_args__ = (
        UniqueConstraint("org_id", "agent_id", "end_user_id"),
    )

    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    end_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

"""ORM model for the user_files table."""

import uuid
from typing import Optional

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.blueprint_files import NodeType


class UserFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_files"
    _short_id_prefix = "file"
    __table_args__ = (
        UniqueConstraint("blueprint_agent_id", "user_account_id", "path"),
        Index("idx_user_files_by_user", "blueprint_agent_id", "user_account_id"),
        Index("idx_user_files_ls", "blueprint_agent_id", "user_account_id", "parent"),
        Index("idx_user_files_glob", "blueprint_agent_id", "path", postgresql_ops={"path": "text_pattern_ops"}),
    )

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False
    )
    user_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("end_user_accounts.id", ondelete="CASCADE"), nullable=False
    )

    path: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NodeType] = mapped_column(
        SAEnum(NodeType, name="node_type", create_type=False),
        nullable=False,
        server_default="file",
    )

    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="")
    mime_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="text/markdown")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file_class: Mapped[str] = mapped_column(Text, nullable=False, server_default="file")

    parent: Mapped[str] = mapped_column(Text, nullable=False, server_default="/")
    ext: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_by: Mapped[str] = mapped_column(Text, nullable=False, server_default="system")

"""ORM model for the blueprint_files table."""

import enum
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


class NodeType(str, enum.Enum):
    file = "file"
    directory = "directory"


class BlueprintFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_files"
    __table_args__ = (
        UniqueConstraint("blueprint_agent_id", "path"),
        Index("idx_blueprint_ls", "blueprint_agent_id", "parent"),
        Index("idx_blueprint_glob", "blueprint_agent_id", "path", postgresql_ops={"path": "text_pattern_ops"}),
        Index("idx_blueprint_class", "blueprint_agent_id", "file_class"),
    )

    blueprint_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False
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

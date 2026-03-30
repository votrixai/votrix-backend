"""ORM model for the blueprint_files table."""

from sqlalchemy import (
    Enum as SAEnum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

import enum


class NodeType(str, enum.Enum):
    file = "file"
    directory = "directory"


class BlueprintFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "blueprint_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "agent_id"],
            ["agent_config.org_id", "agent_config.agent_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("org_id", "agent_id", "path"),
        Index("idx_blueprint_ls", "org_id", "agent_id", "parent"),
        Index("idx_blueprint_glob", "org_id", "agent_id", "path", postgresql_ops={"path": "text_pattern_ops"}),
        Index("idx_blueprint_class", "org_id", "agent_id", "file_class"),
    )

    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")

    path: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NodeType] = mapped_column(
        SAEnum(NodeType, name="node_type", create_type=False),
        nullable=False,
        server_default="file",
    )

    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    mime_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="text/markdown")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    file_class: Mapped[str] = mapped_column(Text, nullable=False, server_default="file")

    parent: Mapped[str] = mapped_column(Text, nullable=False, server_default="/")
    ext: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_by: Mapped[str] = mapped_column(Text, nullable=False, server_default="system")

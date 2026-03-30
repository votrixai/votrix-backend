"""ORM model for the user_files table."""

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
from app.db.models.blueprint_files import NodeType


class UserFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "agent_id"],
            ["agent_config.org_id", "agent_config.agent_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("org_id", "agent_id", "end_user_id", "path"),
        Index("idx_user_files_by_user", "org_id", "agent_id", "end_user_id"),
        Index("idx_user_files_ls", "org_id", "agent_id", "end_user_id", "parent"),
        Index("idx_user_files_glob", "org_id", "agent_id", "path", postgresql_ops={"path": "text_pattern_ops"}),
    )

    org_id: Mapped[str] = mapped_column(Text, nullable=False)
    agent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default="default")
    end_user_id: Mapped[str] = mapped_column(Text, nullable=False)

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

"""Workspaces and workspace membership."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    display_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    members: Mapped[list["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="workspace")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="workspace")
    agent_employees: Mapped[list["AgentEmployee"]] = relationship("AgentEmployee", back_populates="workspace")


class WorkspaceMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="owner")

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="workspace_memberships")

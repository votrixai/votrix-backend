"""Agent employees — hired employee based on agent blueprint within a workspace."""

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentEmployee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_employees"
    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_blueprint_id", name="uq_agent_employees_workspace_id_agent_blueprint_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_blueprint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="agent_employees")
    blueprint: Mapped["AgentBlueprint"] = relationship("AgentBlueprint", back_populates="agent_employees")
    memory_stores: Mapped[list["AgentEmployeeMemoryStore"]] = relationship("AgentEmployeeMemoryStore", back_populates="agent_employee")

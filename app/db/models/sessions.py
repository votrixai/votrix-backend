"""Conversation sessions and events."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    provider_session_id: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    composio_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_blueprint_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_blueprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="sessions")
    blueprint: Mapped["AgentBlueprint | None"] = relationship("AgentBlueprint", back_populates="sessions")
    events: Mapped[list["SessionEvent"]] = relationship(
        "SessionEvent",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SessionEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "session_events"
    __table_args__ = (
        Index("ix_session_events_session_id_event_index", "session_id", "event_index"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    session: Mapped["Session"] = relationship("Session", back_populates="events")

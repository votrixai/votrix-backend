"""Per-employee memory store mapping."""

import uuid

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models._base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentEmployeeMemoryStore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_employee_memory_stores"

    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    provider_memory_store_id: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    agent_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_employee: Mapped["AgentEmployee"] = relationship("AgentEmployee", back_populates="memory_stores")

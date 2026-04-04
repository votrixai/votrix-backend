"""Session history queries — CRUD for sessions + session_events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sessions import Session, SessionEvent


async def create_session_row(
    db: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Session:
    """Insert a new session row with a server-generated id. No events."""
    new_id = uuid.uuid4()
    row = Session(id=new_id, agent_id=agent_id, user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def upsert_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Session:
    """Return existing session or create a new one. Idempotent."""
    row = await db.get(Session, session_id)
    if row:
        return row
    row = Session(id=session_id, agent_id=agent_id, user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def append_event(
    db: AsyncSession,
    session_id: uuid.UUID,
    event_type: str,
    event_body: str,
    *,
    event_title: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> SessionEvent:
    """Append one event to a session. sequence_no is auto-assigned."""
    # Derive next sequence number in the same transaction.
    result = await db.execute(
        select(func.coalesce(func.max(SessionEvent.sequence_no), 0))
        .where(SessionEvent.session_id == session_id)
    )
    next_seq: int = result.scalar_one() + 1

    ev = SessionEvent(
        session_id=session_id,
        sequence_no=next_seq,
        event_type=event_type,
        event_title=event_title,
        event_body=event_body,
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def get_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    include_events: bool = True,
) -> Optional[Tuple[Session, List[SessionEvent]]]:
    """Return (session, events) or None if not found."""
    row = await db.get(Session, session_id)
    if not row:
        return None

    events: List[SessionEvent] = []
    if include_events:
        result = await db.execute(
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id)
            .order_by(SessionEvent.sequence_no)
        )
        events = list(result.scalars().all())

    return row, events


async def end_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Optional[Tuple[Session, List[SessionEvent]]]:
    """Set ended_at = now(). Idempotent. Returns (session, events) or None."""
    stmt = (
        update(Session)
        .where(Session.id == session_id, Session.ended_at.is_(None))
        .values(ended_at=func.now())
    )
    await db.execute(stmt)
    await db.commit()
    return await get_session(db, session_id, include_events=True)


# ---------------------------------------------------------------------------
# List helpers (with event_count, paginated)
# ---------------------------------------------------------------------------

class _SessionRow:
    """Thin wrapper so the router can access .event_count uniformly."""
    __slots__ = ("id", "agent_id", "user_id", "started_at", "ended_at", "event_count")

    def __init__(self, session: Session, event_count: int) -> None:
        self.id = session.id
        self.agent_id = session.agent_id
        self.user_id = session.user_id
        self.started_at = session.created_at   # created_at == session start
        self.ended_at = session.ended_at
        self.event_count = event_count


async def list_sessions(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    page_offset: int = 0,
    page_size: int = 20,
) -> Tuple[List[_SessionRow], int]:
    """Return (page, total) filtered by user and/or agent."""
    count_sub = (
        select(SessionEvent.session_id, func.count().label("cnt"))
        .group_by(SessionEvent.session_id)
        .subquery()
    )

    base = (
        select(Session, func.coalesce(count_sub.c.cnt, 0).label("event_count"))
        .outerjoin(count_sub, Session.id == count_sub.c.session_id)
    )

    if user_id is not None:
        base = base.where(Session.user_id == user_id)
    if agent_id is not None:
        base = base.where(Session.agent_id == agent_id)

    total_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total: int = total_result.scalar_one()

    paged = base.order_by(Session.created_at.desc()).offset(page_offset).limit(page_size)
    rows = (await db.execute(paged)).all()

    return [_SessionRow(r.Session, r.event_count) for r in rows], total

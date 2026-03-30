"""Session + session event queries."""

from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sessions import Session, SessionEvent


def _session_to_dict(row: Session) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in Session.__table__.columns}


def _event_to_dict(row: SessionEvent) -> Dict[str, Any]:
    return {c.key: getattr(row, c.key) for c in SessionEvent.__table__.columns}


async def get_session(
    session: AsyncSession, session_id: str, events_limit: int = 150
) -> Optional[Dict[str, Any]]:
    """Fetch session with its most recent events."""
    stmt = select(Session).where(Session.session_id == session_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        return None
    data = _session_to_dict(row)

    events_stmt = (
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.seq)
        .limit(events_limit)
    )
    events_result = await session.execute(events_stmt)
    data["events"] = [_event_to_dict(e) for e in events_result.scalars()]
    return data


async def create_session(
    session: AsyncSession,
    session_id: str, org_id: str, agent_id: str = "default", channel_type: str = "web"
) -> Dict[str, Any]:
    values = {
        "session_id": session_id,
        "org_id": org_id,
        "agent_id": agent_id,
        "channel_type": channel_type,
    }
    stmt = (
        pg_insert(Session)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["session_id"],
            set_={"channel_type": channel_type},
        )
        .returning(Session)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _session_to_dict(result.scalar_one())


async def log_event(
    session: AsyncSession,
    session_id: str,
    seq: int,
    event_type: str,
    event_body: str,
    event_title: Optional[str] = None,
) -> Dict[str, Any]:
    obj = SessionEvent(
        session_id=session_id,
        seq=seq,
        event_type=event_type,
        event_body=event_body,
        event_title=event_title,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _event_to_dict(obj)


async def update_summary(session: AsyncSession, session_id: str, summary: str) -> None:
    stmt = (
        update(Session)
        .where(Session.session_id == session_id)
        .values(summary=summary)
    )
    await session.execute(stmt)
    await session.commit()


async def update_labels(session: AsyncSession, session_id: str, labels: List[str]) -> None:
    stmt = (
        update(Session)
        .where(Session.session_id == session_id)
        .values(labels=labels)
    )
    await session.execute(stmt)
    await session.commit()

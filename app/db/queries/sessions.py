import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sessions import Session, SessionEvent


async def create_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    agent_slug: str,
) -> Session:
    session = Session(id=session_id, user_id=user_id, agent_slug=agent_slug)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def save_anthropic_session_id(
    db: AsyncSession, session_id: uuid.UUID, anthropic_session_id: str
) -> None:
    session = await get_session(db, session_id)
    if session:
        session.anthropic_session_id = anthropic_session_id
        await db.commit()


async def list_sessions(
    db: AsyncSession, user_id: uuid.UUID
) -> Sequence[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
    )
    return result.scalars().all()


async def append_event(
    db: AsyncSession,
    session_id: uuid.UUID,
    event_type: str,
    body: str,
    title: str | None = None,
) -> SessionEvent:
    # next event_index
    result = await db.execute(
        select(SessionEvent.event_index)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.event_index.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    next_index = (last + 1) if last is not None else 0

    event = SessionEvent(
        session_id=session_id,
        event_index=next_index,
        type=event_type,
        title=title,
        body=body,
    )
    db.add(event)
    await db.commit()
    return event


async def get_events(
    db: AsyncSession, session_id: uuid.UUID
) -> Sequence[SessionEvent]:
    result = await db.execute(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.event_index)
    )
    return result.scalars().all()


async def delete_session(db: AsyncSession, session_id: uuid.UUID) -> bool:
    session = await get_session(db, session_id)
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True

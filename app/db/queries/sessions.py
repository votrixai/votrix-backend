import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sessions import Session, SessionEvent


async def create_session(
    db: AsyncSession,
    session_id: str,
    user_id: uuid.UUID,
    agent_slug: str | None = None,
    agent_id: str | None = None,
) -> Session:
    session = Session(
        id=session_id,
        user_id=user_id,
        agent_slug=agent_slug,
        agent_id=agent_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession, user_id: uuid.UUID, agent_slug: str | None = None
) -> Sequence[Session]:
    stmt = select(Session).where(Session.user_id == user_id)
    if agent_slug is not None:
        stmt = stmt.where(Session.agent_slug == agent_slug)
    result = await db.execute(stmt.order_by(Session.created_at.desc()))
    return result.scalars().all()


async def update_provider_session_title(
    db: AsyncSession, session_id: str, title: str
) -> None:
    session = await get_session(db, session_id)
    if not session:
        return
    session.provider_session_title = title
    await db.commit()


async def append_event(
    db: AsyncSession,
    session_id: str,
    event_type: str,
    body: str,
    title: str | None = None,
) -> SessionEvent:
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
    db: AsyncSession, session_id: str
) -> Sequence[SessionEvent]:
    result = await db.execute(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.event_index)
    )
    return result.scalars().all()


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    session = await get_session(db, session_id)
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True

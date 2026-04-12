import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.users import User


async def create_user(
    db: AsyncSession,
    display_name: str,
    agent_slug: str,
) -> User:
    user = User(display_name=display_name, agent_slug=agent_slug)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, agent_slug: str | None = None) -> Sequence[User]:
    q = select(User)
    if agent_slug:
        q = q.where(User.agent_slug == agent_slug)
    result = await db.execute(q.order_by(User.created_at.desc()))
    return result.scalars().all()


async def set_anthropic_agent_id(
    db: AsyncSession, user_id: uuid.UUID, anthropic_agent_id: str
) -> None:
    user = await get_user(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    user.anthropic_agent_id = anthropic_agent_id
    await db.commit()


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    user = await get_user(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True

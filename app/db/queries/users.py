import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.users import User


async def create_user(
    db: AsyncSession,
    display_name: str,
) -> User:
    user = User(display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_display_name(
    db: AsyncSession, user_id: uuid.UUID, display_name: str
) -> User | None:
    user = await get_user(db, user_id)
    if not user:
        return None
    user.display_name = display_name
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


async def set_agent_id(
    db: AsyncSession, user_id: uuid.UUID, agent_id: str
) -> None:
    user = await get_user(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    user.agent_id = agent_id
    await db.commit()


async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
    user = await get_user(db, user_id)
    if not user:
        return False
    await db.delete(user)
    await db.commit()
    return True

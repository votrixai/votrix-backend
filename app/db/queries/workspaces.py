"""Workspace and membership queries."""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workspaces import Workspace, WorkspaceMember


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    return result.scalar_one_or_none()


async def get_user_workspaces(db: AsyncSession, user_id: uuid.UUID) -> Sequence[tuple[Workspace, str]]:
    """Return (workspace, role) tuples for a user."""
    result = await db.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at.desc())
    )
    return result.all()


async def get_member_role(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def is_member(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None

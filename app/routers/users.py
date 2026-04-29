"""
User management routes.

GET    /users/me                    current user profile + workspaces
PATCH  /users/me                    update current user profile (display_name)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session
from app.db.queries import users as users_q
from app.db.queries import workspaces as workspaces_q
from app.models.user import UserResponse, WorkspaceResponse

router = APIRouter(prefix="/users", tags=["users"])


class UpdateUserRequest(BaseModel):
    display_name: str


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    user = await users_q.get_user(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found (trigger missed?)")
    rows = await workspaces_q.get_user_workspaces(db, current_user.id)
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        created_at=user.created_at,
        workspaces=[
            WorkspaceResponse(
                id=w.id,
                display_name=w.display_name,
                role=role,
                created_at=w.created_at,
            )
            for w, role in rows
        ],
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    user = await users_q.update_display_name(db, current_user.id, body.display_name)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return UserResponse(id=user.id, display_name=user.display_name, created_at=user.created_at)

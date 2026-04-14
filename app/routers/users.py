"""
User management routes.

POST   /users                       create user
GET    /users                       list users
GET    /users/{id}                  get user + sessions
DELETE /users/{id}                  delete user
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import sessions as sessions_q
from app.db.queries import users as users_q
from app.models.session import SessionResponse
from app.models.user import CreateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_session),
):
    user = await users_q.create_user(db, body.display_name)
    return UserResponse(id=user.id, display_name=user.display_name, created_at=user.created_at)


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_session),
):
    rows = await users_q.list_users(db)
    return [
        UserResponse(id=r.id, display_name=r.display_name, created_at=r.created_at)
        for r in rows
    ]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    user = await users_q.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    sessions = await sessions_q.list_sessions(db, user_id)
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        created_at=user.created_at,
        sessions=[
            SessionResponse(id=s.id, user_id=s.user_id, display_name=s.display_name, created_at=s.created_at)
            for s in sessions
        ],
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    deleted = await users_q.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

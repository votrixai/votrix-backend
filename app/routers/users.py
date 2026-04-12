"""
User management routes.

POST   /users                       create user
GET    /users                       list users
GET    /users/{id}                  get user
DELETE /users/{id}                  delete user
POST   /users/{id}/provision        provision per-user managed agent (idempotent)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import users as users_q
from app.management import provisioning
from app.models.user import CreateUserRequest, ProvisionResponse, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_session),
):
    user = await users_q.create_user(db, body.display_name)
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        agent_id=user.agent_id,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_session),
):
    rows = await users_q.list_users(db)
    return [
        UserResponse(
            id=r.id,
            display_name=r.display_name,
            agent_id=r.agent_id,
            created_at=r.created_at,
        )
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
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        agent_id=user.agent_id,
        created_at=user.created_at,
    )


@router.post("/{user_id}/provision", response_model=ProvisionResponse)
async def provision_user(
    user_id: uuid.UUID,
    agent_slug: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Create a per-user managed agent for this user.
    Idempotent — returns existing agent_id if already provisioned.
    agent_slug: the agent template to provision against (e.g. "marketing-agent")
    """
    user = await users_q.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.agent_id:
        return ProvisionResponse(
            agent_id=user.agent_id,
            provisioned=False,
        )

    agent_id = provisioning.create_user_agent(
        slug=agent_slug,
        user_id=str(user.id),
        display_name=user.display_name,
    )
    await users_q.set_agent_id(db, user.id, agent_id)

    return ProvisionResponse(agent_id=agent_id, provisioned=True)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    deleted = await users_q.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

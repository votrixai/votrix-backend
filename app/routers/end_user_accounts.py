"""End user account CRUD API + agent instantiation.

Routes:
  POST   /orgs/{org_id}/users                                          — create end user account (org-scoped)
  GET    /orgs/{org_id}/users                                          — list end user accounts (org-scoped)
  GET    /users/{user_id}                                              — get end user account
  PATCH  /users/{user_id}                                              — update end user account
  DELETE /users/{user_id}                                              — delete end user account
  POST   /users/{user_id}/agents                                       — instantiate blueprint agent for user
  GET    /users/{user_id}/agents                                       — list user's agents
  DELETE /users/{user_id}/agents/{blueprint_agent_id}                   — unlink agent from user
"""

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries.end_user_accounts import (
    create_end_user_account,
    delete_end_user_account,
    get_end_user_account,
    list_end_user_accounts,
    update_end_user_account,
)
from app.db.queries.end_user_agent_links import (
    link_agent,
    list_links_for_account,
    replicate_blueprint_to_user,
    unlink_agent,
)
from app.models.end_user_account import (
    CreateEndUserAccountRequest,
    EndUserAccountDetail,
    EndUserAccountSummary,
    UpdateEndUserAccountRequest,
)

router = APIRouter()


# ── Pydantic models for agent instantiation ──────────────────

class CreateEndUserAgentRequest(BaseModel):
    blueprint_agent_id: str


class EndUserAgentLink(BaseModel):
    id: str
    end_user_account_id: str
    blueprint_agent_id: str
    created_at: datetime


# ── Helpers ──────────────────────────────────────────────────

def _to_detail(row) -> EndUserAccountDetail:
    return EndUserAccountDetail(
        id=str(row.id),
        org_id=str(row.org_id),
        display_name=row.display_name,
        sandbox=row.sandbox,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── Account CRUD (org-scoped: list, create) ──────────────────

@router.post("/orgs/{org_id}/users", response_model=EndUserAccountDetail, status_code=201)
async def create_end_user(
    org_id: uuid.UUID,
    body: CreateEndUserAccountRequest,
    session: AsyncSession = Depends(get_session),
):
    account = await create_end_user_account(
        session, org_id,
        display_name=body.display_name,
        sandbox=body.sandbox,
    )
    await session.commit()
    return _to_detail(account)


@router.get("/orgs/{org_id}/users", response_model=List[EndUserAccountSummary])
async def list_end_users(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    accounts = await list_end_user_accounts(session, org_id)
    return [
        EndUserAccountSummary(
            id=str(a.id),
            display_name=a.display_name,
            sandbox=a.sandbox,
            created_at=a.created_at,
        )
        for a in accounts
    ]


# ── Account CRUD (flat: get, update, delete) ─────────────────

@router.get("/users/{user_id}", response_model=EndUserAccountDetail)
async def get_end_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    account = await get_end_user_account(session, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="End user account not found")
    return _to_detail(account)


@router.patch("/users/{user_id}", response_model=EndUserAccountDetail)
async def update_end_user(
    user_id: uuid.UUID,
    body: UpdateEndUserAccountRequest,
    session: AsyncSession = Depends(get_session),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    account = await update_end_user_account(session, user_id, **updates)
    if account is None:
        raise HTTPException(status_code=404, detail="End user account not found")
    await session.commit()
    return _to_detail(account)


@router.delete("/users/{user_id}", status_code=204)
async def delete_end_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    deleted = await delete_end_user_account(session, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="End user account not found")
    await session.commit()


# ── Agent instantiation (flat) ───────────────────────────────

@router.post(
    "/users/{user_id}/agents",
    response_model=EndUserAgentLink,
    status_code=201,
    summary="Instantiate a blueprint agent for an end user",
)
async def create_end_user_agent(
    user_id: uuid.UUID,
    body: CreateEndUserAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Link a user to a blueprint agent and replicate blueprint files into user files."""
    account = await get_end_user_account(session, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="End user account not found")

    link = await link_agent(session, account.id, body.blueprint_agent_id)
    await replicate_blueprint_to_user(session, link.blueprint_agent_id, account.id)
    await session.commit()

    return EndUserAgentLink(
        id=str(link.id),
        end_user_account_id=str(link.end_user_account_id),
        blueprint_agent_id=str(link.blueprint_agent_id),
        created_at=link.created_at,
    )


@router.get(
    "/users/{user_id}/agents",
    response_model=List[EndUserAgentLink],
    summary="List user's linked agents",
)
async def list_end_user_agents(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    account = await get_end_user_account(session, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="End user account not found")

    links = await list_links_for_account(session, account.id)
    return [
        EndUserAgentLink(
            id=str(l.id),
            end_user_account_id=str(l.end_user_account_id),
            blueprint_agent_id=str(l.blueprint_agent_id),
            created_at=l.created_at,
        )
        for l in links
    ]


@router.delete(
    "/users/{user_id}/agents/{blueprint_agent_id}",
    status_code=204,
    summary="Unlink an agent from a user",
)
async def delete_end_user_agent(
    user_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    account = await get_end_user_account(session, user_id)
    if account is None:
        raise HTTPException(status_code=404, detail="End user account not found")

    deleted = await unlink_agent(session, account.id, blueprint_agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent link not found")
    await session.commit()

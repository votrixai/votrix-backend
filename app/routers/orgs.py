"""Router for org CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries.orgs import create_org, delete_org, get_org, list_orgs, update_org
from app.models.org import CreateOrgRequest, OrgDetail, OrgSummary, UpdateOrgRequest

router = APIRouter(prefix="/orgs")


def _org_detail(org) -> OrgDetail:
    return OrgDetail(
        id=str(org.id),
        display_name=org.display_name,
        timezone=org.timezone,
        metadata=org.metadata_,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.post("", response_model=OrgDetail, status_code=201)
async def create_org_endpoint(body: CreateOrgRequest, session: AsyncSession = Depends(get_session)):
    org = await create_org(session, display_name=body.display_name, timezone=body.timezone, metadata=body.metadata)
    await session.commit()
    return _org_detail(org)


@router.get("", response_model=list[OrgSummary])
async def list_orgs_endpoint(session: AsyncSession = Depends(get_session)):
    orgs = await list_orgs(session)
    return [OrgSummary(id=str(o.id), display_name=o.display_name, created_at=o.created_at) for o in orgs]


@router.get("/{org_id}", response_model=OrgDetail)
async def get_org_endpoint(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    org = await get_org(session, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    return _org_detail(org)


@router.patch("/{org_id}", response_model=OrgDetail)
async def update_org_endpoint(org_id: uuid.UUID, body: UpdateOrgRequest, session: AsyncSession = Depends(get_session)):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    org = await update_org(session, org_id, **updates)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    await session.commit()
    return _org_detail(org)


@router.delete("/{org_id}", status_code=204)
async def delete_org_endpoint(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    deleted = await delete_org(session, org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Org not found")
    await session.commit()

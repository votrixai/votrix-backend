"""Router for org CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries.orgs import create_org, delete_org, get_org, list_orgs, update_org
from app.models.org import CreateOrgRequest, OrgDetailResponse, OrgSummaryResponse, UpdateOrgRequest
from app.integrations.catalog import DEFAULT_ORG_INTEGRATIONS

router = APIRouter(prefix="/orgs", tags=["orgs"])

_404 = {404: {"description": "Org not found"}}
_400 = {400: {"description": "Bad request"}}


def _org_detail(org) -> OrgDetailResponse:
    return OrgDetailResponse(
        id=str(org.id),
        display_name=org.display_name,
        timezone=org.timezone,
        metadata=org.metadata_,
        enabled_integration_slugs=list(org.enabled_integration_slugs or []),
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.get("", response_model=list[OrgSummaryResponse], summary="List orgs")
async def list_orgs_endpoint(session: AsyncSession = Depends(get_session)):
    """Return all orgs (id, display_name, created_at)."""
    orgs = await list_orgs(session)
    return [OrgSummaryResponse(id=str(o.id), display_name=o.display_name, created_at=o.created_at) for o in orgs]


@router.post("", response_model=OrgDetailResponse, status_code=201, summary="Create org")
async def create_org_endpoint(body: CreateOrgRequest, session: AsyncSession = Depends(get_session)):
    """Create a new org. Default integrations are pre-activated."""
    org = await create_org(
        session,
        display_name=body.display_name,
        timezone=body.timezone,
        metadata=body.metadata,
        integrations=DEFAULT_ORG_INTEGRATIONS,
    )
    await session.commit()
    return _org_detail(org)


@router.get("/{org_id}", response_model=OrgDetailResponse, summary="Get org", responses=_404)
async def get_org_endpoint(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Return full org detail including metadata and timestamps."""
    org = await get_org(session, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    return _org_detail(org)


@router.patch("/{org_id}", response_model=OrgDetailResponse, summary="Update org", responses={**_404, **_400})
async def update_org_endpoint(org_id: uuid.UUID, body: UpdateOrgRequest, session: AsyncSession = Depends(get_session)):
    """Partial update — only provided fields are changed."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "enabled_integration_slugs" in updates:
        updates["integrations"] = updates.pop("enabled_integration_slugs")
    org = await update_org(session, org_id, **updates)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    await session.commit()
    return _org_detail(org)


@router.delete("/{org_id}", status_code=204, summary="Delete org", responses=_404)
async def delete_org_endpoint(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Delete org and all associated data (cascade)."""
    deleted = await delete_org(session, org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Org not found")
    await session.commit()

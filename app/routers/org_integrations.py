"""Org integration library API.

An org's integration library is the set of integrations they have activated.
Agents can only use integrations that exist in their org's library.
The platform integration is always available and is not stored in the DB.

Routes:
  GET    /orgs/{org_id}/integrations          — list activated integrations
  POST   /orgs/{org_id}/integrations          — activate an integration
  DELETE /orgs/{org_id}/integrations/{slug}   — deactivate an integration
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import orgs as orgs_q
from app.models.tools import OrgIntegrationItem, ProviderType
from app.tools import cache as composio_cache
from app.tools.registry import PROVIDERS, get_integration

router = APIRouter(prefix="/orgs", tags=["org-integrations"])

_PLATFORM_SLUG = "platform"


class AddIntegrationRequest(BaseModel):
    slug: str


def _provider_type(provider_id: str) -> ProviderType:
    p = PROVIDERS.get(provider_id)
    return p.type if p else ProviderType.UNSPECIFIED


def _slug_to_item(slug: str) -> OrgIntegrationItem | None:
    """Resolve a slug to OrgIntegrationItem from registry or cache."""
    integration = get_integration(slug)
    if integration:
        return OrgIntegrationItem(
            slug=integration.id,
            display_name=integration.display_name,
            description=integration.description,
            provider_type=_provider_type(integration.provider_id),
            tool_count=len(integration.tools),
            categories=[],
        )
    item = composio_cache.get_by_slug(slug)
    if item:
        return OrgIntegrationItem(
            slug=item["slug"],
            display_name=item["name"],
            description=item["description"],
            provider_type=ProviderType.COMPOSIO,
            tool_count=item["tool_count"],
            categories=item.get("categories", []),
        )
    return None


@router.get("/{org_id}/integrations", response_model=List[OrgIntegrationItem],
            summary="List org integrations",
            responses={404: {"description": "Org not found"}})
async def list_org_integrations(
    org_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all integrations activated for this org. Platform is always included."""
    org = await orgs_q.get_org(session, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    slugs = [_PLATFORM_SLUG] + [s for s in (org.integrations or []) if s != _PLATFORM_SLUG]

    items = []
    for slug in slugs:
        item = _slug_to_item(slug)
        if item:
            items.append(item)

    return items


@router.post("/{org_id}/integrations", response_model=OrgIntegrationItem, status_code=201,
             summary="Activate integration for org",
             responses={400: {"description": "platform integration is always available"},
                        404: {"description": "Org or integration not found"}})
async def add_org_integration(
    org_id: uuid.UUID,
    body: AddIntegrationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Activate an integration for this org."""
    slug = body.slug.lower().strip()

    if slug == _PLATFORM_SLUG:
        raise HTTPException(status_code=400, detail="platform integration is always available")

    # Validate slug exists (registry or Composio cache)
    if not get_integration(slug) and not composio_cache.slug_exists(slug):
        raise HTTPException(status_code=404, detail=f"Integration '{slug}' not found")

    org = await orgs_q.add_org_integration(session, org_id, slug)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    await session.commit()

    return _slug_to_item(slug)


@router.delete("/{org_id}/integrations/{slug}", status_code=204,
               summary="Deactivate integration for org",
               responses={400: {"description": "platform integration cannot be removed"},
                          404: {"description": "Org or integration not found"}})
async def remove_org_integration(
    org_id: uuid.UUID,
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Deactivate an integration for this org."""
    if slug == _PLATFORM_SLUG:
        raise HTTPException(status_code=400, detail="platform integration cannot be removed")

    removed = await orgs_q.remove_org_integration(session, org_id, slug)
    if not removed:
        raise HTTPException(status_code=404, detail="Org or integration not found")
    await session.commit()

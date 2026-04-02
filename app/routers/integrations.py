"""Integration catalog API.

Routes:
  GET /integrations               — list all integrations (platform + Composio cache)
  GET /integrations/{slug}        — single integration detail with tools
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.models.integration import IntegrationDetailResponse, IntegrationSummaryResponse, ProviderType, ToolSchemaResponse
from app.integrations import cache as composio_cache
from app.integrations.providers.composio import get_toolkit_detail, get_tool_schemas
from app.integrations.registry import PROVIDERS, get_integration, list_integrations

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _provider_type(provider_slug: str) -> ProviderType:
    p = PROVIDERS.get(provider_slug)
    return p.type if p else ProviderType.UNSPECIFIED


def _summary_from_registry(integration) -> IntegrationSummaryResponse:
    return IntegrationSummaryResponse(
        slug=integration.slug,
        display_name=integration.display_name,
        description=integration.description,
        provider_type=_provider_type(integration.provider_slug),
        deferred=integration.deferred,
        tool_count=len(integration.tools),
    )


def _summary_from_cache(item: dict) -> IntegrationSummaryResponse:
    return IntegrationSummaryResponse(
        slug=item["slug"],
        display_name=item["name"],
        description=item["description"],
        provider_type=ProviderType.COMPOSIO,
        deferred=True,
        tool_count=item["tool_count"],
    )


@router.get("", response_model=List[IntegrationSummaryResponse], summary="List integrations")
async def list_integrations_endpoint(
    search: Optional[str] = Query(None, description="Filter by name or slug"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all available integrations. Platform integrations always appear first."""
    results: list[IntegrationSummaryResponse] = []

    for integration in list_integrations():
        s = _summary_from_registry(integration)
        if search and search.lower() not in s.slug.lower() and search.lower() not in s.display_name.lower():
            continue
        results.append(s)

    cache_items, _ = composio_cache.get_all(
        search=search or "",
        category=category or "",
        limit=10_000,
        offset=0,
    )
    registry_slugs = {i.slug for i in results}
    for item in cache_items:
        if item["slug"] not in registry_slugs:
            results.append(_summary_from_cache(item))

    return results[offset : offset + limit]


@router.get("/{slug}", response_model=IntegrationDetailResponse, summary="Get integration detail",
            responses={404: {"description": "Integration not found"}})
async def get_integration_endpoint(slug: str):
    """Get integration detail with full tool schemas."""
    integration = get_integration(slug)
    if integration:
        return IntegrationDetailResponse(
            slug=integration.slug,
            display_name=integration.display_name,
            description=integration.description,
            provider_type=_provider_type(integration.provider_slug),
            deferred=integration.deferred,
            tools=[
                ToolSchemaResponse(
                    slug=t.slug,
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in integration.tools
            ],
        )

    settings = get_settings()
    toolkit = await get_toolkit_detail(settings.composio_api_key, slug)
    if toolkit is None:
        raise HTTPException(status_code=404, detail=f"Integration '{slug}' not found")

    tool_schemas = await get_tool_schemas(settings.composio_api_key, slug)
    return IntegrationDetailResponse(
        slug=toolkit["slug"],
        display_name=toolkit["name"],
        description=toolkit["description"],
        provider_type=ProviderType.COMPOSIO,
        deferred=True,
        tools=[
            ToolSchemaResponse(
                slug=t["slug"],
                name=t["name"],
                description=t["description"],
                input_schema=t.get("input_schema"),
            )
            for t in tool_schemas
        ],
    )

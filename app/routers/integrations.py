"""Integration catalog API.

Routes:
  GET /integrations               — list all integrations (platform + Composio cache)
  GET /integrations/{slug}        — single integration detail with tools
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.models.tools import IntegrationDetail, IntegrationSummary, ProviderType, ToolSchema
from app.integrations import cache as composio_cache
from app.integrations.providers.composio import get_toolkit_detail, get_tool_schemas
from app.integrations.registry import PROVIDERS, get_integration, list_integrations

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _provider_type(provider_id: str) -> ProviderType:
    p = PROVIDERS.get(provider_id)
    return p.type if p else ProviderType.UNSPECIFIED


def _summary_from_registry(integration) -> IntegrationSummary:
    return IntegrationSummary(
        id=integration.id,
        display_name=integration.display_name,
        description=integration.description,
        provider_type=_provider_type(integration.provider_id),
        deferred=integration.deferred,
        tool_count=len(integration.tools),
    )


def _summary_from_cache(item: dict) -> IntegrationSummary:
    return IntegrationSummary(
        id=item["slug"],
        display_name=item["name"],
        description=item["description"],
        provider_type=ProviderType.COMPOSIO,
        deferred=True,
        tool_count=item["tool_count"],
    )


@router.get("", response_model=List[IntegrationSummary], summary="List integrations")
async def list_integrations_endpoint(
    search: Optional[str] = Query(None, description="Filter by name or slug"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all available integrations. Platform integrations always appear first."""
    results: list[IntegrationSummary] = []

    # --- platform (local registry, always included) ---
    for integration in list_integrations():
        s = _summary_from_registry(integration)
        if search and search.lower() not in s.id.lower() and search.lower() not in s.display_name.lower():
            continue
        results.append(s)

    # --- Composio catalog ---
    cache_items, _ = composio_cache.get_all(
        search=search or "",
        category=category or "",
        limit=10_000,
        offset=0,
    )
    registry_ids = {i.id for i in results}
    for item in cache_items:
        if item["slug"] not in registry_ids:
            results.append(_summary_from_cache(item))

    return results[offset : offset + limit]


@router.get("/{slug}", response_model=IntegrationDetail, summary="Get integration detail",
            responses={404: {"description": "Integration not found"}})
async def get_integration_endpoint(slug: str):
    """Get integration detail with full tool schemas.

    Platform integrations return locally-defined schemas.
    Composio-backed integrations fetch real action schemas from the SDK
    (per-slug cached for 24h).
    """
    # Check local registry first (has full schemas)
    integration = get_integration(slug)
    if integration:
        return IntegrationDetail(
            id=integration.id,
            display_name=integration.display_name,
            description=integration.description,
            provider_type=_provider_type(integration.provider_id),
            deferred=integration.deferred,
            tools=[
                ToolSchema(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in integration.tools
            ],
        )

    # Composio-backed: fetch toolkit metadata + real action schemas from SDK
    settings = get_settings()
    toolkit = await get_toolkit_detail(settings.composio_api_key, slug)
    if toolkit is None:
        raise HTTPException(status_code=404, detail=f"Integration '{slug}' not found")

    tool_schemas = await get_tool_schemas(settings.composio_api_key, slug)
    return IntegrationDetail(
        id=toolkit["slug"],
        display_name=toolkit["name"],
        description=toolkit["description"],
        provider_type=ProviderType.COMPOSIO,
        deferred=True,
        tools=[
            ToolSchema(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                input_schema=t.get("input_schema"),
            )
            for t in tool_schemas
        ],
    )

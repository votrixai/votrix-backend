"""Integration catalog API.

Routes:
  GET /integrations               — list all integrations (platform + Composio cache)
  GET /integrations/{slug}        — single integration detail with tools
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.models.integration import (
    InputSchemaDef, IntegrationDetailResponse, IntegrationSummaryResponse,
    PropertyDef, ProviderType, ToolSchemaResponse,
)
from app.integrations.handlers.composio import warm_toolkit, get_cached_toolkit_schemas
from app.integrations.catalog import PROVIDERS, get_integration, get_cached, list_integrations, get_cached_toolkit_meta

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _provider_type(provider_slug: str) -> ProviderType:
    p = PROVIDERS.get(provider_slug)
    return p.type if p else ProviderType.UNSPECIFIED


def _resolve_type(prop: Dict[str, Any]) -> str:
    """Handle anyOf [{type: X}, {type: null}] → X, fall back to 'string'."""
    if "type" in prop:
        return str(prop["type"])
    for sub in prop.get("anyOf", []):
        if isinstance(sub, dict) and sub.get("type") != "null":
            return str(sub.get("type", "string"))
    return "string"


def _items_type(prop: Dict[str, Any], resolved_type: str) -> Optional[str]:
    """Extract array element type, handling both top-level and anyOf-nested items."""
    if resolved_type != "array":
        return None
    if "items" in prop:
        return prop["items"].get("type")
    for sub in prop.get("anyOf", []):
        if isinstance(sub, dict) and sub.get("type") == "array" and "items" in sub:
            return sub["items"].get("type")
    return None


def _flatten_schema(raw: Optional[Dict[str, Any]]) -> Optional[InputSchemaDef]:
    """JSON Schema object → InputSchemaDef for frontend consumption."""
    if not raw:
        return None
    props = raw.get("properties") or {}
    if not props:
        return None
    required_set = set(raw.get("required") or [])
    return InputSchemaDef(
        properties={
            name: PropertyDef(
                type=(t := _resolve_type(prop)),
                description=prop.get("description", ""),
                required=name in required_set,
                default=prop.get("default"),
                enum=prop.get("enum"),
                items_type=_items_type(prop, t),
            )
            for name, prop in props.items()
            if isinstance(prop, dict)
        }
    )


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


# ── Routes ────────────────────────────────────────────────────────────────────

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

    cache_items, _ = get_cached(
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
                    name=t.name,
                    description=t.description,
                    input_schema=_flatten_schema(t.input_schema),
                )
                for t in integration.tools
            ],
        )

    settings = get_settings()

    # Toolkit metadata from catalog cache (populated at startup).
    toolkit_meta = get_cached_toolkit_meta(slug)
    if toolkit_meta is None:
        raise HTTPException(status_code=404, detail=f"Integration '{slug}' not found")

    # Tool schemas from schema cache; warm on first access.
    tool_objects = get_cached_toolkit_schemas(slug)
    if not tool_objects:
        await warm_toolkit(settings.composio_api_key, slug)
        tool_objects = get_cached_toolkit_schemas(slug)

    return IntegrationDetailResponse(
        slug=toolkit_meta["slug"],
        display_name=toolkit_meta["name"],
        description=toolkit_meta["description"],
        provider_type=ProviderType.COMPOSIO,
        deferred=True,
        tools=[
            ToolSchemaResponse(
                name=getattr(t, "slug", ""),
                description=getattr(t, "description", ""),
                input_schema=_flatten_schema(
                    getattr(t, "input_parameters", None)
                ),
            )
            for t in tool_objects
        ],
    )

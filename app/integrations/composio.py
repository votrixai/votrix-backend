"""
Composio integration — session factory and async resource accessor.

One singleton AsyncComposio client per process.

Per-conversation session IDs are stored in the DB so all pods share the same
session_id — avoids creating a new Composio session on every chat request.
"""

from __future__ import annotations

import structlog
from composio_client import AsyncComposio

from app.config import get_settings

logger = structlog.get_logger()

_async_composio: AsyncComposio | None = None


def _get_async_composio() -> AsyncComposio:
    global _async_composio
    if _async_composio is None:
        _async_composio = AsyncComposio(api_key=get_settings().composio_api_key)
    return _async_composio


def get_async_session_resource():
    """Return the async Composio session resource for execute/tools/link/toolkits."""
    return _get_async_composio().tool_router.session


async def _resolve_auth_configs(slugs: list[str]) -> dict[str, str]:
    """Return {toolkit_slug: auth_config_id} for each slug that has an auth config.

    Prefers composio-managed configs; falls back to any available.
    Filters client-side because the toolkit_slug query param is unreliable.
    """
    if not slugs:
        return {}
    slug_set = set(slugs)
    response = await _get_async_composio().auth_configs.list(
        toolkit_slug=",".join(slugs),
        limit=1000,
    )
    best: dict[str, tuple[str, bool]] = {}  # slug -> (auth_config_id, is_managed)
    for item in response.items:
        slug = item.toolkit.slug
        if slug not in slug_set:
            continue
        is_managed = bool(item.is_composio_managed)
        if slug not in best or (is_managed and not best[slug][1]):
            best[slug] = (item.id, is_managed)
    result = {slug: ac_id for slug, (ac_id, _) in best.items()}
    missing = [s for s in slugs if s not in result]
    if missing:
        logger.warning("composio: no auth_config found for toolkits=%s", missing)
    return result


async def create_composio_session(
    workspace_id: str,
    integrations: list[str],
    connected_accounts: dict[str, str] | None = None,
) -> str | None:
    """
    Create a new Composio ToolRouter session scoped to the given integrations.
    Returns the session_id string, or None if composio_api_key is not configured.
    Raises on session creation failure.

    Call once per DB session (not per request) and store the returned session_id.

    connected_accounts: optional map of toolkit_slug -> connected_account_id for
    shared/company accounts that should override per-user OAuth resolution.
    e.g. {"apollo": "conn_abc123"}
    """
    settings = get_settings()
    if not settings.composio_api_key:
        logger.warning("composio: api_key not configured, session not created")
        return None

    session_resource = get_async_session_resource()
    # NB: Composio SDK expects `user_id` as the kwarg name; we pass our workspace_id as the value.
    kwargs: dict = dict(user_id=workspace_id)
    if integrations:
        kwargs["toolkits"] = {"enable": integrations}
        auth_configs = await _resolve_auth_configs(integrations)
        if auth_configs:
            kwargs["auth_configs"] = auth_configs
    if connected_accounts:
        kwargs["connected_accounts"] = connected_accounts

    session = await session_resource.create(**kwargs)

    logger.info(
        "composio: created session workspace=%s toolkits=%s auth_configs=%s shared=%s id=%s",
        workspace_id, integrations, list((kwargs.get("auth_configs") or {}).keys()),
        list(connected_accounts or {}.keys()), session.session_id,
    )
    return session.session_id

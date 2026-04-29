"""
Composio integration — session factory and async resource accessor.

One singleton Composio client per process.

Per-conversation session IDs are stored in the DB so all pods share the same
session_id — avoids creating a new Composio session on every chat request.
"""

from __future__ import annotations

import asyncio

import structlog

from composio import Composio
from composio_client import AsyncComposio

from app.config import get_settings

logger = structlog.get_logger()

_composio: Composio | None = None
_async_composio: AsyncComposio | None = None


def _get_composio() -> Composio:
    global _composio
    if _composio is None:
        _composio = Composio(api_key=get_settings().composio_api_key)
    return _composio


def _get_async_composio() -> AsyncComposio:
    global _async_composio
    if _async_composio is None:
        _async_composio = AsyncComposio(api_key=get_settings().composio_api_key)
    return _async_composio


def get_async_session_resource():
    """Return the async Composio session resource for execute/tools/link/toolkits."""
    return _get_async_composio().tool_router.session


async def create_composio_session(
    user_id: str,
    integrations: list[str],
    connected_accounts: dict[str, str] | None = None,
) -> str | None:
    """
    Create a new Composio ToolRouter session scoped to the given integrations.
    Returns the session_id string, or None if composio_api_key is not configured.

    Call once per DB session (not per request) and store the returned session_id.

    connected_accounts: optional map of toolkit_slug -> connected_account_id for
    shared/company accounts that should override per-user OAuth resolution.
    e.g. {"apollo": "conn_abc123"}
    """
    settings = get_settings()
    if not settings.composio_api_key:
        logger.warning("composio: api_key not configured, session not created")
        return None

    composio = _get_composio()
    kwargs: dict = dict(user_id=user_id, toolkits=integrations or [])
    if connected_accounts:
        kwargs["connected_accounts"] = connected_accounts

    try:
        session = await asyncio.to_thread(composio.create, **kwargs)
    except Exception:
        # Some toolkits may lack auth configs — fall back to a session with no toolkit filter.
        logger.warning("composio: session with toolkits=%s failed, retrying with no filter", integrations)
        try:
            session = await asyncio.to_thread(composio.create, user_id=user_id)
        except Exception as exc:
            logger.error("composio: session creation failed: %s", exc)
            return None

    logger.info(
        "composio: created session user=%s toolkits=%s shared=%s id=%s",
        user_id, integrations, list(connected_accounts or {}.keys()), session.session_id,
    )
    return session.session_id

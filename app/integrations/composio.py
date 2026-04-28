"""
Composio MCP helpers.

MCP server lifecycle:
  - One server per agent per provision, named "votrix-{agent_id}-{datetime}"
  - create_mcp_server() always creates a new server; old servers are kept alive
    so existing Anthropic agents (baked into running sessions) continue to work
  - Per-user routing via ?user_id= on the MCP URL
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_MCP_BASE = "https://backend.composio.dev/v3/mcp"
_API_BASE = "https://backend.composio.dev/api/v3"


def _headers() -> dict:
    return {"x-api-key": get_settings().composio_api_key}


def _server_name(agent_id: str) -> str:
    # Composio limit: 30 chars. Use last 8 chars of agent_id + 12-char timestamp.
    ts = datetime.now(timezone.utc).strftime("%m%d%H%M%S")  # 10 chars
    short_id = agent_id[-8:]                                  # last 8 chars
    return f"vx-{short_id}-{ts}"                             # 3+1+8+1+10 = 23 chars


async def get_auth_config(toolkit_slug: str) -> dict | None:
    """Return the best auth_config for a toolkit slug.
    Prefers composio-managed, falls back to any available. Handles pagination.
    Note: slug is nested under item["toolkit"]["slug"], not at the top level.
    The ?toolkit_slug= filter param is unreliable, so we filter client-side."""
    page = 1
    fallback = None
    async with httpx.AsyncClient() as client:
        while True:
            r = await client.get(
                f"{_API_BASE}/auth_configs",
                headers=_headers(),
                params={"toolkit_slug": toolkit_slug, "page": page},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            for item in data.get("items", []):
                item_slug = (item.get("toolkit") or {}).get("slug", "")
                if item_slug != toolkit_slug:
                    continue
                if item.get("is_composio_managed"):
                    return item
                if fallback is None:
                    fallback = item
            if page >= (data.get("total_pages") or 1):
                return fallback
            page += 1


async def _create_server(
    name: str,
    auth_config_ids: list[str],
    managed_auth: bool,
) -> str:
    """Create a new Composio MCP server. Returns server_id."""
    payload: dict = {
        "name": name,
        "managed_auth_via_composio": managed_auth,
        "auth_config_ids": auth_config_ids,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{_API_BASE}/mcp/servers",
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
    if not r.is_success:
        raise RuntimeError(f"Failed to create MCP server: {r.status_code} {r.text}")
    return r.json()["id"]


async def create_mcp_server(
    agent_id: str,
    integrations: list[dict],
) -> str | None:
    """
    Create a new Composio MCP server for this agent provision.

    Always creates a new server with a datetime-stamped name — old servers are
    intentionally kept alive so existing Anthropic agents (baked into running
    sessions) continue to reach their MCP server.

    Returns None if there are no integrations.
    """
    if not integrations:
        return None

    name = _server_name(agent_id)
    auth_config_ids: list[str] = []
    all_managed = True

    for i in integrations:
        slug = i["slug"]
        ac = await get_auth_config(slug)
        if ac is None:
            raise RuntimeError(f"No auth_config found in Composio for integration '{slug}'. "
                               "Create one in the Composio dashboard first.")
        auth_config_ids.append(ac["id"])
        if not ac.get("is_composio_managed"):
            all_managed = False

    server_id = await _create_server(name, auth_config_ids, managed_auth=all_managed)
    logger.info("composio: created MCP server %s (%s)", name, server_id)
    return server_id


def mcp_url(server_id: str, user_id: str) -> str:
    """Return Composio MCP URL scoped to a user."""
    s = get_settings()
    return f"{_MCP_BASE}/{server_id}/mcp?user_id={quote(user_id, safe='')}&api_key={s.composio_api_key}"

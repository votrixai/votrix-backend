"""
Composio MCP helpers.

MCP server lifecycle:
  - One server per agent, named "votrix-{agent_id}"
  - get_or_create_mcp_server() finds existing or creates new (idempotent)
  - force=True deletes and recreates
  - Per-user routing via ?user_id= on the MCP URL
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_MCP_BASE = "https://backend.composio.dev/v3/mcp"
_API_BASE = "https://backend.composio.dev/api/v3"


def _headers() -> dict:
    return {"x-api-key": get_settings().composio_api_key}


def _server_name(agent_id: str) -> str:
    return f"votrix-{agent_id}"


def _get_auth_config(toolkit_slug: str) -> dict | None:
    """Return the best auth_config for a toolkit slug.
    Prefers composio-managed, falls back to any available. Handles pagination.
    Note: slug is nested under item["toolkit"]["slug"], not at the top level.
    The ?toolkit_slug= filter param is unreliable, so we filter client-side."""
    page = 1
    fallback = None
    while True:
        r = httpx.get(
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
                return item  # managed takes priority
            if fallback is None:
                fallback = item  # keep first non-managed as fallback
        if page >= (data.get("total_pages") or 1):
            return fallback
        page += 1


async def _get_auth_config_async(toolkit_slug: str) -> dict | None:
    """Async version of _get_auth_config — for use in async tool handlers at runtime."""
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


def _find_existing_server(name: str) -> dict | None:
    """Return existing server dict if found by name, else None. Handles pagination."""
    page = 1
    while True:
        r = httpx.get(f"{_API_BASE}/mcp/servers", headers=_headers(),
                      params={"page": page}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for server in data.get("items", []):
            if server.get("name") == name:
                return server
        if page >= (data.get("total_pages") or 1):
            return None
        page += 1


def _delete_server(server_id: str) -> None:
    r = httpx.delete(f"{_API_BASE}/mcp/{server_id}", headers=_headers(), timeout=15)
    if not r.is_success:
        logger.warning("composio: delete server %s returned %s", server_id, r.status_code)


def _create_server(
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

    r = httpx.post(
        f"{_API_BASE}/mcp/servers",
        headers={**_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    if not r.is_success:
        raise RuntimeError(f"Failed to create MCP server: {r.status_code} {r.text}")
    return r.json()["id"]


def get_or_create_mcp_server(
    agent_id: str,
    integrations: list[dict],
    force: bool = False,
) -> str | None:
    """
    Return the Composio MCP server_id for this agent.

    - Finds existing server named "votrix-{agent_id}"
    - force=True: delete and recreate
    - If no integrations have a valid auth_config, returns None (no MCP server needed)
    """
    if not integrations:
        return None

    name = _server_name(agent_id)

    existing = _find_existing_server(name)
    if existing and not force:
        logger.info("composio: reusing MCP server %s (%s)", name, existing["id"])
        return existing["id"]

    if existing and force:
        logger.info("composio: deleting existing MCP server %s", name)
        _delete_server(existing["id"])

    # Resolve auth_configs
    auth_config_ids: list[str] = []
    all_managed = True  # track if all auth_configs are composio-managed

    for i in integrations:
        slug = i["slug"]
        ac = _get_auth_config(slug)
        if ac is None:
            raise RuntimeError(f"No auth_config found in Composio for integration '{slug}'. "
                               "Create one in the Composio dashboard first.")
        auth_config_ids.append(ac["id"])
        if not ac.get("is_composio_managed"):
            all_managed = False

    server_id = _create_server(name, auth_config_ids, managed_auth=all_managed)
    logger.info("composio: created MCP server %s (%s)", name, server_id)
    return server_id


def mcp_url(server_id: str, user_id: str) -> str:
    """Return Composio MCP URL scoped to a user."""
    s = get_settings()
    return f"{_MCP_BASE}/{server_id}/mcp?user_id={user_id}&api_key={s.composio_api_key}"

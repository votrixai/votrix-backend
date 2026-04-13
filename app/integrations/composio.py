"""
Composio MCP helpers.

Composio auth model (confirmed via testing):
  - user_id in URL query param  → user routing
  - api_key as bearer token     → org-level auth (injected by Anthropic Vault)
  - api_key in URL query param  → conflicts with vault; don't do both

For per-user agents (no vault), embed both in URL:
  ?user_id={user_id}&api_key={api_key}

Per-toolkit scoping via &apps={toolkit_slug} prevents tool overload —
each MCP server only exposes tools for one integration.
"""

from __future__ import annotations

from app.config import get_settings

_MCP_BASE = "https://backend.composio.dev/v3/mcp"


def mcp_url(user_id: str) -> str:
    """Return Composio MCP URL for a specific user (all tools)."""
    s = get_settings()
    return f"{_MCP_BASE}/{s.composio_server_id}/mcp?user_id={user_id}&api_key={s.composio_api_key}"


def mcp_url_for_toolkit(user_id: str, toolkit_slug: str) -> str:
    """Return Composio MCP URL scoped to a single toolkit slug."""
    s = get_settings()
    return (
        f"{_MCP_BASE}/{s.composio_server_id}/mcp"
        f"?user_id={user_id}&api_key={s.composio_api_key}&apps={toolkit_slug}"
    )

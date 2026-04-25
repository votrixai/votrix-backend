"""
manage_connections — create or verify connections to any app via Composio.

Behavior mirrors COMPOSIO_MANAGE_CONNECTIONS:
  - ACTIVE connection  → returns connection details + account metadata
  - No/expired connection → initiates OAuth and returns redirect_url
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.integrations.composio import get_auth_config

logger = logging.getLogger(__name__)

_API_BASE = "https://backend.composio.dev/api/v3"


DEFINITIONS = [
    {
        "type": "custom",
        "name": "manage_connections",
        "description": (
            "Create or manage connections to any app or service that requires authentication "
            "(OAuth, API key, or any other auth type). Works with social media platforms, "
            "productivity tools, CRMs, email providers, calendars, and any other Composio-supported integration. "
            "If the connection is already ACTIVE, returns connection details and available account metadata "
            "(e.g. user ID, username, page ID, email). "
            "If not connected or connection is expired, initiates authentication and returns a redirect_url — "
            "show it as a formatted markdown link and ask the user to click it to complete authorization. "
            "Always call this to verify a connection is ACTIVE before executing any tool for that app."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "toolkit": {
                    "type": "string",
                    "description": (
                        "The toolkit/app name to connect or check. "
                        "Use the exact Composio toolkit identifier, e.g. 'instagram', 'facebook', "
                        "'twitter', 'linkedin', 'gmail', 'github', 'slack', 'notion', 'google_calendar', etc."
                    ),
                },
                "force_reconnect": {
                    "type": "boolean",
                    "description": (
                        "If true, forces a new OAuth flow even if a connection already exists. "
                        "Use this when the existing connection lacks required permissions "
                        "(e.g. page posting permissions for Facebook)."
                    ),
                },
            },
            "required": ["toolkit"],
        },
    },
]


async def _list_connections(api_key: str, user_id: str, toolkit: str) -> list[dict]:
    """Return connected accounts for the given user and toolkit via REST API."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{_API_BASE}/connected_accounts",
                headers={"x-api-key": api_key},
                params={"user_ids": user_id, "toolkit_slugs": toolkit, "statuses": "ACTIVE"},
                timeout=15,
            )
            if not r.is_success:
                logger.warning("manage_connections: list connections returned %s: %s", r.status_code, r.text)
                return []
            return r.json().get("items", [])
    except Exception as exc:
        logger.warning("manage_connections: could not list connections: %r", exc)
        return []



async def handle(name: str, input: dict, user_id: str) -> dict:
    settings = get_settings()
    if not settings.composio_api_key:
        return {"status": False, "message": "Composio API key not configured"}

    toolkit = input.get("toolkit", "").lower().strip()
    if not toolkit:
        return {"status": False, "message": "toolkit is required"}

    try:
        force_reconnect = input.get("force_reconnect", False)

        # Check existing connections via REST API
        connections = await _list_connections(settings.composio_api_key, user_id, toolkit)
        active_conn = next(
            (c for c in connections
             if (c.get("status", "") or "").upper() == "ACTIVE"),
            None,
        )

        if active_conn and not force_reconnect:
            result = {
                "status": True,
                "connected": True,
                "toolkit": toolkit,
                "connection_id": active_conn.get("id"),
                "connection_status": active_conn.get("status"),
            }
            return result

        # Not connected — initiate auth via REST API (supports both managed and self-registered OAuth)
        ac = await get_auth_config(toolkit)
        if ac is None:
            return {"status": False, "message": f"No auth_config found for '{toolkit}'. Create one in Composio dashboard first."}

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_API_BASE}/connected_accounts",
                headers={"x-api-key": settings.composio_api_key, "Content-Type": "application/json"},
                json={
                    "auth_config": {"id": ac["id"]},
                    "connection": {"user_id": user_id},
                },
                timeout=15,
            )
        if not r.is_success:
            return {"status": False, "message": f"Failed to initiate connection: {r.text}"}
        redirect_url = r.json().get("redirect_url") or r.json().get("redirectUrl")

        if redirect_url:
            return {
                "status": True,
                "connected": False,
                "auth_type": "oauth",
                "toolkit": toolkit,
                "redirect_url": redirect_url,
                "message": f"Please authorize {toolkit} by visiting the redirect_url.",
            }
        else:
            # API key or other non-OAuth scheme — connection params needed from user
            return {
                "status": True,
                "connected": False,
                "auth_type": "api_key",
                "toolkit": toolkit,
                "message": f"{toolkit} requires an API key. Please provide your credentials to connect.",
            }

    except Exception as exc:
        logger.error("manage_connections failed for %s: %s", toolkit, exc)
        return {"status": False, "message": str(exc)}

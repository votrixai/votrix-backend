"""
manage_connections — create or verify connections to any app via Composio.

Behavior mirrors COMPOSIO_MANAGE_CONNECTIONS:
  - ACTIVE connection  → returns connection details + account metadata
  - No/expired connection → initiates OAuth and returns redirect_url
"""

from __future__ import annotations

import logging

from composio import App, Composio

from app.config import get_settings

logger = logging.getLogger(__name__)


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


async def handle(name: str, input: dict, user_id: str) -> dict:
    settings = get_settings()
    if not settings.composio_api_key:
        return {"status": False, "message": "Composio API key not configured"}

    toolkit = input.get("toolkit", "").lower().strip()
    if not toolkit:
        return {"status": False, "message": "toolkit is required"}

    # Resolve Composio App enum via attribute lookup (e.g. App.INSTAGRAM)
    app: App | None = getattr(App, toolkit.upper(), None)
    if app is None:
        return {"status": False, "message": f"Unknown toolkit '{toolkit}'. Use the exact Composio toolkit identifier."}

    try:
        client = Composio(api_key=settings.composio_api_key)
        entity = client.get_entity(id=user_id)

        force_reconnect = input.get("force_reconnect", False)

        # Check existing connections
        connections = entity.get_connections()
        active_conn = next(
            (c for c in connections
             if (getattr(c, "appName", "") or "").lower() == toolkit
             and getattr(c, "status", "").upper() in ("ACTIVE", "INITIATED")),
            None,
        )

        if active_conn and not force_reconnect:
            result = {
                "status": True,
                "connected": True,
                "toolkit": toolkit,
                "connection_id": getattr(active_conn, "id", None),
                "connection_status": getattr(active_conn, "status", None),
            }
            # For Instagram, also fetch the IG Business Account ID needed for publishing
            if toolkit == "instagram":
                try:
                    from composio import ComposioToolSet
                    toolset = ComposioToolSet(api_key=settings.composio_api_key, entity_id=user_id)
                    info = toolset.execute_action("INSTAGRAM_GET_USER_INFO", {}, entity_id=user_id)
                    if info.get("successful"):
                        data = info.get("data", {})
                        result["ig_user_id"] = data.get("id")
                        result["username"] = data.get("username")
                except Exception as exc:
                    logger.warning("manage_connections: could not get IG user info: %s", exc)
            return result

        # Not connected — initiate auth (OAuth redirect or API key form depending on app)
        connection_request = entity.initiate_connection(app_name=app)
        redirect_url = getattr(connection_request, "redirectUrl", None)

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

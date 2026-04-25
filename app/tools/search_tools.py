"""
search_tools — capability reference for connected external platforms.

Returns raw tool slugs from Composio's catalog. The agent checks whether
returned slugs exist in its own available tools to determine supportability.
"""

from __future__ import annotations

import structlog
import httpx

from app.config import get_settings

logger = structlog.get_logger()

_API_BASE = "https://backend.composio.dev/api/v3"

DEFINITIONS = [
    {
        "type": "custom",
        "name": "search_tools",
        "description": (
            "Reference tool for checking whether a specific action is supported "
            "by connected external platforms. "
            "Use this when admin requests an operation you are unsure the platform supports, "
            "or before telling admin something cannot be done. "
            "This is a reference only — does not cover custom tools or built-in agent capabilities. "
            "After receiving results, check whether the returned tool slugs exist in your own "
            "available tools. If yes, the action is supported — use that slug to call it. "
            "If the returned slugs are not in your tools, or no results are found, "
            "the action is not available — inform admin."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Describe the action in English, e.g. 'delete a published Instagram post'.",
                },
            },
            "required": ["query"],
        },
    },
]


async def handle(name: str, input: dict, user_id: str) -> dict:
    settings = get_settings()
    if not settings.composio_api_key:
        return {"tools": [], "error": "Composio API key not configured"}

    query = (input.get("query") or "").strip()
    if not query:
        return {"tools": [], "error": "query is required"}

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_API_BASE}/tools/execute/COMPOSIO_SEARCH_TOOLS",
                headers={
                    "x-api-key": settings.composio_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "arguments": {
                        "queries": [{"use_case": query}],
                        "session": {"generate_id": True},
                    },
                    "user_id": user_id,
                },
                timeout=15,
            )
        if not r.is_success:
            logger.warning("search_tools: Composio returned %s: %s", r.status_code, r.text)
            return {"tools": [], "error": f"Search API error {r.status_code}"}

        results = r.json().get("data", {}).get("results", [])
        tools: list[str] = [
            slug
            for result in results
            for slug in (result.get("primary_tool_slugs") or [])
        ]
        return {"tools": tools}

    except Exception as exc:
        logger.error("search_tools failed: %s", exc)
        return {"tools": [], "error": str(exc)}

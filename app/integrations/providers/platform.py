"""
PlatformProvider — loads platform-native tools.

Tools with effective provider_slug == "platform"  → wrapped with a local handler.
Tools with effective provider_slug == "composio"  → delegated to Composio SDK
    (e.g. web_search → TAVILY_SEARCH, web_fetch → SCRAPE_URL, bash_tool → EXEC_COMMAND).
"""

import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import create_model

from app.models.integration import Integration, Tool
from app.integrations.handlers import PLATFORM_HANDLERS
from app.integrations.providers import ToolProvider
from app.integrations.providers.composio import load_by_tools

logger = logging.getLogger(__name__)

_PY_TYPE_MAP = {
    "string":  str,
    "integer": int,
    "number":  float,
    "boolean": bool,
    "array":   list,
    "object":  dict,
}


def _schema_to_model(tool_slug: str, schema: Dict[str, Any]) -> Type:
    """Dynamically build a Pydantic model from a JSON Schema dict."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: Dict[str, Any] = {}
    for name, prop in props.items():
        py_type = _PY_TYPE_MAP.get(prop.get("type", "string"), Any)
        if name in required:
            fields[name] = (py_type, ...)
        else:
            fields[name] = (Optional[py_type], None)
    return create_model(f"{tool_slug}_schema", **fields)


def _make_local_tool(tool: Tool) -> BaseTool:
    handler = PLATFORM_HANDLERS[tool.slug]
    model = _schema_to_model(tool.slug, tool.input_schema)
    return StructuredTool(
        name=tool.slug,
        description=tool.description,
        args_schema=model,
        coroutine=handler,
    )


class PlatformProvider(ToolProvider):
    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    async def load_tools(
        self,
        integration: Integration,
        enabled_mcp_tool_slugs: Optional[List[str]],
        user_id: str,
    ) -> List[BaseTool]:
        tools = integration.tools
        if enabled_mcp_tool_slugs:
            tools = [t for t in tools if t.slug in enabled_mcp_tool_slugs]

        result: List[BaseTool] = []
        composio_actions: List[str] = []

        for tool in tools:
            eff_provider = integration.effective_provider_slug(tool)

            if eff_provider == "platform":
                if tool.slug not in PLATFORM_HANDLERS:
                    logger.warning("No handler for platform tool: %s — skipping", tool.slug)
                    continue
                result.append(_make_local_tool(tool))

            elif eff_provider == "composio":
                cfg = integration.effective_provider_config(tool)
                action = cfg.get("action")
                if action:
                    composio_actions.append(action)
                else:
                    logger.warning("composio tool %s has no action in provider_config", tool.slug)

        if composio_actions:
            composio_tools = await load_by_tools(self._api_key, user_id, composio_actions)
            result.extend(composio_tools)

        return result

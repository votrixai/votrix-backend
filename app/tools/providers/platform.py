"""
PlatformProvider — loads platform-native tools.

Tools with effective provider_id == "platform"  → wrapped with a local handler.
Tools with effective provider_id == "composio"  → delegated to Composio SDK
    (e.g. web_search → TAVILY_SEARCH, web_fetch → SCRAPE_URL, bash_tool → EXEC_COMMAND).
"""

import logging
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import create_model

from app.models.tools import Integration, Tool
from app.tools.handlers import PLATFORM_HANDLERS
from app.tools.providers import ToolProvider

logger = logging.getLogger(__name__)

_PY_TYPE_MAP = {
    "string":  str,
    "integer": int,
    "number":  float,
    "boolean": bool,
    "array":   list,
    "object":  dict,
}


def _schema_to_model(tool_id: str, schema: Dict[str, Any]) -> Type:
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
    return create_model(f"{tool_id}_schema", **fields)


def _make_local_tool(tool: Tool) -> BaseTool:
    handler = PLATFORM_HANDLERS[tool.id]
    model = _schema_to_model(tool.id, tool.input_schema)
    return StructuredTool(
        name=tool.id,
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
        enabled_tool_ids: Optional[List[str]],
        user_id: str,
    ) -> List[BaseTool]:
        tools = integration.tools
        if enabled_tool_ids:
            tools = [t for t in tools if t.id in enabled_tool_ids]

        result: List[BaseTool] = []
        composio_actions: List[str] = []

        for tool in tools:
            eff_provider = integration.effective_provider_id(tool)

            if eff_provider == "platform":
                if tool.id not in PLATFORM_HANDLERS:
                    logger.warning("No handler for platform tool: %s — skipping", tool.id)
                    continue
                result.append(_make_local_tool(tool))

            elif eff_provider == "composio":
                cfg = integration.effective_provider_config(tool)
                action = cfg.get("action")
                if action:
                    composio_actions.append(action)
                else:
                    logger.warning("composio tool %s has no action in provider_config", tool.id)

        if composio_actions:
            from app.tools.providers.composio import load_by_actions
            composio_tools = await load_by_actions(self._api_key, user_id, composio_actions)
            result.extend(composio_tools)

        return result

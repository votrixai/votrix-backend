"""
Platform handler — tool schemas, execution closures, and tool assembly.

Local tools (create_file, str_replace, view) are backed by the user_files
virtual filesystem (Postgres). Composio-routed tools (web_search, web_fetch,
bash_tool) are delegated to the Composio SDK.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Type

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.queries import user_files as user_files_q
from app.models.integration import Integration, Tool

logger = logging.getLogger(__name__)


# ── Context ───────────────────────────────────────────────────────────────────

@dataclass
class FileContext:
    session: AsyncSession
    blueprint_agent_id: uuid.UUID
    user_id: uuid.UUID


# ── Pydantic input models (source of truth for schema + LangChain args_schema) ─

class CreateFileInput(BaseModel):
    description: str = Field(..., description="Why I'm creating this file. ALWAYS PROVIDE THIS PARAMETER FIRST.")
    path: str        = Field(..., description="Path to the file to create. ALWAYS PROVIDE THIS PARAMETER SECOND.")
    file_text: str   = Field(..., description="Content to write to the file. ALWAYS PROVIDE THIS PARAMETER LAST.")


class StrReplaceInput(BaseModel):
    description: str = Field(..., description="Why I'm making this edit")
    path: str        = Field(..., description="Path to the file to edit")
    old_str: str     = Field(..., description="String to replace (must be unique in file)")
    new_str: str     = Field("",  description="String to replace with (empty string to delete)")


class ViewInput(BaseModel):
    description: str              = Field(..., description="Why I need to view this")
    path: str                     = Field(..., description="Absolute path to file or directory")
    view_range: Optional[List[int]] = Field(None, description="Optional line range [start, end] for text files")


# slug → Pydantic input class (used directly as LangChain args_schema)
_INPUT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "create_file": CreateFileInput,
    "str_replace":  StrReplaceInput,
    "view":         ViewInput,
}


# ── Tool catalog (input_schema derived from Pydantic classes) ─────────────────

_PLATFORM_TOOLS = [
    Tool(
        name="create_file",
        description="Create a new file with content in the user workspace",
        input_schema=CreateFileInput.model_json_schema(),
    ),
    Tool(
        name="str_replace",
        description=(
            "Replace a unique string in a file with another string. "
            "old_str must match the file content exactly and appear exactly once."
        ),
        input_schema=StrReplaceInput.model_json_schema(),
    ),
    Tool(
        name="view",
        description="View a file's content or list the immediate children of a directory.",
        input_schema=ViewInput.model_json_schema(),
    ),
    Tool(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
        provider_slug="composio",
        provider_config={"app_id": "TAVILY", "action": "TAVILY_SEARCH"},
    ),
    Tool(
        name="web_fetch",
        description="Fetch the contents of a web page at a given URL.",
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        },
        provider_slug="composio",
        provider_config={"app_id": "FIRECRAWL", "action": "SCRAPE_URL"},
    ),
    Tool(
        name="bash_tool",
        description="Run a bash command in the container",
        input_schema={
            "type": "object",
            "properties": {
                "command":     {"type": "string", "description": "Bash command to run"},
                "description": {"type": "string", "description": "Why I'm running this command"},
            },
            "required": ["command"],
        },
        provider_slug="composio",
        provider_config={"app_id": "REMOTE_BASH", "action": "EXEC_COMMAND"},
    ),
]

PLATFORM_INTEGRATION = Integration(
    slug="platform",
    display_name="Platform",
    description="Platform-native tools built into the runtime",
    provider_slug="platform",
    provider_config={},
    deferred=False,
    tools=_PLATFORM_TOOLS,
)

# tool_search is auto-injected by ToolAssembler when any deferred integration is enabled.
TOOL_SEARCH = Tool(
    name="tool_search",
    description=(
        "Search for and load deferred tools by keyword. "
        "Call this to load tool definitions before using them."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query to find relevant tools"},
            "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)


# ── Handler factories ─────────────────────────────────────────────────────────

def _make_view_handler(ctx: FileContext):
    async def handler(description: str, path: str, view_range: Optional[list] = None):
        node = await user_files_q.read_file(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, path
        )
        if node and node.type == "file":
            content = node.content or ""
            if view_range and len(view_range) == 2:
                lines = content.splitlines()
                start, end = view_range[0] - 1, view_range[1]
                content = "\n".join(lines[max(0, start):end])
            return {"status": True, "content": content}
        entries = await user_files_q.ls(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, path
        )
        if entries:
            return {
                "status": True,
                "entries": [
                    {"name": e.name, "type": e.type, "size_bytes": e.size_bytes}
                    for e in entries
                ],
            }
        return {"status": False, "message": f"Path not found: {path}"}
    return handler


def _make_create_file_handler(ctx: FileContext):
    async def handler(description: str, path: str, file_text: str):
        try:
            await user_files_q.write_file(
                ctx.session, ctx.blueprint_agent_id, ctx.user_id, path, file_text
            )
            return {"status": True, "message": f"Created {path}"}
        except Exception as exc:
            logger.error("create_file failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_str_replace_handler(ctx: FileContext):
    async def handler(description: str, path: str, old_str: str, new_str: str = ""):
        result = await user_files_q.edit_file(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, path, old_str, new_str
        )
        if result is None:
            return {"status": False, "message": "old_str not found or file does not exist"}
        return {"status": True, "message": f"Replaced in {path}"}
    return handler


_HANDLER_FACTORIES = {
    "view":        _make_view_handler,
    "create_file": _make_create_file_handler,
    "str_replace": _make_str_replace_handler,
}


# ── Tool assembly ─────────────────────────────────────────────────────────────

def _make_local_tool(tool: Tool, ctx: FileContext) -> BaseTool:
    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=_INPUT_SCHEMAS[tool.name],
        coroutine=_HANDLER_FACTORIES[tool.name](ctx),
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def load_tools(
    integration: Integration,
    enabled_tool_slugs: Optional[List[str]],
    user_id: str,
    agent_id: uuid.UUID,
    session: AsyncSession,
    api_key: str = "",
) -> List[BaseTool]:
    from app.integrations.handlers.composio import load_by_tools

    tools = integration.tools
    if enabled_tool_slugs:
        tools = [t for t in tools if t.name in enabled_tool_slugs]

    ctx = FileContext(
        session=session,
        blueprint_agent_id=agent_id,
        user_id=uuid.UUID(user_id),
    )
    result: List[BaseTool] = []
    composio_actions: List[str] = []

    for tool in tools:
        eff_provider = tool.provider_slug if tool.provider_slug is not None else integration.provider_slug

        if eff_provider == "platform":
            if tool.name not in _HANDLER_FACTORIES:
                logger.warning("No handler for platform tool: %s — skipping", tool.name)
                continue
            result.append(_make_local_tool(tool, ctx))

        elif eff_provider == "composio":
            cfg = tool.provider_config if tool.provider_config is not None else integration.provider_config
            action = cfg.get("action")
            if action:
                composio_actions.append(action)
            else:
                logger.warning("composio tool %s has no action in provider_config", tool.name)

    if composio_actions:
        composio_tools = await load_by_tools(api_key, user_id, composio_actions)
        result.extend(composio_tools)

    return result

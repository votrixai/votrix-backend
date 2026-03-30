"""
Platform integration static data — tool declarations and input schemas.

Defines what tools the platform integration provides: their names,
descriptions, input_schema, and routing config. No execution logic here.

docs/tools.md §3 — Platform Integration
"""

from app.models.tools import Integration, Provider, ProviderType, Tool

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

PROVIDERS = {
    "platform": Provider(id="platform", name="Platform", type=ProviderType.PLATFORM),
    "composio": Provider(id="composio", name="Composio", type=ProviderType.COMPOSIO),
}

# ---------------------------------------------------------------------------
# Platform tool declarations (deferred: false)
# native tools inherit provider "platform"; composio-backed tools override
# ---------------------------------------------------------------------------

_PLATFORM_TOOLS = [
    Tool(
        id="create_file",
        name="create_file",
        description="Create a new file with content in the container",
        input_schema={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Why I'm creating this file. ALWAYS PROVIDE THIS PARAMETER FIRST.",
                },
                "path": {
                    "type": "string",
                    "description": "Path to the file to create. ALWAYS PROVIDE THIS PARAMETER SECOND.",
                },
                "file_text": {
                    "type": "string",
                    "description": "Content to write to the file. ALWAYS PROVIDE THIS PARAMETER LAST.",
                },
            },
            "required": ["description", "path", "file_text"],
        },
    ),
    Tool(
        id="str_replace",
        name="str_replace",
        description=(
            "Replace a unique string in a file with another string. "
            "old_str must match the raw file content exactly and appear exactly once."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Why I'm making this edit"},
                "path": {"type": "string", "description": "Path to the file to edit"},
                "old_str": {
                    "type": "string",
                    "description": "String to replace (must be unique in file)",
                },
                "new_str": {
                    "type": "string",
                    "description": "String to replace with (empty to delete)",
                },
            },
            "required": ["description", "old_str", "path"],
        },
    ),
    Tool(
        id="view",
        name="view",
        description="Supports viewing text, images, and directory listings.",
        input_schema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Why I need to view this"},
                "path": {
                    "type": "string",
                    "description": "Absolute path to file or directory",
                },
                "view_range": {
                    "type": "array",
                    "description": "Optional line range [start, end] for text files",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
            "required": ["description", "path"],
        },
    ),
    Tool(
        id="web_search",
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
        provider_id="composio",
        provider_config={"app_id": "TAVILY", "action": "TAVILY_SEARCH"},
    ),
    Tool(
        id="web_fetch",
        name="web_fetch",
        description="Fetch the contents of a web page at a given URL.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
            },
            "required": ["url"],
        },
        provider_id="composio",
        provider_config={"app_id": "FIRECRAWL", "action": "SCRAPE_URL"},
    ),
    Tool(
        id="bash_tool",
        name="bash_tool",
        description="Run a bash command in the container",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Bash command to run"},
                "description": {
                    "type": "string",
                    "description": "Why I'm running this command",
                },
            },
            "required": ["command"],
        },
        provider_id="composio",
        provider_config={"app_id": "REMOTE_BASH", "action": "EXEC_COMMAND"},
    ),
]

PLATFORM_INTEGRATION = Integration(
    id="platform",
    display_name="Platform",
    description="Platform-native tools built into the runtime",
    provider_id="platform",
    provider_config={},
    deferred=False,
    tools=_PLATFORM_TOOLS,
)

# tool_search is auto-injected by context_builder when any deferred integration
# is enabled. It has no integration owner and is not listed under PLATFORM_INTEGRATION.
TOOL_SEARCH = Tool(
    id="tool_search",
    name="tool_search",
    description=(
        "Search for and load deferred tools by keyword. "
        "Call this to load tool definitions before using them."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query to find relevant tools"},
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["query"],
    },
)

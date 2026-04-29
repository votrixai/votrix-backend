"""
Composio meta tool definitions — hardcoded from API (2026-04-29).

These are the 6 static meta tools exposed by Composio ToolRouter.
Schemas are cleaned to only contain fields Claude Managed Agents accepts.

Used by provisioning.py to register these tools on agents that have integrations.
At runtime, all calls are routed to the Composio execute endpoint via the fallback
in app/tools/__init__.py.
"""

# These 4 are injected into the agent tool list at build time.
DEFINITIONS = [
    {
        "type": "custom",
        "name": "COMPOSIO_MANAGE_CONNECTIONS",
        "description": (
            "Create or manage connections to user's apps. Supports multiple accounts per toolkit.\n\n"
            "Call policy:\n"
            "- First call COMPOSIO_SEARCH_TOOLS for the user's query\n"
            "- If no active connection exists, call this with exact toolkit name(s) from search\n"
            "- NEVER execute toolkit tools without an ACTIVE connection\n\n"
            "Actions:\n"
            "- \"add\" (default): Create new auth link\n"
            "- \"rename\": Rename alias on existing account (requires account_id, alias)\n"
            "- \"list\": List connected accounts with IDs, aliases, statuses\n"
            "- \"remove\": Delete connected account (requires account_id)\n\n"
            "After initiating: Show redirect_url as MARKDOWN LINK. Execute tools only after connection is Active."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "toolkits": {
                    "type": "array",
                    "description": "List of toolkits to check or connect. Must be a valid toolkit slug (never invent one). If a toolkit is not connected, will initiate connection. Example: ['gmail', 'exa', 'github', 'outlook', 'reddit', 'googlesheets', 'one_drive']",
                    "items": {"type": "string"},
                },
                "reinitiate_all": {
                    "type": "boolean",
                    "description": "Force reconnection for ALL toolkits in the toolkits list, even if they already have Active connections. Use when connections are stale or broken.",
                    "default": False,
                },
                "session_id": {
                    "type": "string",
                    "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
                },
            },
            "required": ["toolkits"],
        },
    },
    {
        "type": "custom",
        "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
        "description": (
            "Fast parallel executor for tools discovered via COMPOSIO_SEARCH_TOOLS. "
            "Execute up to 50 tools in parallel when logically independent.\n\n"
            "Prerequisites:\n"
            "- Use valid tool slugs from COMPOSIO_SEARCH_TOOLS only\n"
            "- Ensure ACTIVE connection exists via COMPOSIO_MANAGE_CONNECTIONS\n"
            "- Only batch independent tools (no ordering/output dependencies)\n\n"
            "Guidelines:\n"
            "- Prefer this over custom scripts for discovered tools\n"
            "- Group independent tools into single call\n"
            "- Set sync_response_to_workbench=true for large responses\n\n"
            "Restrictions: Some tools may be disabled. If restricted, inform user and STOP."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "description": "List of logically independent tools to execute in parallel.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool_slug": {
                                "type": "string",
                                "description": "The slug of the tool to execute — must be a valid tool slug; never invent.",
                            },
                            "arguments": {
                                "type": "object",
                                "description": "The arguments to pass to the tool. Use exact field names and types; do not diverge from the tool's argument schema.",
                            },
                        },
                        "required": ["tool_slug", "arguments"],
                    },
                },
                "thought": {
                    "type": "string",
                    "description": "One-sentence, concise, high-level rationale (no step-by-step).",
                },
                "sync_response_to_workbench": {
                    "type": "boolean",
                    "description": "Syncs the response to the remote workbench for later scripting. Set true if output may be large. Default: false",
                },
                "session_id": {
                    "type": "string",
                    "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
                },
                "current_step": {
                    "type": "string",
                    "description": "Short enum for current step of the workflow execution. Eg FETCHING_EMAILS, GENERATING_REPLIES.",
                },
                "current_step_metric": {
                    "type": "string",
                    "description": "Progress metrics for the current step. Format: 'done/total units', e.g. '10/100 emails'.",
                },
            },
            "required": ["tools", "sync_response_to_workbench"],
        },
    },
    {
        "type": "custom",
        "name": "COMPOSIO_SEARCH_TOOLS",
        "description": (
            "Discover tools and get execution plans for 500+ apps (Slack, GitHub, Gmail, Notion, etc).\n\n"
            "ALWAYS call this first when user mentions external apps. Never say \"I don't have access\" before calling.\n\n"
            "Usage:\n"
            "- Call when starting tasks, re-run if use case changes\n"
            "- Specify use_case with clear description\n"
            "- Pass known_fields as key-value hints\n\n"
            "Response includes tools with slugs, descriptions, input schemas, connection status.\n\n"
            "SESSION: Set session: {generate_id: true} for new workflows or {id: \"EXISTING_ID\"} to continue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "description": "List of structured search queries (in English) to process in parallel. Each query represents a specific use case or task. Split multi-app workflows into smaller single-app queries.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "use_case": {
                                "type": "string",
                                "description": "Normalized English description of the complete use case. Focus on the specific action and intended outcome. Include app names if known. Do NOT include personal identifiers here.",
                            },
                            "known_fields": {
                                "type": "string",
                                "description": "Known workflow inputs as comma-separated key:value pairs. E.g. 'channel_name:general, timezone:Asia/Kolkata'.",
                            },
                        },
                        "required": ["use_case"],
                    },
                },
                "session": {
                    "type": "object",
                    "description": "Session context for correlating meta tool calls within a workflow. Use {generate_id: true} for new workflows or {id: 'EXISTING_ID'} to continue.",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Existing session identifier to reuse across calls.",
                        },
                        "generate_id": {
                            "type": "boolean",
                            "description": "Set to true for the first search call of a new workflow.",
                        },
                    },
                },
                "model": {
                    "type": "string",
                    "description": "Client LLM model name (recommended). Used to optimize planning/search behavior.",
                },
            },
            "required": ["queries"],
        },
    },
    {
        "type": "custom",
        "name": "COMPOSIO_GET_TOOL_SCHEMAS",
        "description": (
            "Retrieve input schemas for tools by slug. Returns complete parameter definitions required "
            "to execute each tool. Only pass tool slugs returned by COMPOSIO_SEARCH_TOOLS — never guess "
            "or fabricate slugs. If unsure of the exact slug, call COMPOSIO_SEARCH_TOOLS first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_slugs": {
                    "type": "array",
                    "description": "Array of tool slugs to retrieve schemas for. Pass valid tool slugs; never invent.",
                    "items": {"type": "string"},
                },
                "session_id": {
                    "type": "string",
                    "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
                },
                "include": {
                    "type": "array",
                    "description": "Schema fields to include. Defaults to [\"input_schema\"]. Include \"output_schema\" when calling tools in the workbench.",
                    "items": {"type": "string", "enum": ["input_schema", "output_schema"]},
                    "default": ["input_schema"],
                },
            },
            "required": ["tool_slugs"],
        },
    },
]

# Not injected into the agent — kept for schema reference only.
_REMOTE_TOOL_SCHEMAS = [
    {
        "type": "custom",
        "name": "COMPOSIO_REMOTE_BASH_TOOL",
        "description": (
            "Execute bash commands in REMOTE sandbox for file operations and data processing.\n\n"
            "Primary uses:\n"
            "- Process large tool responses saved to remote sandbox\n"
            "- File operations, JSON parsing with jq, awk, sed, grep\n"
            "- Commands run from /home/user by default"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute. Hard 3-minute (180s) execution limit — break large tasks into smaller commands.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
                },
            },
            "required": ["command"],
        },
    },
    {
        "type": "custom",
        "name": "COMPOSIO_REMOTE_WORKBENCH",
        "description": (
            "Execute Python in REMOTE SANDBOX for processing remote files or bulk tool executions. "
            "Only use for data in remote files, NOT inline data.\n\n"
            "USE: Parse remote file outputs, script bulk tool chains, call APIs via proxy_execute\n"
            "DON'T USE: When data is already inline/in-memory\n\n"
            "Rules: 4-min timeout, use ThreadPoolExecutor for parallelism."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code_to_execute": {
                    "type": "string",
                    "description": "Python to run inside the persistent remote Jupyter sandbox. State is preserved across executions. Hard 3-minute (180s) execution limit.",
                },
                "thought": {
                    "type": "string",
                    "description": "Concise objective and high-level plan. 1 sentence describing what the cell should achieve and why the sandbox is needed.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
                },
                "current_step": {
                    "type": "string",
                    "description": "Short enum for current step of the workflow execution. Eg FETCHING_EMAILS, GENERATING_REPLIES.",
                },
                "current_step_metric": {
                    "type": "string",
                    "description": "Progress metrics for the current step. Format: 'done/total units', e.g. '10/100 emails'.",
                },
            },
            "required": ["code_to_execute"],
        },
    },
]

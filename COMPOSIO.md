# Composio Integration Notes

## SDK Version

Use the **new SDK** (`composio >= 0.11.4`), NOT the old `ComposioToolSet` API (`0.7.x`).
The two versions have completely different APIs.

```bash
uv add composio  # upgrades to latest
```

---

## Core Concept: ToolRouter Session

Everything goes through `composio.create()` (alias for `composio.tool_router.create()`).
A session is **per-user**, scoped to specific toolkits at creation time.

```python
from composio import Composio

composio = Composio(api_key=settings.composio_api_key)

session = composio.create(
    user_id=user_id,                                        # per-user isolation
    toolkits=["instagram", "twitter", "facebook", "linkedin"],  # allowlist from config.json
    connected_accounts={"instagram": "ca_xxx", ...},        # optional: pre-set known accounts
)
```

Once created, the session has three methods we care about:

| Method | What it does | Replaces |
|--------|-------------|---------|
| `session.search(query=...)` | Semantic search for tools — scoped to session's toolkits | `search_tools.py` raw HTTP |
| `session.execute(tool_slug=..., arguments=...)` | Execute a Composio tool as the user | missing (was never implemented) |
| `session.authorize(toolkit=...)` | Start OAuth flow, returns `redirect_url` | `oauth.py` raw HTTP |

**The `toolkits` allowlist is server-side enforced.** Composio's backend locks the session to those
toolkits — `search()` only returns tools from them, `execute()` only runs them.

---

## Why Not MCP

The old `composio.py` tried to create Composio MCP servers and pass `user_id` in the URL.
This does not work: Claude Managed Agents' MCP connector requires Bearer token auth on a fixed URL;
it cannot handle per-user routing via query params.

Reference: https://github.com/ComposioHQ/composio/issues/3258

**Solution**: custom tools + `ToolRouterSession` (no MCP involved).

---

## How Scoping Works

The `toolkits` param in `create()` accepts:

```python
# List shorthand — enable only these (allowlist)
toolkits=["instagram", "twitter"]

# Explicit enable object
toolkits={"enable": ["instagram", "twitter"]}

# Explicit disable object (denylist)
toolkits={"disable": ["linear"]}
```

Source: `composio/core/models/tool_router.py` `ToolRouter.create()` docstring.

---

## `connected_accounts` Parameter

Maps toolkit slug → connected account ID. Use when you already know which Composio
connected account to use for a given toolkit.

```python
connected_accounts={"instagram": "ca_abc123", "twitter": "ca_def456"}
```

If omitted, Composio resolves the connected account automatically via `user_id`.
Two options:
1. **Don't pass it** — Composio auto-resolves. Simple, costs one API round-trip.
2. **Query + pass** — Call Composio connected accounts API first, then pass IDs. More explicit.

Currently our DB does not store connected account IDs, so option 1 is default.

---

## Integration with Votrix Runtime

### Session lifecycle

The `ToolRouterSession` should be created **once per chat request**, in `chat.py`,
before starting the SSE stream. The `integrations` list comes from the agent's `config.json`.

```python
# chat.py — before event_stream()
agent_config = _read_config_by_provider_agent_id(blueprint.provider_agent_id)
integrations = [i["slug"] for i in agent_config.get("integrations", [])]
composio_session = composio_singleton.create(user_id=str(current_user.id), toolkits=integrations)
```

Then pass `composio_session` into `runtime.stream()` → `execute_tool()` → tool handlers.

### Tool handler replacements

**`tools/search_tools.py`**
```python
async def handle(name, input, user_id, composio_session):
    result = composio_session.search(query=input["query"])
    # result contains tool slugs scoped to the session's toolkits
    return {"tools": result}
```

**`tools/oauth.py`** (manage_connections)
```python
async def handle(name, input, user_id, composio_session):
    # Check existing connection
    toolkits_info = composio_session.toolkits(toolkits=[input["toolkit"]])
    item = toolkits_info.items[0] if toolkits_info.items else None
    if item and item.connection and item.connection.is_active and not input.get("force_reconnect"):
        return {"connected": True, "toolkit": input["toolkit"]}
    # Initiate OAuth
    conn_request = composio_session.authorize(toolkit=input["toolkit"])
    return {"connected": False, "redirect_url": conn_request.redirect_url}
```

**New: Composio tool execution** (currently missing entirely)
```python
# tools/__init__.py — fallback after all known custom tools
result = composio_session.execute(tool_slug=name, arguments=input)
return result.data if not result.error else {"error": result.error}
```

---

## What Still Needs to Change

1. **`app/integrations/composio.py`** — delete MCP server code, replace with
   a singleton `Composio` instance + `get_scoped_session(user_id, integrations)` helper.

2. **`app/management/provisioning.py`** — add a helper to reverse-lookup agent config
   from `provider_agent_id` (scan `agents/*/config.json`), so `chat.py` can get `integrations`.

3. **`app/routers/chat.py`** — create `ToolRouterSession` before the event stream,
   pass it to `runtime.stream()`.

4. **`app/runtime/sessions.py`** — add `composio_session` param to `stream()`,
   pass to `execute_tool()`.

5. **`app/tools/__init__.py`** — add `composio_session` param to `execute()`,
   pass to `search_tools` and `oauth` handlers; add fallback Composio execution.

6. **`app/tools/search_tools.py`** — replace raw HTTP with `session.search()`.

7. **`app/tools/oauth.py`** — replace raw HTTP with `session.authorize()` + `session.toolkits()`.

---

## Reference Files

- New SDK entry point: `/home/zyue/.local/lib/python3.12/site-packages/composio/sdk.py`
- `ToolRouter.create()`: `composio/core/models/tool_router.py` line 418
- `ToolRouterSession`: `composio/core/models/tool_router_session.py`
- POC repo showing overall pattern: `/home/zyue/project/votrix/claude-managed-agents-poc/`



SLUG: COMPOSIO_MANAGE_CONNECTIONS
{
  "properties": {
    "toolkits": {
      "description": "List of toolkits to check or connect. Must be a valid toolkit slug (never invent one). If a toolkit is not connected, will initiate connection. Example: ['gmail', 'exa', 'github', 'outlook', 'reddit', 'googlesheets', 'one_drive']",
      "items": {
        "properties": {},
        "type": "string"
      },
      "title": "Toolkits",
      "type": "array"
    },
    "reinitiate_all": {
      "default": false,
      "description": "Force reconnection for ALL toolkits in the toolkits list, even if they already have Active connections.\n              WHEN TO USE:\n              - You suspect existing connections are stale or broken.\n              - You want to refresh all connections with new credentials or settings.\n              - You're troubleshooting connection issues across multiple toolkits.\n              BEHAVIOR:\n              - Overrides any existing active connections for all specified toolkits and initiates new link-based authentication flows.\n              DEFAULT: false (preserve existing active connections)",
      "title": "Reinitiate All",
      "type": "boolean"
    },
    "session_id": {
      "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
      "title": "Session ID",
      "type": "string"
    }
  },
  "required": [
    "toolkits"
  ],
  "title": "ManageConnectionsRequest",
  "type": "object"
}
---
SLUG: COMPOSIO_MULTI_EXECUTE_TOOL
{
  "properties": {
    "tools": {
      "description": "List of logically independent tools to execute in parallel.",
      "items": {
        "properties": {
          "tool_slug": {
            "description": "The slug of the tool to execute \u2014 must be a valid tool slug; never invent.",
            "examples": [
              "GMAIL_SEND_EMAIL",
              "SLACK_SEND_MESSAGE",
              "GITHUB_CREATE_AN_ISSUE"
            ],
            "minLength": 1,
            "title": "Tool Slug",
            "type": "string"
          },
          "arguments": {
            "additionalProperties": true,
            "description": "The arguments to pass to the tool. Use exact field names and types; do not diverge from the tool's argument schema.",
            "examples": [
              {
                "body": "This is a test",
                "subject": "Hello",
                "to": "test@gmail.com"
              },
              {
                "channel": "#general",
                "text": "Hello from Composio!"
              },
              {
                "body": "Description of the issue",
                "labels": [
                  "bug"
                ],
                "title": "Bug Report"
              }
            ],
            "title": "Arguments",
            "type": "object"
          }
        },
        "required": [
          "tool_slug",
          "arguments"
        ],
        "title": "MultiExecuteToolItem",
        "type": "object"
      },
      "maxItems": 50,
      "minItems": 1,
      "title": "Tools",
      "type": "array"
    },
    "thought": {
      "description": "One-sentence, concise, high-level rationale (no step-by-step).",
      "title": "Thought",
      "type": "string"
    },
    "sync_response_to_workbench": {
      "description": "Syncs the response to the remote workbench (for later scripting/processing) while still viewable inline. Predictively set true if the output may be large or need scripting; if it turns out small/manageable, skip workbench and use inline only. Default: false",
      "title": "Sync Response To Workbench",
      "type": "boolean"
    },
    "session_id": {
      "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
      "title": "Session ID",
      "type": "string"
    },
    "current_step": {
      "description": "Short enum for current step of the workflow execution. Eg FETCHING_EMAILS, GENERATING_REPLIES. Always include to keep execution aligned with the workflow.",
      "title": "Current Step",
      "type": "string"
    },
    "current_step_metric": {
      "description": "Progress metrics for the current step - use to track how far execution has advanced. Format as a string \"done/total units\" - example \"10/100 emails\", \"0/n messages\", \"3/10 pages\".",
      "title": "Current Step Metric",
      "type": "string"
    }
  },
  "required": [
    "tools",
    "sync_response_to_workbench"
  ],
  "title": "MultiExecuteToolRequest",
  "type": "object"
}
---
SLUG: COMPOSIO_REMOTE_BASH_TOOL
{
  "properties": {
    "command": {
      "description": "The bash command to execute. **Hard 3-minute (180s) execution limit** \u2014 break large tasks into smaller commands.",
      "title": "Command",
      "type": "string"
    },
    "session_id": {
      "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
      "title": "Session ID",
      "type": "string"
    }
  },
  "required": [
    "command"
  ],
  "title": "RemoteBashToolInput",
  "type": "object"
}
---
SLUG: COMPOSIO_REMOTE_WORKBENCH
{
  "description": "Remote Workbench \u2014 run analysis/orchestration in a persistent remote sandbox.\nUse only when working with remote artifacts or when you must script multiple Composio tool calls.\nAvoid if the needed data is already inline in the chat/context.",
  "properties": {
    "code_to_execute": {
      "description": "Python to run inside the persistent **remote Jupyter sandbox**. State (imports, variables, files) is preserved across executions. Keep code concise to minimize tool call latency. Avoid unnecessary comments. **Hard 3-minute (180s) execution limit** \u2014 break large tasks into smaller cells.",
      "examples": [
        "import json, glob\npaths = glob.glob(file_path)\n...",
        "result, error = run_composio_tool(tool_slug='SLACK_SEARCH_MESSAGES', arguments={'query': 'Rube'})\nif error: return\nmessages = result.get('data', {}).get('messages', [])"
      ],
      "title": "Code To Execute",
      "type": "string"
    },
    "thought": {
      "description": "Concise objective and high-level plan (no private chain-of-thought). 1 sentence describing what the cell should achieve and why the sandbox is needed.",
      "title": "Thought",
      "type": "string"
    },
    "session_id": {
      "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
      "title": "Session ID",
      "type": "string"
    },
    "current_step": {
      "description": "Short enum for current step of the workflow execution. Eg FETCHING_EMAILS, GENERATING_REPLIES. Always include to keep execution aligned with the workflow.",
      "title": "Current Step",
      "type": "string"
    },
    "current_step_metric": {
      "description": "Progress metrics for the current step - use to track how far execution has advanced. Format as a string \"done/total units\" - example \"10/100 emails\", \"0/n messages\", \"3/10 pages\".",
      "title": "Current Step Metric",
      "type": "string"
    }
  },
  "required": [
    "code_to_execute"
  ],
  "title": "RemoteWorkbenchRequest",
  "type": "object"
}
---
SLUG: COMPOSIO_SEARCH_TOOLS
{
  "properties": {
    "queries": {
      "type": "array",
      "description": "List of structured search queries (in English) to process in parallel. Each query represents a specific use case or task. For multi-app or complex workflows, split them into smaller single-app, API-level actions for best accuracy, including implicit prerequisites (e.g., fetch the resource before updating it). Each query returns 5-10 tools.",
      "items": {
        "type": "object",
        "properties": {
          "use_case": {
            "description": "Provide a normalized English description of the complete use case to enable precise planning. Focus on the specific action and intended outcome. Include any specific apps if mentioned by user in each use_case. Do NOT include personal identifiers (names, emails, IDs) here \u2014 put those in known_fields.",
            "examples": [
              "send an email to someone",
              "search issues with label in jira toolkit",
              "put issue details in a google sheet",
              "post a formatted message to slack channel"
            ],
            "title": "Use Case",
            "type": "string",
            "maxLength": 1024
          },
          "known_fields": {
            "type": "string",
            "description": "Provide known workflow inputs as a single English string of comma-separated key:value pairs (not an array). Keep 1-2 short, structured items - stable identifiers, names, emails, or settings only. Omit if not relevant. No free-form or long text (messages, notes, descriptions).",
            "examples": [
              "channel_name:pod-sdk",
              "channel_id:123",
              "invitee_names:John,Maria, timezone:Asia/Kolkata"
            ]
          }
        },
        "required": [
          "use_case"
        ]
      },
      "minItems": 1,
      "title": "Queries"
    },
    "session": {
      "type": "object",
      "description": "Session context for correlating meta tool calls within a workflow. Always pass this parameter. Use {generate_id: true} for new workflows or {id: \"EXISTING_ID\"} to continue existing workflows.",
      "properties": {
        "id": {
          "type": "string",
          "description": "Existing session identifier for the current workflow to reuse across calls.",
          "title": "Session ID"
        },
        "generate_id": {
          "type": "boolean",
          "description": "Set to true for the first search call of a new usecase/workflow to generate a new session ID. When user pivots to a different task, set this true. If omitted or false with an existing session.id, the provided session ID will be reused.",
          "title": "Generate ID"
        }
      }
    },
    "model": {
      "type": "string",
      "description": "Client LLM model name (recommended). Used to optimize planning/search behavior. Ignored if omitted or invalid.",
      "examples": [
        "gpt-5.2",
        "claude-4.5-sonnet"
      ],
      "title": "Model"
    }
  },
  "required": [
    "queries"
  ],
  "title": "SearchToolsRequest",
  "type": "object"
}
---
SLUG: COMPOSIO_GET_TOOL_SCHEMAS
{
  "properties": {
    "tool_slugs": {
      "description": "Array of tool slugs to retrieve schemas for. Pass valid tool slugs; never invent.",
      "examples": [
        [
          "GMAIL_SEND_EMAIL",
          "SLACK_SEND_MESSAGE"
        ]
      ],
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "title": "Tool Slugs"
    },
    "session_id": {
      "description": "Pass the session_id if you received one from a prior COMPOSIO_SEARCH_TOOLS call.",
      "title": "Session ID",
      "type": "string"
    },
    "include": {
      "description": "Schema fields to include. Defaults to [\"input_schema\"]. Include \"output_schema\" when calling tools in the workbench to validate response structure.",
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "input_schema",
          "output_schema"
        ]
      },
      "default": [
        "input_schema"
      ],
      "examples": [
        [
          "input_schema"
        ],
        [
          "input_schema",
          "output_schema"
        ]
      ]
    }
  },
  "required": [
    "tool_slugs"
  ],
  "title": "GetToolSchemasRequest",
  "type": "object"
}
---
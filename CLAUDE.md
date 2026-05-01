# votrix-backend

## What This Is

FastAPI backend for Votrix — powered by Claude Managed Agents (Anthropic Agent SDK).
Agent templates are defined as local files; Anthropic hosts execution.

## Key Design

### Two phases

**Build** (admin, one-time per agent change):
```
python -m app.build.run                        # provision all agents
python -m app.build.run --agent marketing-agent
python -m app.build.run --agent marketing-agent --force
```
Reads `agents/{agent_id}/` → uploads skills → creates Anthropic managed agent → writes `.cache.json`.

**Runtime** (per chat request):
- `POST /agents/{agent_id}/chat` reads `.cache.json` for `agent_id + env_id`
- Creates Anthropic session → relays SSE stream

### Local file layout

```
agents/{agent_id}/
  config.json      # name, model, skills[], integrations[]
  IDENTITY.md      # system prompt component
  SOUL.md          # system prompt component
  .cache.json      # {agent_id, env_id, version} — gitignored, written by build

skills/{skill_name}/
  SKILL.md         # required — uploaded to Anthropic Skills API
  REFERENCE.md     # optional extra context zipped with SKILL.md
  .cache.json      # {skill_id, content_hash} — gitignored, written by build
```

### Database (9 tables)

| Table | Purpose |
|---|---|
| `users` | End users (display_name) |
| `workspaces` | Tenant workspaces (display_name) |
| `workspace_members` | User ↔ workspace membership (role) |
| `agent_blueprints` | Provisioned Anthropic agents (provider_agent_id, display_name, provider) |
| `agent_employees` | Blueprint hired into a workspace (workspace_id, agent_blueprint_id) |
| `agent_employee_memory_stores` | Memory store per employee (provider_memory_store_id, name) |
| `sessions` | Conversation sessions (provider_session_id, workspace_id, agent_blueprint_id, title) |
| `session_events` | Append-only event log (event_index, event_type, title, body) |
| `schedules` | Recurring cron jobs (cron_expression, timezone, message, is_active, next_run_at) |

## Running

```bash
uv sync
cp .env.example .env   # fill DATABASE_URL + ANTHROPIC_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Language

- All Python code and Python comments must be in English only. No non-English characters anywhere in `.py` files.

## Code Conventions

- All DB access via `app/db/queries/*.py` — DAO functions take `AsyncSession` as first arg
- ORM models in `app/db/models/` — one file per table
- Pydantic request/response schemas in `app/models/`
- `app/build/` = provision-time only (no FastAPI dependencies)
- `app/runtime/` = chat-time SSE relay
- `app/client.py` = shared Anthropic singleton via `get_client()`

## Agent Skill Design

### Composio tool pattern

All external tools (Apollo, Google Sheets, Firecrawl, etc.) are accessed through Composio's `ToolRouterSession`, NOT through MCP. The old MCP approach does not work with Claude Managed Agents (see `COMPOSIO.md`).

**How it works:**
1. Agent `config.json` declares toolkit slugs in `integrations` (e.g., `apollo`, `googlesheets`, `firecrawl`, `composio_search`)
2. At runtime, a Composio session is created scoped to those toolkits — all tools from those toolkits become directly callable by slug
3. Skills call tools by exact slug (e.g., `APOLLO_PEOPLE_SEARCH`, `FIRECRAWL_SCRAPE`, `COMPOSIO_SEARCH_TAVILY`, `GOOGLESHEETS_BATCH_GET`)
4. No MCP involved — tools flow through Composio's ToolRouterSession
5. Slugs are known and hardcoded in reference files — no runtime discovery needed

**Rules:**
- All agent skills MUST reference Composio tools by exact slug — NEVER use generic descriptions like "search with Tavily" or "scrape with Firecrawl"
- Document tool slugs and parameters in `skills/{skill}/reference/tools.md`
- Reference these files inline at the phase where they are used
- Use `COMPOSIO_MANAGE_CONNECTIONS` only for connection management
- Use `COMPOSIO_MULTI_EXECUTE_TOOL` only for parallel execution of multiple independent tool calls

### Skill file structure

- YAML frontmatter: `name`, `description` (trigger phrases + anti-triggers), `integrations` list
- Startup check: read workspace state, gate on prerequisites
- Phase-based flow: numbered phases with clear inputs/outputs, decision tables over prose
- Inline references: point to reference files at the exact phase they are used
- Error handling table at the bottom of every skill
- Handoff: each skill ends by naming the next skill in the pipeline
- Target 90-200 lines per skill; one coherent responsibility per skill

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

# votrix-backend

## What This Is

FastAPI backend for Votrix — powered by Claude Managed Agents (Anthropic Agent SDK).
Agent templates are defined as local files; Anthropic hosts execution.

## Key Design

### Two phases

**Provision** (admin, one-time per agent change):
- `POST /agents/{agent_id}/reprovision` — uploads skills, creates or updates Anthropic managed agent, persists `provider_agent_id` to DB
- `POST /agents/{agent_id}/enable` — links the provisioned agent to a workspace (creates `agent_employees` record)

Skill upload state is tracked in `.skills_registry.json` at project root (gitignored):
`{skill_name: {skill_id, content_hash}}` — skips re-upload if content unchanged.

**Runtime** (per chat request):
- `POST /sessions` — creates Anthropic session from DB-stored `provider_agent_id`
- `POST /chat` — relays SSE stream from Anthropic session

### Local file layout

```
agents/{agent_id}/
  config.json      # name, model, skills[], integrations[], tools[], memoryConfigs[]
  PROMPT.md        # system prompt

skills/{skill_name}/
  SKILL.md         # required — uploaded to Anthropic Skills API
  (any other files in the directory are zipped and uploaded together)

.skills_registry.json   # {skill_name: {skill_id, content_hash}} — gitignored
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
- `app/management/` = provision-time logic (skills upload, agent create/update, session create)
- `app/runtime/` = chat-time SSE relay
- `app/client.py` = shared Anthropic singleton via `get_client()`

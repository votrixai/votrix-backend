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
Reads `agents/{slug}/` → uploads skills → creates Anthropic managed agent → writes `.cache.json`.

**Runtime** (per chat request):
- `POST /agents/{slug}/chat` reads `.cache.json` for `agent_id + env_id`
- Creates Anthropic session → relays SSE stream

### Local file layout

```
agents/{slug}/
  config.json      # name, model, skills[], integrations[]
  IDENTITY.md      # system prompt component
  SOUL.md          # system prompt component
  .cache.json      # {agent_id, env_id, version} — gitignored, written by build

skills/{slug}/
  SKILL.md         # required — uploaded to Anthropic Skills API
  REFERENCE.md     # optional extra context zipped with SKILL.md
  .cache.json      # {skill_id, content_hash} — gitignored, written by build
```

### Database (3 tables only)

| Table | Purpose |
|---|---|
| `users` | End users (id, display_name, agent_slug) |
| `sessions` | Conversation sessions (user_id, agent_slug, anthropic_session_id) |
| `session_events` | Append-only event log (type, title, body) |

## Running

```bash
uv sync
cp .env.example .env   # fill DATABASE_URL + ANTHROPIC_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Code Conventions

- All DB access via `app/db/queries/*.py` — DAO functions take `AsyncSession` as first arg
- ORM models in `app/db/models/` — one file per table
- Pydantic request/response schemas in `app/models/`
- `app/build/` = provision-time only (no FastAPI dependencies)
- `app/runtime/` = chat-time SSE relay
- `app/client.py` = shared Anthropic singleton via `get_client()`

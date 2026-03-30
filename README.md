# votrix-backend

AI chat backend for Votrix — multi-tenant agent platform with virtual filesystem on Postgres.

## Architecture

```
POST /chat/stream (Vercel AI SDK data stream)
  → build_assistant_context (org_id, agent_id)
    → Postgres: agent_config, blueprint_files, sessions
  → LangGraph (ChatConversationNode)
    → Tools: read, write, votrix_run
      → SQLAlchemy async queries for file ops
    → Gemini Flash (primary) / Gemini 2.0 Flash (backup)
  → Stream response (text deltas, tool calls, tool results)
```

## Setup

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy env
cp .env.example .env
# Fill in DATABASE_URL, GOOGLE_API_KEY

# 3. Apply schema (fresh database)
psql $DATABASE_URL -f supabase/migrations/001_initial.sql
alembic stamp head  # tell Alembic the DB matches current models

# 4. Seed default data
python -c "
import asyncio
from app.db.engine import init_engine
from app.config import get_settings
from app.db.seed import seed_all

init_engine(get_settings().database_url)
asyncio.run(seed_all())
"

# 5. Run
uvicorn app.main:app --reload --port 8000
```

## Migrations

Schema is managed via **Alembic** with async support. ORM models live in `app/db/models/`.

```bash
# Generate a new migration after changing ORM models
alembic revision --autogenerate -m "description of change"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

## OpenAPI → TypeScript Client Generation

FastAPI auto-generates the OpenAPI schema at `/openapi.json`. To generate a TypeScript client:

```bash
# 1. Start the server (or export schema statically)
uvicorn app.main:app --port 8000 &

# 2. Fetch the schema
curl http://localhost:8000/openapi.json -o openapi.json

# 3. Generate TypeScript client (pick one)

# Option A: openapi-typescript + openapi-fetch (recommended, lightweight)
npx openapi-typescript openapi.json -o src/api/schema.d.ts

# Option B: orval (generates axios/fetch hooks for React)
npx orval --input openapi.json --output src/api/client.ts
```

For CI, export the schema without running the server:

```bash
python -c "
import json
from app.main import app
print(json.dumps(app.openapi(), indent=2))
" > openapi.json
```

## Database Schema

8 active tables (agent_version_log and agent_conflicts are commented out):

| Table | Purpose |
|---|---|
| `orgs` | Tenant root, keyed by `org_id` |
| `agent_config` | Agent config + registry (JSONB) |
| `blueprint_files` | Admin-owned virtual filesystem (base files) |
| `user_files` | End-user independent files |
| `end_user_account_info` | Persistent cross-session end user metadata |
| `sessions` | Chat session metadata |
| `session_events` | Append-only event log (user messages, AI replies, tool results) |

### blueprint_files — admin-owned virtual filesystem

Each file node has:

| Field | Description |
|---|---|
| `path` | Full path, e.g. `/skills/booking/SKILL.md` |
| `name` | Filename, e.g. `SKILL.md` |
| `type` | `file` or `directory` |
| `mime_type` | e.g. `text/markdown`, `application/json` |
| `file_class` | `skill` / `skill_asset` / `prompt` / `file` |

### user_files — end-user independent files

| Field | Description |
|---|---|
| `end_user_id` | Always set — identifies the end user |
| `path` | Independent path namespace per end user |
| `content`, `name`, `type`, etc. | Same structure as blueprint_files |

Core filesystem operations and their index coverage:

| Op | Index |
|---|---|
| `ls(parent)` | `idx_blueprint_ls` — B-tree on `(org_id, agent_id, parent)` |
| `read_file(path)` | Unique index on `(org_id, agent_id, path)` |
| `write_file(path)` | Same unique index (upsert) |
| `grep(pattern)` | `idx_blueprint_fts` — GIN full-text search |
| `glob(pattern)` | `idx_blueprint_glob` — `text_pattern_ops` prefix scan |

## API Reference

Scalar API docs at `GET /reference` (interactive). OpenAPI schema at `GET /openapi.json`.

| Tag | Endpoints |
|---|---|
| **chat** | `POST /chat/stream` |
| **agents** | Agent CRUD |
| **files** | ls, read, write, edit, delete, mkdir, mv, grep, glob, tree (all support `end_user_id`) |

## Project Structure

```
app/
├── main.py                  # FastAPI app + lifespan + Scalar docs
├── config.py                # Pydantic settings (DATABASE_URL, API keys)
├── deps.py                  # FastAPI dependencies (get_session)
├── models/                  # Pydantic request/response schemas
│   ├── agent.py             # Agent CRUD schemas
│   ├── chat.py              # ChatStreamRequest/Message
│   └── files.py             # FileEntry, WriteFileRequest, etc.
├── routers/
│   ├── chat.py              # POST /chat/stream
│   ├── agents.py            # Agent CRUD + prompt sections
│   └── files.py             # Virtual filesystem CRUD
├── context/                 # AssistantContext (org_id, agent_id, db_session)
├── llm/                     # LangGraph, prompt builder, model manager
├── tools/                   # read/write/votrix_run + exec handlers
├── db/
│   ├── engine.py            # SQLAlchemy async engine + session factory
│   ├── models/              # ORM models (one per table)
│   │   ├── base.py          # DeclarativeBase + common mixins
│   │   ├── orgs.py
│   │   ├── agent_config.py
│   │   ├── blueprint_files.py
│   │   ├── user_files.py
│   │   ├── end_user_account_info.py
│   │   ├── sessions.py
│   ├── queries/             # DAO layer (SQLAlchemy queries)
│   │   ├── agents.py        # agent_config table queries
│   │   ├── blueprint_files.py # Blueprint filesystem ops
│   │   ├── user_files.py    # User file ops
│   │   ├── sessions.py      # Session + event queries
│   └── seed.py              # First-run seeder
└── utils/                   # ChatManager, logger

alembic/                     # Alembic migration config + versions
supabase/migrations/         # Reference SQL schema
prompts/                     # Seed data (disk → DB on first boot)
```

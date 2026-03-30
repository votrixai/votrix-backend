# votrix-backend

AI chat backend for Votrix — multi-tenant agent platform with virtual filesystem on Supabase.

## Architecture

```
POST /chat/stream (Vercel AI SDK data stream)
  → build_assistant_context (org_id, agent_id)
    → Supabase: agents, agent_files, sessions
  → LangGraph (ChatConversationNode)
    → Tools: read, write, votrix_run
      → Supabase queries for file ops
    → Gemini Flash (primary) / Gemini 2.0 Flash (backup)
  → Stream response (text deltas, tool calls, tool results)
```

## Setup

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy env
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, GOOGLE_API_KEY

# 3. Run Supabase migration
supabase db push
# Or apply manually:
#   psql $DATABASE_URL -f supabase/migrations/001_initial.sql

# 4. Seed default data
python -c "
import asyncio
from app.db.client import init_supabase
from app.config import get_settings
from app.db.seed import seed_all

settings = get_settings()
init_supabase(settings.supabase_url, settings.supabase_service_key)
asyncio.run(seed_all())
"

# 5. Run
uvicorn app.main:app --reload --port 8000
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
# Then use with openapi-fetch:
#   import createClient from 'openapi-fetch'
#   import type { paths } from './schema'
#   const client = createClient<paths>({ baseUrl: 'http://localhost:8000' })

# Option B: orval (generates axios/fetch hooks for React)
npx orval --input openapi.json --output src/api/client.ts

# Option C: openapi-generator (full SDK)
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g typescript-fetch -o src/api/generated
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

7 active tables (agent_version_log and agent_conflicts are disabled):

| Table | Purpose |
|---|---|
| `orgs` | Tenant root, keyed by `org_id` |
| `agents` | Agent config + prompt sections (flat columns) + registry (JSONB) + `prompt_version` |
| `agent_files` | Virtual filesystem with override layer (base + end user overrides) |
| `end_user_account_info` | Persistent cross-session end user metadata |
| `sessions` | Chat session metadata |
| `session_events` | Append-only event log (user messages, AI replies, tool results) |
| `guidelines` | Global singleton prompt guidelines (TOOL_CALLS, SKILLS) |

### agent_files — virtual filesystem

Each file node has:

| Field | Description |
|---|---|
| `path` | Full path, e.g. `/skills/booking/SKILL.md` |
| `name` | Filename, e.g. `SKILL.md` |
| `type` | `file` or `directory` |
| `end_user_perm` | `'none'` (hidden) / `'r'` (read-only) / `'rw'` (personalizable) |
| `end_user_id` | `NULL` = base file, set = end user override |
| `base_version` | Which admin version this file/override was created against |
| `mime_type` | e.g. `text/markdown`, `application/json` |
| `file_class` | `skill` / `skill_asset` / `prompt` / `file` |

**Override layer**: Base files (`end_user_id IS NULL`) are member-owned. End users get a merged view where their overrides win per path. Writes by end users create overrides, never modify base files. Files with `end_user_perm='none'` are hidden from end users.

Core filesystem operations and their index coverage:

| Op | Index |
|---|---|
| `ls(parent)` | `idx_agent_files_ls` — B-tree on `(org_id, agent_id, parent)` where base |
| `ls(parent, end_user_id)` | `idx_agent_files_ls_user` — includes end_user_id for merged view |
| `read_file(path)` | Unique index on `(org_id, agent_id, coalesce(end_user_id,''), path)` |
| `write_file(path)` | Same unique index (upsert) |
| `edit_file(path, old, new)` | Same unique index |
| `grep(pattern)` | Seq scan on `(org_id, agent_id)` filtered set + `idx_agent_files_fts` for FTS |
| `glob(pattern)` | `idx_agent_files_glob` — `text_pattern_ops` prefix scan |

### Versioning + Conflict Resolution

1. Admin edits base files normally via the files API
2. `POST /orgs/{org_id}/agents/{agent_id}/publish` bumps `prompt_version`, detects conflicts with end user overrides, auto-syncs clean end users
3. `GET /conflicts` lists unresolved conflicts (filterable by end_user_id, path)
4. `POST /conflicts/resolve` applies a strategy:
   - `force_admin` — delete conflicting overrides, keep admin version
   - `force_user` — keep overrides, update their base_version
   - `drop_overrides` — delete all overrides for affected users
5. Conflicts are superseded (not stacked) — unique on `(end_user_id, path)`, so a new publish replaces the stale conflict

## API Reference

Scalar API docs at `GET /reference` (interactive). OpenAPI schema at `GET /openapi.json`.

| Tag | Endpoints |
|---|---|
| **chat** | `POST /chat/stream` |
| **agents** | Agent CRUD + prompt section get/put |
| **files** | ls, read, write, edit, delete, mkdir, mv, grep, glob, tree (all support `end_user_id`) |
| **versioning** | publish, conflicts, conflicts/summary, conflicts/resolve, version-log, end-users |

## Project Structure

```
app/
├── main.py                  # FastAPI app + lifespan + Scalar docs
├── config.py                # Pydantic settings
├── models/
│   ├── agent.py             # Agent CRUD schemas
│   ├── chat.py              # ChatStreamRequest/Message
│   ├── conflicts.py         # Publish, conflict, resolve schemas
│   └── files.py             # FileEntry, WriteFileRequest, etc.
├── routers/
│   ├── chat.py              # POST /chat/stream
│   ├── agents.py            # Agent CRUD + prompt sections
│   ├── files.py             # Virtual filesystem CRUD
│   └── conflicts.py         # Publish, versioning, conflict resolution
├── context/                 # AssistantContext (org_id, agent_id)
├── llm/                     # LangGraph, prompt builder, model manager
├── tools/                   # read/write/votrix_run + exec handlers
├── db/
│   ├── client.py            # Supabase singleton
│   ├── queries/
│   │   ├── agents.py        # Agent table queries
│   │   ├── agent_files.py   # Filesystem ops + override layer helpers
│   │   ├── conflicts.py     # Conflict detection, resolution, version log
│   │   ├── sessions.py      # Session + event queries
│   │   └── guidelines.py    # Global guidelines
│   └── seed.py              # First-run seeder
└── utils/                   # ChatManager, logger

supabase/migrations/         # SQL schema (9 tables)
prompts/                     # Seed data (disk → Supabase on first boot)
```

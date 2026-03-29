# votrix-backend

AI chat backend for Votrix — multi-tenant agent platform with virtual filesystem on Supabase.

## Architecture

```
POST /chat/stream (Vercel AI SDK data stream)
  → build_assistant_context (org_id, agent_id)
    → Supabase: agents, agent_prompt_files, sessions
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

6 tables:

| Table | Purpose |
|---|---|
| `orgs` | Tenant root, keyed by `org_id` |
| `agents` | Agent config + prompt sections (flat columns) + registry (JSONB) |
| `agent_prompt_files` | Virtual filesystem — skills, configs, user files |
| `sessions` | Chat session metadata |
| `session_events` | Append-only event log (user messages, AI replies, tool results) |
| `guidelines` | Global singleton prompt guidelines (TOOL_CALLS, SKILLS) |

### agent_prompt_files — virtual filesystem

Each file node has:

| Field | Description |
|---|---|
| `path` | Full path, e.g. `/skills/booking/SKILL.md` |
| `name` | Filename, e.g. `SKILL.md` |
| `type` | `file` or `directory` |
| `access_level` | `owner` / `org_read` / `org_write` |
| `mime_type` | e.g. `text/markdown`, `application/json` |
| `file_class` | `skill` / `skill_asset` / `prompt` / `file` |

Core filesystem operations and their index coverage:

| Op | Index |
|---|---|
| `ls(parent)` | `idx_prompt_files_ls` — B-tree on `(org_id, agent_id, parent)` |
| `read_file(path)` | Unique index on `(org_id, agent_id, path)` |
| `write_file(path)` | Same unique index (upsert) |
| `edit_file(path, old, new)` | Same unique index |
| `grep(pattern)` | Seq scan on `(org_id, agent_id)` filtered set + `idx_prompt_files_fts` for FTS |
| `glob(pattern)` | `idx_prompt_files_glob` — `text_pattern_ops` prefix scan |

## Project Structure

```
app/
├── main.py                  # FastAPI app + lifespan
├── config.py                # Pydantic settings
├── models/                  # Request/response schemas
├── routers/chat.py          # POST /chat/stream
├── context/                 # AssistantContext (org_id, agent_id)
├── llm/                     # LangGraph, prompt builder, model manager
├── tools/                   # read/write/votrix_run + exec handlers
├── db/
│   ├── client.py            # Supabase singleton
│   ├── queries/             # Query functions per table
│   └── seed.py              # First-run seeder
└── utils/                   # ChatManager, logger

supabase/migrations/         # SQL schema
prompts/                     # Seed data (disk → Supabase on first boot)
```

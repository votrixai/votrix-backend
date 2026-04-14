# votrix-backend

FastAPI backend for Votrix. Each session spins up a dedicated Anthropic Managed Agent with per-user scoped Composio MCP tools.

---

## Architecture

### Per-session agent model

Every `POST /users/{user_id}/sessions` call:
1. Reads the agent template from `agents/{agent_id}/config.json`
2. Uploads/caches skills to Anthropic Skills API
3. Creates a new Anthropic Managed Agent (per-user system prompt, MCP servers, skills, tools)
4. Creates an Anthropic session against that agent + environment
5. Stores the session in the database

Chat then streams SSE from the Anthropic session via `POST /agents/{agent_id}/chat`.

### File layout

```
agents/{agent_id}/
  config.json     # name, model, envId, skills[], integrations[], tools[]
  PROMPT.md       # system prompt (user name is appended at provision time)

skills/{skill_name}/
  SKILL.md        # uploaded to Anthropic Skills API
  REFERENCE.md    # optional — zipped together with SKILL.md

app/
  routers/        # FastAPI endpoints (agents, sessions, users, chat)
  management/     # provisioning.py, skills.py, environments.py
  runtime/        # SSE stream relay (sessions.py)
  db/             # SQLAlchemy models + async DAO queries
  models/         # Pydantic request/response schemas
  integrations/   # Composio MCP URL builder
  tools/          # Custom tool definitions (cron, image_generate)
  client.py       # Shared Anthropic client singleton
  config.py       # Pydantic settings (reads .env)

scripts/
  test_marketing_session.py   # E2E test: create user → session → chat
```

### Database tables

| Table | Columns |
|---|---|
| `users` | id, display_name, created_at |
| `sessions` | id, user_id, display_name, session_id (Anthropic), created_at |
| `session_events` | id, session_id, event_index, type, title, body |

### Available agents

| Agent | Skills | Integrations | Custom tools |
|---|---|---|---|
| `marketing-agent` | email-sending, gmail-drafting | Gmail | cron, image_generate |
| `post-agent` | social-media-post-* (6 skills) | LinkedIn, Twitter, Instagram | cron, image_generate |
| `scheduling-agent` | calendar-scheduling | Google Calendar | — |

---

## Setup

### 1. Install dependencies

```bash
# requires Python 3.10+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_ENV=staging

# Supabase Postgres (use the pooler URL for asyncpg)
DATABASE_URL=postgresql+asyncpg://postgres.<project>:<password>@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Composio (get from Composio dashboard)
COMPOSIO_API_KEY=ak_...
COMPOSIO_SERVER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Supabase Storage
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_...

# Gemini (for image generation)
GEMINI_API_KEY=AIza...
```

### 3. Run migrations

```bash
.venv/bin/alembic upgrade head
```

### 4. Pre-upload skills (one-time per account)

Skills must be uploaded to the Anthropic Skills API before session creation works.

```bash
.venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv()
from app.management.skills import get_or_upload_all
get_or_upload_all(['email-sending', 'gmail-drafting'])
"
```

This writes `.skills_registry.json` at the project root (gitignored). Subsequent session creations use the cached skill IDs.

### 5. Create an Anthropic environment (one-time per account)

```bash
.venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv()
from app.client import get_client
env = get_client().beta.environments.create(name='votrix', config={'type': 'cloud'})
print('envId:', env.id)
"
```

Update `envId` in every `agents/*/config.json` with the returned ID.

### 6. Start the server

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

---

## API

### Users

```
POST   /users                    create user        { display_name }
GET    /users                    list users
GET    /users/{user_id}          get user + sessions
DELETE /users/{user_id}          delete user
```

### Sessions

```
POST   /users/{user_id}/sessions   create session   { agent_id, display_name }
GET    /users/{user_id}/sessions   list sessions
GET    /sessions/{session_id}      get session + events
DELETE /sessions/{session_id}      delete session
```

### Chat (SSE)

```
POST /agents/{agent_id}/chat     { user_id, session_id, message }
```

Streams `text/event-stream`:

```
data: {"type": "token",      "content": "..."}
data: {"type": "tool_start", "name": "...", "input": {...}}
data: {"type": "tool_end",   "output": "..."}
data: {"type": "done"}
data: {"type": "error",      "message": "..."}
```

### Agents (read-only templates)

```
GET /agents              list agent templates
GET /agents/{agent_id}   get agent config
```

---

## E2E Test

```bash
# start server first
.venv/bin/uvicorn app.main:app --port 8000

# in another terminal
.venv/bin/python scripts/test_marketing_session.py
.venv/bin/python scripts/test_marketing_session.py --message "帮我起草一封推广邮件"
```

# votrix-backend

## What This Is

Multi-tenant AI chat backend for the Votrix platform. This repo owns the **`POST /chat/stream`** endpoint — the single entry point for all AI conversations. It replaces the chat stream path previously in `votrix-ai-core`.

## End Goal

A self-contained backend service where:
1. Every tenant (`org_id`) has isolated agents, each with its own prompt files and skills
2. Agent prompts and skills live in a **virtual filesystem on Postgres** (not disk), editable via a web file browser
3. The chat endpoint streams responses in **Vercel AI SDK data stream protocol** for direct `useChat()` integration
4. The OpenAPI schema at `/openapi.json` is the **source of truth** for the TypeScript frontend client (generated, not hand-written)

## Architecture

```
Frontend (Next.js useChat)
  ↓ POST /chat/stream { org_id, agent_id, session_id, messages }
  ↓
FastAPI Router (app/routers/chat.py)
  ↓
build_assistant_context_for_stream()     ← loads prompts, skills, session history from DB
  ↓
ChatLangGraphHandler.ainvoke()           ← LangGraph: dispatcher → conversation → (tool loop) → reply
  ├── build_system_messages()            ← assembles prompt sections + guidelines + skills into SystemMessages
  ├── ChatConversationNode               ← Gemini Flash primary, Gemini 2.0 Flash backup
  │   ├── read()                         ← reads from agent_config (prompt sections) or blueprint_files
  │   ├── write()                        ← writes to agent_config or blueprint_files
  │   └── votrix_run()                   ← command dispatch to handlers (bootstrap, registry, fs, search, fetch)
  └── ContextCompactor                   ← trims history when approaching token limits
  ↓
Vercel AI SDK data stream (text deltas, tool calls, tool results, finish)
```

## Key Design Decisions

- **org_id, not host_id or workspace_id** — tenant identifier across all tables and code
- **Postgres (via SQLAlchemy async + asyncpg)** — direct connection, RLS for tenant isolation, `text_pattern_ops` for glob, GIN for full-text search
- **SQLAlchemy ORM + Alembic** — ORM models in `app/db/models/`, auto-generated migrations via Alembic. Schema reference in `supabase/migrations/001_initial.sql`
- **Prompt sections as flat columns on `agent_config` table** — IDENTITY.md, SOUL.md, etc. are read every turn; a single-row select is faster than a file lookup
- **Two-table filesystem** — `blueprint_files` for admin-owned base files, `user_files` for end-user independent files. No override/merge — completely decoupled
- **`file_class` enum** — `skill` (SKILL.md entry points), `skill_asset` (supporting files), `prompt` (top-level agent prompts), `file` (everything else). Frontend uses this to render icons and group skill assets
- **Guidelines loaded from DB, cached in-memory** — TOOL_CALLS.md and SKILLS.md are global singletons, rarely change
- **No `votrix_schema` protobuf dependency** — ChatManager uses plain dicts internally, builds LangChain messages on demand
- **Exec handlers are modular** — each handler exposes `parse(cmd) -> dict | None` and `run(**args) -> str`. Dispatcher does O(1) namespace lookup
- **Session injection** — all DAO functions accept `AsyncSession` as first parameter. Routers inject via `Depends(get_session)`. Tools get session from `AssistantContext.db_session`. Background tasks use `session_scope()` context manager

## Database

8 active tables defined as ORM models in `app/db/models/` (agent_version_log and agent_conflicts are commented out in the reference SQL):

- `orgs` — tenant root
- `agent_config` — prompt sections (flat columns) + registry (JSONB) + `prompt_version` for publish tracking
- `blueprint_files` — admin-owned virtual filesystem. Unique on `(org_id, agent_id, path)`
- `user_files` — end-user independent files. Unique on `(org_id, agent_id, end_user_id, path)`
- `end_user_account_info` — persistent cross-session end user metadata
- `sessions` — chat session metadata
- `session_events` — append-only event log
- `guidelines` — global prompt guidelines

RLS is enabled on agent_config, blueprint_files, user_files, end_user_account_info, sessions, session_events. Backend connects as `postgres` superuser (bypasses RLS). Future: JWT-based policies for direct frontend access.

## What's Migrated vs Not Yet

Migrated from `votrix-ai-core`:
- Full chat stream pipeline: router → context builder → LangGraph → tool loop → stream response
- Core tools: read, write, votrix_run
- Handlers: fs (ls), bootstrap, registry, search, fetch
- ChatManager (simplified, no protobuf)
- ContextCompactor
- Prompt section assembly + skills renderer

**Not yet migrated** (add when needed):
- `receptionist` handler — customer-facing phone/chat receptionist logic
- `booking` handler — Google Calendar integration via Composio
- `billing` handler — Stripe billing commands
- `phone` handler — phone number provisioning
- `sms` handler — SMS sending
- `call` handler — outbound call initiation
- Composio tool adapter (Google Calendar, Gmail, etc.)
- WebSocket chat handler (only HTTP stream is migrated)
- Voice/Telepipe pipeline (out of scope — stays in ai-core)

## Code Conventions

- All DB access goes through `app/db/queries/*.py` — DAO functions accept `AsyncSession` as first parameter
- ORM models in `app/db/models/*.py` — one file per table, match the SQL schema exactly
- Pydantic API models in `app/models/*.py` — request/response schemas for FastAPI
- Tool context (org_id, agent_id, db_session) is passed via `ContextVar` in `app/tools/tool_context.py`, set before each tool execution loop
- Prompt sections are identified by key: `identity`, `soul`, `agents`, `user`, `tools`, `bootstrap`
- File paths in blueprint_files/user_files always start with `/` (e.g. `/skills/booking/SKILL.md`)
- Handlers follow the `parse(cmd) -> Optional[Dict]` + `run(**args) -> str` pattern
- `build_system_messages()` is async (loads guidelines from DB)

## Running

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in DATABASE_URL, GOOGLE_API_KEY
# Apply schema (if fresh DB):
#   psql $DATABASE_URL -f supabase/migrations/001_initial.sql
#   alembic stamp head
# Or run Alembic migrations:
#   alembic upgrade head
# Seed:
#   python -c "import asyncio; from app.db.engine import init_engine; from app.config import get_settings; from app.db.seed import seed_all; init_engine(get_settings().database_url); asyncio.run(seed_all())"
uvicorn app.main:app --reload --port 8000
```

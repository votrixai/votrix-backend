# votrix-backend

## What This Is

Multi-tenant AI chat backend for the Votrix platform. This repo owns the **`POST /chat/stream`** endpoint — the single entry point for all AI conversations. It replaces the chat stream path previously in `votrix-ai-core`.

## End Goal

A self-contained backend service where:
1. Every tenant (`org_id`) has isolated agents, each with its own prompt files and skills
2. Agent prompts and skills live in a **virtual filesystem on Supabase** (not disk), editable via a web file browser
3. The chat endpoint streams responses in **Vercel AI SDK data stream protocol** for direct `useChat()` integration
4. The OpenAPI schema at `/openapi.json` is the **source of truth** for the TypeScript frontend client (generated, not hand-written)

## Architecture

```
Frontend (Next.js useChat)
  ↓ POST /chat/stream { org_id, agent_id, session_id, messages }
  ↓
FastAPI Router (app/routers/chat.py)
  ↓
build_assistant_context_for_stream()     ← loads prompts, skills, session history from Supabase
  ↓
ChatLangGraphHandler.ainvoke()           ← LangGraph: dispatcher → conversation → (tool loop) → reply
  ├── build_system_messages()            ← assembles prompt sections + guidelines + skills into SystemMessages
  ├── ChatConversationNode               ← Gemini Flash primary, Gemini 2.0 Flash backup
  │   ├── read()                         ← reads from agents table (prompt sections) or agent_prompt_files
  │   ├── write()                        ← writes to agents table or agent_prompt_files
  │   └── votrix_run()                   ← command dispatch to handlers (bootstrap, registry, fs, search, fetch)
  └── ContextCompactor                   ← trims history when approaching token limits
  ↓
Vercel AI SDK data stream (text deltas, tool calls, tool results, finish)
```

## Key Design Decisions

- **org_id, not host_id or workspace_id** — tenant identifier across all tables and code
- **Supabase (Postgres), not MongoDB** — RLS for tenant isolation, `text_pattern_ops` for glob, native `regexp_replace` for sed, `ltree`-ready for future hierarchical queries
- **Prompt sections as flat columns on `agents` table** — IDENTITY.md, SOUL.md, etc. are read every turn; a single-row select is faster than a file lookup
- **Everything else in `agent_prompt_files`** — skills, configs, user-created files. Virtual filesystem with `path`, `parent`, `name`, `type`, `access_level`, `file_class`
- **`file_class` enum** — `skill` (SKILL.md entry points), `skill_asset` (supporting files), `prompt` (top-level agent prompts), `file` (everything else). Frontend uses this to render icons and group skill assets
- **`access_level` enum** — `owner` (only creator sees it), `org_read` (whole org can view), `org_write` (whole org can edit). NOT chmod — no Unix users/groups in a SaaS
- **Guidelines loaded from DB, cached in-memory** — TOOL_CALLS.md and SKILLS.md are global singletons, rarely change
- **No `votrix_schema` protobuf dependency** — ChatManager uses plain dicts internally, builds LangChain messages on demand
- **Exec handlers are modular** — each handler exposes `parse(cmd) -> dict | None` and `run(**args) -> str`. Dispatcher does O(1) namespace lookup

## Database

6 tables in `supabase/migrations/001_initial.sql`:

- `orgs` — tenant root
- `agents` — prompt sections (flat columns) + registry (JSONB)
- `agent_prompt_files` — virtual filesystem (the big one: ls, read, write, edit, grep, glob)
- `sessions` — chat session metadata
- `session_events` — append-only event log
- `guidelines` — global prompt guidelines

RLS is enabled on agents, agent_prompt_files, sessions, session_events. Backend uses service_role key (bypasses RLS). Future: JWT-based policies for direct frontend access.

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

- All DB access goes through `app/db/queries/*.py` — no direct `get_supabase().table(...)` calls in business logic
- Tool context (org_id, agent_id) is passed via `ContextVar` in `app/tools/tool_context.py`, set before each tool execution loop
- Prompt sections are identified by key: `identity`, `soul`, `agents`, `user`, `tools`, `bootstrap`
- File paths in agent_prompt_files always start with `/` (e.g. `/skills/booking/SKILL.md`)
- Handlers follow the `parse(cmd) -> Optional[Dict]` + `run(**args) -> str` pattern
- `build_system_messages()` is async (loads guidelines from Supabase)

## Running

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, GOOGLE_API_KEY
supabase db push      # or apply 001_initial.sql manually
# seed: python -c "import asyncio; from app.db.client import init_supabase; from app.config import get_settings; from app.db.seed import seed_all; s=get_settings(); init_supabase(s.supabase_url, s.supabase_service_key); asyncio.run(seed_all())"
uvicorn app.main:app --reload --port 8000
```

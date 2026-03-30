# votrix-backend

## What This Is

Multi-tenant agentic filesystem backend for the Votrix platform. Provides full CRUD for orgs, agents, and a two-table virtual filesystem (blueprint_files for admins, user_files for end users) — all backed by Postgres.

## End Goal

A self-contained backend service where:
1. Every tenant (org UUID) has isolated agents, each with its own files and integrations
2. Agent files live in a **virtual filesystem on Postgres** (not disk), editable via API
3. The OpenAPI schema at `/openapi.json` is the **source of truth** for the TypeScript frontend client (generated, not hand-written)

## Architecture

```
Frontend (Next.js / any client)
  ↓
FastAPI (app/main.py)
  ├── /orgs            — org CRUD (app/routers/orgs.py)
  ├── /orgs/.../agents — agent CRUD (app/routers/agents.py)
  └── /files           — file CRUD for blueprint_files & user_files (app/routers/files.py)
  ↓
SQLAlchemy async ORM → Postgres (asyncpg)
  ├── orgs
  ├── blueprint_agents
  ├── agent_integrations
  ├── blueprint_files
  ├── user_files
  └── end_user_accounts
```

## Key Design Decisions

- **UUID `id` as sole org identifier** — no text slug for orgs; child tables reference `orgs.id` via UUID FK
- **Postgres (via SQLAlchemy async + asyncpg)** — direct connection, RLS for tenant isolation, `text_pattern_ops` for glob, GIN for full-text search
- **SQLAlchemy ORM + Alembic** — ORM models in `app/db/models/`, auto-generated migrations via Alembic. Schema reference in `supabase/migrations/001_initial.sql`
- **Two-table filesystem** — `blueprint_files` for admin-owned base files, `user_files` for end-user independent files. No override/merge — completely decoupled
- **`file_class` enum** — `skill` (SKILL.md entry points), `skill_asset` (supporting files), `prompt` (top-level agent prompts), `file` (everything else). Frontend uses this to render icons and group skill assets
- **Session injection** — all DAO functions accept `AsyncSession` as first parameter. Routers inject via `Depends(get_session)`

## Database

6 active tables defined as ORM models in `app/db/models/`:

- `orgs` — tenant root (UUID `id`, display_name, timezone, metadata)
- `blueprint_agents` — agent templates. UUID `id` PK, `slug` unique per org, `name` display name
- `agent_integrations` — per-agent tool integrations. FK `blueprint_agent_id` → `blueprint_agents.id`
- `blueprint_files` — admin-owned virtual filesystem. FK `blueprint_agent_id` → `blueprint_agents.id`, unique on `(blueprint_agent_id, path)`
- `user_files` — end-user independent files. FK `blueprint_agent_id` back-reference, unique on `(blueprint_agent_id, end_user_id, path)`
- `end_user_accounts` — persistent end user metadata, org-scoped. Unique on `(org_id, end_user_id)`

RLS is enabled on blueprint_agents, agent_integrations, blueprint_files, user_files, end_user_accounts. Backend connects as `postgres` superuser (bypasses RLS).

## Code Conventions

- All DB access goes through `app/db/queries/*.py` — DAO functions accept `AsyncSession` as first parameter
- ORM models in `app/db/models/*.py` — one file per table, match the SQL schema exactly
- Pydantic API models in `app/models/*.py` — request/response schemas for FastAPI
- File paths in blueprint_files/user_files always start with `/` (e.g. `/skills/booking/SKILL.md`)

## Running

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in DATABASE_URL
# Apply schema (if fresh DB):
#   psql $DATABASE_URL -f supabase/migrations/001_initial.sql
#   alembic stamp head
# Or run Alembic migrations:
#   alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

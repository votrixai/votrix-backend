# votrix-backend

## What This Is

Multi-tenant agentic filesystem backend for the Votrix platform. Provides full CRUD for orgs, blueprint agents, end users, and a two-table virtual filesystem (blueprint_files for agent templates, user_files for end users) — all backed by Postgres.

## End Goal

A self-contained backend service where:
1. Every tenant (org) has blueprint agents, each with its own template files and integrations
2. End users get their own copy of agent files when instantiated via `POST /users/{user_id}/agents`
3. All files live in a **virtual filesystem on Postgres** (not disk), editable via API
4. The OpenAPI schema at `/openapi.json` is the **source of truth** for the TypeScript frontend client (generated, not hand-written)

## Architecture

```
Frontend (Next.js / any client)
  ↓
FastAPI (app/main.py)
  ├── /orgs                                          — org CRUD (app/routers/orgs.py)
  ├── /orgs/{org_id}/agents                          — list/create agents (app/routers/agents.py)
  ├── /agents/{agent_id}                             — get/update/delete agent
  ├── /agents/{agent_id}/files                       — blueprint file ops (app/routers/files.py)
  ├── /orgs/{org_id}/users                           — list/create users (app/routers/end_user_accounts.py)
  ├── /users/{user_id}                               — get/update/delete user
  ├── /users/{user_id}/agents                        — link/list/unlink agents
  └── /users/{user_id}/agents/{id}/files             — user file ops (app/routers/user_files.py)
  ↓
SQLAlchemy async ORM → Postgres (asyncpg)
```

## Key Design Decisions

- **UUID `id` as sole identifier** — all entities use UUID PKs, no text slugs. URLs use UUIDs directly
- **Flat routes for direct access** — `/agents/{id}`, `/users/{id}` don't need org context. Org-scoped routes only for listing and creating
- **Postgres (via SQLAlchemy async + asyncpg)** — direct connection, RLS for tenant isolation, `text_pattern_ops` for glob, GIN for full-text search
- **SQLAlchemy ORM + Alembic** — ORM models in `app/db/models/`, schema reference in `supabase/migrations/001_initial.sql`
- **Two-table filesystem** — `blueprint_files` for agent templates, `user_files` for end-user copies. Completely decoupled
- **Agent instantiation** — `POST /users/{user_id}/agents` creates a link and replicates blueprint_files → user_files
- **Default blueprint files** — creating an agent auto-populates files from `prompts/agents/default/` on disk. Opt out with `skip_defaults: true`. If `seed_from` is set, defaults are skipped (clone takes priority)
- **Soft delete** — `DELETE /agents/{id}?soft=true` sets `deleted_at`, hides from list but agent remains GET-able with files intact. A subsequent hard `DELETE /agents/{id}` fully removes it with cascade
- **Session injection** — all DAO functions accept `AsyncSession` as first parameter. Routers inject via `Depends(get_session)`

## Database

11 tables defined as ORM models in `app/db/models/`:

- `orgs` — tenant root (UUID `id`, display_name, timezone, metadata, integrations)
- `blueprint_agents` — agent templates. UUID `id`, FK `org_id` → `orgs.id`, `display_name`, nullable `deleted_at` for soft delete
- `agent_integrations` — global integration catalog. UUID `id`, unique `slug`, `display_name`, `provider_slug`, `provider_config`
- `agent_integration_tools` — tools per integration. FK `agent_integration_id`, unique `(agent_integration_id, slug)`
- `blueprint_agent_integrations` — agent ↔ integration join. FKs to `blueprint_agents` and `agent_integrations`, unique on pair
- `blueprint_agent_integration_tools` — enabled tools per agent-integration link. FKs to `blueprint_agent_integrations` and `agent_integration_tools`, unique on pair
- `blueprint_files` — admin-owned virtual filesystem. FK `blueprint_agent_id`, unique on `(blueprint_agent_id, path)`
- `end_user_accounts` — end user accounts. FK `org_id` → `orgs.id`, `display_name`, `sandbox`
- `user_files` — end-user files. FKs to `blueprint_agents.id` and `end_user_accounts.id`, unique on `(blueprint_agent_id, user_account_id, path)`
- `end_user_agents` — many-to-many linking users to agents. FKs to both, unique on pair

RLS enabled on all tables. Backend connects as `postgres` superuser (bypasses RLS).

## Code Conventions

- All DB access goes through `app/db/queries/*.py` — DAO functions accept `AsyncSession` as first parameter
- ORM models in `app/db/models/*.py` — one file per table, match the SQL schema exactly
- Pydantic API models in `app/models/*.py` — request/response schemas for FastAPI
- All path params for IDs typed as `uuid.UUID` — FastAPI auto-validates
- File paths in blueprint_files/user_files always start with `/` (e.g. `/skills/booking/SKILL.md`)

## Running

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY
# Apply schema (if fresh DB):
#   psql $DATABASE_URL -f supabase/migrations/001_initial.sql
#   alembic stamp head
# Or run Alembic migrations:
#   alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Supabase Storage (binary files)

Binary files (images, PDFs, sqlite, etc.) are stored in Supabase Storage. Text files stay in Postgres.

1. In the Supabase dashboard → Storage → create a **private** bucket named `files`
2. Add to `.env`:
   ```
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_SERVICE_KEY=your_service_role_key
   ```
3. Run `alembic upgrade head` to add the `storage_path` column

Upload binary files via `POST /agents/{id}/files/upload` (multipart). Read returns a signed download URL.

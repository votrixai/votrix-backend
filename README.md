# votrix-backend

Multi-tenant agentic filesystem backend — blueprint agents with virtual file systems, user instantiation, and file replication.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env  # fill in DATABASE_URL

# Apply schema (fresh database)
psql $DATABASE_URL -f supabase/migrations/001_initial.sql
alembic stamp head

# Or run Alembic migrations
alembic upgrade head

# Run
uvicorn app.main:app --reload --port 8000
```

## API Reference

Scalar API docs at `GET /reference`. OpenAPI schema at `GET /openapi.json`.

### Routes

| Tag | Route | Description |
|-----|-------|-------------|
| **orgs** | `POST /orgs` | Create org |
| | `GET /orgs` | List orgs |
| | `GET /orgs/{org_id}` | Get org |
| | `PATCH /orgs/{org_id}` | Update org |
| | `DELETE /orgs/{org_id}` | Delete org |
| **agents** | `POST /orgs/{org_id}/agents` | Create blueprint agent |
| | `GET /orgs/{org_id}/agents` | List agents in org |
| | `GET /agents/{agent_id}` | Get agent detail |
| | `PATCH /agents/{agent_id}` | Update agent |
| | `DELETE /agents/{agent_id}` | Delete agent |
| **agent-files** | `GET /agents/{agent_id}/files` | List directory |
| | `GET /agents/{agent_id}/files/read` | Read file |
| | `POST /agents/{agent_id}/files` | Write file |
| | `PATCH /agents/{agent_id}/files` | Edit file |
| | `DELETE /agents/{agent_id}/files` | Delete file |
| | `POST /agents/{agent_id}/files/mkdir` | Create directory |
| | `POST /agents/{agent_id}/files/mv` | Move/rename |
| | `GET /agents/{agent_id}/files/grep` | Regex search |
| | `GET /agents/{agent_id}/files/glob` | Glob match |
| | `GET /agents/{agent_id}/files/tree` | Full tree |
| **users** | `POST /orgs/{org_id}/users` | Create end user |
| | `GET /orgs/{org_id}/users` | List users in org |
| | `GET /users/{user_id}` | Get user detail |
| | `PATCH /users/{user_id}` | Update user |
| | `DELETE /users/{user_id}` | Delete user |
| | `POST /users/{user_id}/agents` | Instantiate agent (link + replicate files) |
| | `GET /users/{user_id}/agents` | List user's agents |
| | `DELETE /users/{user_id}/agents/{id}` | Unlink agent |
| **user-files** | `/users/{user_id}/agents/{id}/files/...` | Same 10 file ops as agent-files |

## Database Schema

7 tables with UUID primary keys and FK cascades:

| Table | Purpose |
|-------|---------|
| `orgs` | Tenant root |
| `blueprint_agents` | Agent templates (name, org_id) |
| `agent_integrations` | Per-agent integration slugs |
| `blueprint_files` | Admin-owned virtual filesystem |
| `end_user_accounts` | End user accounts (display_name, sandbox) |
| `user_files` | End-user file copies (FK to blueprint_agent + user_account) |
| `end_user_agent_links` | Many-to-many user ↔ agent |

## Project Structure

```
app/
├── main.py                    # FastAPI app + lifespan + Scalar docs
├── config.py                  # Pydantic settings (DATABASE_URL)
├── models/                    # Pydantic request/response schemas
│   ├── agent.py
│   ├── end_user_account.py
│   ├── files.py
│   └── org.py
├── routers/
│   ├── orgs.py                # Org CRUD
│   ├── agents.py              # Blueprint agent CRUD
│   ├── files.py               # Blueprint file ops
│   ├── end_user_accounts.py   # User CRUD + agent instantiation
│   └── user_files.py          # User file ops
├── db/
│   ├── engine.py              # SQLAlchemy async engine + session factory
│   ├── models/                # ORM models (one per table)
│   └── queries/               # DAO layer (SQLAlchemy queries)
└── tools/platform/            # Tool declarations + stub handlers

supabase/migrations/           # Reference SQL schema
alembic/                       # Alembic migration config
```

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic current
```

## TypeScript Client Generation

```bash
# Export schema
python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json

# Generate types
npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

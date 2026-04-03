"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from scalar_fastapi import get_scalar_api_reference

from app.config import get_settings
from app.db.engine import dispose_engine, init_engine
from app.llm.engine import AgentEngine
from app.routers import agent_files, agents, chat, end_user_accounts, integrations, orgs, sessions, user_files, user_runtime
from app.routers.agents import load_default_blueprint_files
from app.short_id import ShortIdMiddleware, patch_openapi
from app.ws import router as ws_router
from app.integrations import catalog as composio_catalog

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    load_default_blueprint_files()

    # Kick off Composio catalog refresh in the background so startup isn't blocked.
    # GET /integrations returns only platform items until the cache is ready.
    init_engine(settings.database_url)
    logger.info("SQLAlchemy engine initialized")

    # psycopg3 pool for LangGraph checkpointer (requires plain postgresql:// DSN)
    pg_url = settings.langgraph_database_url or settings.database_url.replace("+asyncpg", "")
    pg_pool = AsyncConnectionPool(pg_url, open=False)
    await pg_pool.open()
    await AgentEngine.init(pg_pool)
    logger.info("LLM engine initialized")

    asyncio.create_task(composio_catalog.refresh_cache(settings.composio_api_key))

    yield

    await pg_pool.close()
    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Votrix Backend",
    description="Multi-tenant agentic filesystem backend backed by Postgres.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/swagger",
    redoc_url=None,
)

app.add_middleware(ShortIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orgs.router)
app.include_router(agents.router)
app.include_router(end_user_accounts.router)
app.include_router(agent_files.router)
app.include_router(user_files.router)
app.include_router(integrations.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(user_runtime.router)
app.include_router(ws_router.router)


# Patch OpenAPI schema to show prefixed short IDs instead of raw UUIDs
_original_openapi = app.openapi


def _patched_openapi():
    schema = _original_openapi()
    return patch_openapi(schema)


app.openapi = _patched_openapi


@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Votrix API",
    )

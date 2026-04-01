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
from app.routers import agent_integrations, agents, chat, end_user_accounts, files, integrations, org_integrations, orgs, user_files
from app.ws import router as ws_router
from app.integrations import cache as composio_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    init_engine(settings.database_url)
    logger.info("SQLAlchemy engine initialized")

    # psycopg3 pool for LangGraph checkpointer
    # DATABASE_URL may be postgresql+asyncpg://... — strip the driver suffix
    pg_url = settings.database_url.replace("+asyncpg", "")
    pg_pool = AsyncConnectionPool(pg_url, open=False)
    await pg_pool.open()
    await AgentEngine.init(pg_pool)
    logger.info("LLM engine initialized")

    asyncio.create_task(composio_cache.refresh(settings.composio_api_key))

    yield

    await pg_pool.close()
    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Votrix Backend",
    description="Multi-tenant agentic filesystem backend backed by Postgres.",
    version="0.1.0",
    lifespan=lifespan,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orgs.router, tags=["orgs"])
app.include_router(org_integrations.router, tags=["org-integrations"])
app.include_router(agents.router, tags=["agents"])
app.include_router(agent_integrations.router)
app.include_router(end_user_accounts.router, tags=["users"])
app.include_router(files.router, tags=["agent-files"])
app.include_router(user_files.router, tags=["user-files"])
app.include_router(integrations.router)
app.include_router(chat.router)
app.include_router(ws_router.router)


@app.get("/reference", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Votrix API",
    )

"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.config import get_settings
from app.db.engine import dispose_engine, init_engine
from app.routers import agents, end_user_accounts, files, orgs, user_files

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    init_engine(settings.database_url)
    logger.info("SQLAlchemy async engine initialized")
    yield
    await dispose_engine()
    logger.info("Database engine disposed")


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
app.include_router(agents.router, tags=["agents"])
app.include_router(end_user_accounts.router, tags=["users"])
app.include_router(files.router, tags=["agent-files"])
app.include_router(user_files.router, tags=["user-files"])


@app.get("/reference", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Votrix API",
    )

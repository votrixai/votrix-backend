"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.config import get_settings
from app.db.client import init_supabase
from app.routers import agents, chat, conflicts, files

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    init_supabase(settings.supabase_url, settings.supabase_service_key)
    logger.info("Supabase client initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Votrix Backend",
    description="Multi-tenant AI chat backend. Streams responses in Vercel AI SDK data stream protocol.",
    version="0.1.0",
    lifespan=lifespan,
    redoc_url=None,  # replaced by Scalar
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(agents.router, tags=["agents"])
app.include_router(files.router, tags=["files"])
app.include_router(conflicts.router, tags=["versioning"])


@app.get("/reference", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Votrix API",
    )

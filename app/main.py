from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

load_dotenv()

from app.config import get_settings
from app.logging import setup as setup_logging
from app.routers import agents, chat, cron, files, sessions, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(
        app_env=settings.app_env,
        sentry_dsn=settings.sentry_dsn,
        log_level=settings.log_level,
    )
    yield


app = FastAPI(title="Votrix Backend", lifespan=lifespan, docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(files.router)
app.include_router(cron.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    return HTMLResponse(
        """
<!doctype html>
<html>
<head><title>Votrix API</title><meta charset="utf-8"/></head>
<body>
<script id="api-reference" data-url="/openapi.json"></script>
<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body>
</html>
"""
    )

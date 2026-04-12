from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import agents, chat, sessions, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Votrix Backend", lifespan=lifespan)

app.include_router(agents.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

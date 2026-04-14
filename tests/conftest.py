import os
import tempfile

# Must be set before app imports so get_settings() lru_cache picks them up
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-key")

# Create a temp SQLite file for the test session and point settings at it
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
_TEST_DB_URL = f"sqlite+aiosqlite:///{_tmp_db_path}"
os.environ["DATABASE_URL"] = _TEST_DB_URL

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from unittest.mock import patch

from app.main import app
from app.db.models.base import Base
import app.db.engine as db_engine_module


def _make_nullpool_engine():
    return create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Create ORM tables once before all tests, drop them after."""
    engine = _make_nullpool_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    yield
    engine = _make_nullpool_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.unlink(_tmp_db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
async def isolate_db():
    """Give each test its own NullPool engine so connections never cross event loops."""
    engine = _make_nullpool_engine()
    db_engine_module._engine = engine
    db_engine_module._session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    yield
    await engine.dispose()
    db_engine_module._engine = None
    db_engine_module._session_factory = None


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def user(client):
    r = await client.post("/users", json={"display_name": "Test User"})
    assert r.status_code == 201
    data = r.json()
    yield data
    await client.delete(f"/users/{data['id']}")


@pytest.fixture
async def provisioned_user(client, user):
    with patch("app.routers.users.provisioning.create_user_agent", return_value="agt_test123"):
        r = await client.post(f"/users/{user['id']}/provision?agent_id=marketing-agent")
    assert r.status_code == 200
    yield {**user, "agent_id": "agt_test123"}

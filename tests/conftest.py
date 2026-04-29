import importlib
import os
import tempfile
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Must be set before app imports so get_settings() lru_cache picks them up
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-key")

# Create a temp SQLite file for the test session and point settings at it
_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
_TEST_DB_URL = f"sqlite+aiosqlite:///{_tmp_db_path}"
os.environ["DATABASE_URL"] = _TEST_DB_URL

app = importlib.import_module("app.main").app
Base = importlib.import_module("app.db.models._base").Base
db_engine_module = importlib.import_module("app.db.engine")

from app.auth import AuthedUser, require_user


_TEST_USER_ID = uuid.uuid4()
_TEST_USER = AuthedUser(id=_TEST_USER_ID, email="test@example.com")


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
    app.dependency_overrides[require_user] = lambda: _TEST_USER
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(require_user, None)


@pytest.fixture
async def db_user(client):
    """Create a User row + workspace in DB matching the auth override."""
    from app.db.engine import session_scope
    from app.db.models.users import User
    from app.db.models.workspaces import Workspace, WorkspaceMember

    async with session_scope() as db:
        user = User(id=_TEST_USER_ID, display_name="Test User")
        db.add(user)
        await db.commit()

        ws = Workspace(display_name="Test User")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)

        member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
        db.add(member)
        await db.commit()

    yield {"id": str(_TEST_USER_ID), "workspace_id": str(ws.id)}

    async with session_scope() as db:
        from sqlalchemy import delete
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.user_id == _TEST_USER_ID))
        await db.execute(delete(Workspace).where(Workspace.id == ws.id))
        await db.execute(delete(User).where(User.id == _TEST_USER_ID))
        await db.commit()

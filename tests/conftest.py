"""Shared fixtures — async SQLite engine + session + httpx client."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import JSON, String, Text, event, types
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models.base import Base

# Import all models so Base.metadata knows about every table.
import app.db.models.orgs  # noqa: F401
import app.db.models.blueprint_agents  # noqa: F401
import app.db.models.blueprint_files  # noqa: F401
import app.db.models.end_user_accounts  # noqa: F401
import app.db.models.end_user_agent_links  # noqa: F401
import app.db.models.user_files  # noqa: F401


class _UUIDAsString(types.TypeDecorator):
    """Store UUID as plain text in SQLite, auto-converting uuid.UUID ↔ str."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        return value  # keep as string — matches how app works with Text columns


def _patch_columns_for_sqlite():
    """Replace Postgres-specific column types with SQLite-compatible ones."""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            type_name = type(col.type).__name__
            if type_name == "JSONB":
                col.type = JSON()
            elif type_name == "UUID":
                col.type = _UUIDAsString()
            elif type_name in ("Enum", "SAEnum"):
                col.type = Text()
            elif type_name == "ARRAY":
                col.type = JSON()  # store arrays as JSON in SQLite

        # Remove Postgres-specific indexes (text_pattern_ops etc.)
        pg_indexes = [
            idx for idx in list(table.indexes)
            if idx.dialect_options.get("postgresql", {}).get("ops", None)
        ]
        for idx in pg_indexes:
            table.indexes.discard(idx)


_patch_columns_for_sqlite()


# ---------------------------------------------------------------------------
# Engine / session fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
        dbapi_conn.create_function("now", 0, lambda: __import__("datetime").datetime.utcnow().isoformat())
        cursor.close()

    return eng


@pytest.fixture(autouse=True)
async def _create_tables(engine):
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


# ---------------------------------------------------------------------------
# httpx AsyncClient for router tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(engine):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db.engine import get_session

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

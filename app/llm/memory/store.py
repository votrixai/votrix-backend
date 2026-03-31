"""Long-term memory: cross-session persistence via PostgresStore.

Falls back to InMemoryStore if langgraph-checkpoint-postgres is not installed.
"""

import logging

logger = logging.getLogger(__name__)


async def create_store(db_url: str):
    """Create a store for cross-session long-term memory.

    Tries AsyncPostgresStore first; falls back to InMemoryStore.
    Calls .setup() to run DB migrations on first use.
    """
    if not db_url:
        logger.warning("No database URL provided — using InMemoryStore (non-persistent)")
        return _memory_store()

    try:
        from langgraph.store.postgres.aio import AsyncPostgresStore

        store = AsyncPostgresStore.from_conn_string(db_url)
        await store.setup()
        logger.info("PostgresStore initialized")
        return store
    except ImportError:
        logger.warning(
            "langgraph-checkpoint-postgres not installed — using InMemoryStore. "
            "Add langgraph-checkpoint-postgres to dependencies for persistent long-term memory."
        )
        return _memory_store()
    except Exception as e:
        logger.error(f"Failed to initialize PostgresStore ({e}) — falling back to InMemoryStore")
        return _memory_store()


def _memory_store():
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()

"""Short-term memory: per-thread session persistence via PostgresSaver.

Falls back to MemorySaver if langgraph-checkpoint-postgres is not installed
(useful for local dev without a Postgres connection).
"""

import logging

logger = logging.getLogger(__name__)


async def create_checkpointer(db_url: str):
    """Create a checkpointer for per-thread session persistence.

    Tries AsyncPostgresSaver first; falls back to MemorySaver.
    Calls .setup() to run DB migrations on first use.
    """
    if not db_url:
        logger.warning("No database URL provided — using MemorySaver (non-persistent)")
        return _memory_saver()

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await checkpointer.setup()
        logger.info("PostgresSaver checkpointer initialized")
        return checkpointer
    except ImportError:
        logger.warning(
            "langgraph-checkpoint-postgres not installed — using MemorySaver. "
            "Add langgraph-checkpoint-postgres to dependencies for persistent sessions."
        )
        return _memory_saver()
    except Exception as e:
        logger.error(f"Failed to initialize PostgresSaver ({e}) — falling back to MemorySaver")
        return _memory_saver()


def _memory_saver():
    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()

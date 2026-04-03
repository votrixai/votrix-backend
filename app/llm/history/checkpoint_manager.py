class CheckpointManager:
    """
    Manages LangGraph checkpoint rows in Postgres for a given connection pool.

    LangGraph owns writes (AsyncPostgresSaver persists state automatically).
    This class only handles lifecycle operations:
      - prune: remove stale intermediate rows after each turn
      - clear: wipe all rows when a conversation is reset

    thread_id = str(session_id)  — caller resolves this before calling here.
    """

    def __init__(self, pool) -> None:
        self._pool = pool

    async def prune(self, thread_id: str) -> None:
        """
        Delete all checkpoint rows except the single latest one for this thread.
        Also removes orphaned checkpoint_writes rows.

        Called by AgentEngine after every astream() turn.
        Safe to call unconditionally — no-op if only one row exists.
        """
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                DELETE FROM checkpoints
                WHERE thread_id = %s
                  AND checkpoint_id != (
                      SELECT checkpoint_id FROM checkpoints
                      WHERE thread_id = %s
                      ORDER BY checkpoint_id DESC
                      LIMIT 1
                  )
                """,
                (thread_id, thread_id),
            )
            await conn.execute(
                """
                DELETE FROM checkpoint_writes
                WHERE thread_id = %s
                  AND checkpoint_id NOT IN (
                      SELECT checkpoint_id FROM checkpoints
                      WHERE thread_id = %s
                  )
                """,
                (thread_id, thread_id),
            )

    async def clear(self, thread_id: str) -> None:
        """
        Delete ALL checkpoint rows and checkpoint_writes rows for this thread.
        Called when a conversation is fully reset.
        """
        async with self._pool.connection() as conn:
            await conn.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                (thread_id,),
            )
            await conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (thread_id,),
            )

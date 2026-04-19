"""sessions: use provider_session_id as primary key (Text), drop session_id column

Revision ID: 013
Revises: 011
Create Date: 2026-04-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop RLS policies that reference sessions before touching the table
    op.execute('drop policy if exists "Users can access their own sessions" on public.sessions')
    op.execute('drop policy if exists "Users can access events for their own sessions" on public.session_events')

    # Drop FK from session_events → sessions.id (UUID)
    op.drop_constraint("session_events_session_id_fkey", "session_events", type_="foreignkey")

    # Rename old sessions table, create new one with Text PK
    op.execute("ALTER TABLE sessions RENAME TO sessions_old")
    op.create_table(
        "sessions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_session_title", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Text(), nullable=True),
        sa.Column("agent_slug", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Copy rows where session_id (Anthropic ID) is set
    op.execute("""
        INSERT INTO sessions (id, user_id, provider_session_title, provider, agent_id, agent_slug, created_at, updated_at)
        SELECT session_id, user_id, provider_session_title, provider, agent_id, agent_slug, created_at, updated_at
        FROM sessions_old
        WHERE session_id IS NOT NULL
    """)

    # Migrate session_events.session_id: UUID → Anthropic text ID via join
    op.execute("ALTER TABLE session_events ADD COLUMN new_session_id TEXT")
    op.execute("""
        UPDATE session_events se
        SET new_session_id = sol.session_id
        FROM sessions_old sol
        WHERE sol.id = se.session_id
          AND sol.session_id IS NOT NULL
    """)
    # Drop events that can't be remapped (sessions with no Anthropic ID)
    op.execute("DELETE FROM session_events WHERE new_session_id IS NULL")
    op.execute("ALTER TABLE session_events DROP COLUMN session_id")
    op.execute("ALTER TABLE session_events RENAME COLUMN new_session_id TO session_id")
    op.execute("ALTER TABLE session_events ALTER COLUMN session_id SET NOT NULL")

    op.drop_table("sessions_old")

    # Re-add FK
    op.create_foreign_key(
        "session_events_session_id_fkey",
        "session_events", "sessions",
        ["session_id"], ["id"],
        ondelete="CASCADE",
    )

    # Recreate RLS policies
    op.execute("alter table public.sessions enable row level security")
    op.execute("""
        create policy "Users can access their own sessions"
            on public.sessions for all
            using (user_id = auth.uid())
            with check (user_id = auth.uid())
    """)
    op.execute("alter table public.session_events enable row level security")
    op.execute("""
        create policy "Users can access events for their own sessions"
            on public.session_events for all
            using (session_id in (select id from public.sessions where user_id = auth.uid()))
    """)


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for PK type change")

"""user_agents cache + sessions.agent_slug; drop users.agent_id/provider

Revision ID: 009
Revises: 008
Create Date: 2026-04-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cache of per-user per-template provisioned agents
    op.create_table(
        "user_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_slug", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="anthropic"),
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "agent_slug", name="uq_user_agents_user_slug"),
    )
    op.create_index("ix_user_agents_user_id", "user_agents", ["user_id"])

    op.execute("alter table public.user_agents enable row level security;")
    op.execute("""
        create policy "Users access their own agents"
            on public.user_agents
            for all
            using (user_id = auth.uid())
            with check (user_id = auth.uid());
    """)

    # Which template (slug) this session uses — for sidebar filtering
    op.add_column("sessions", sa.Column("agent_slug", sa.Text(), nullable=True))

    # users.agent_id and users.provider were for single-agent-per-user flow
    op.drop_column("users", "agent_id")
    op.drop_column("users", "provider")


def downgrade() -> None:
    op.add_column("users", sa.Column("provider", sa.Text(), nullable=False, server_default="anthropic"))
    op.add_column("users", sa.Column("agent_id", sa.Text(), nullable=True))
    op.drop_column("sessions", "agent_slug")
    op.execute('drop policy if exists "Users access their own agents" on public.user_agents;')
    op.drop_index("ix_user_agents_user_id", table_name="user_agents")
    op.drop_table("user_agents")

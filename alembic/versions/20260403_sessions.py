"""Add sessions + session_events tables for conversation history.

Revision ID: 20260403a001
Revises: 20260402a001
Create Date: 2026-04-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260403a001"
down_revision = "20260402a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("end_user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_sessions_agent", "sessions", ["agent_id"])
    op.create_index("idx_sessions_user", "sessions", ["user_id"])
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")

    op.create_table(
        "session_events",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_title", sa.Text(), nullable=True),
        sa.Column("event_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_session_events_session", "session_events", ["session_id", "sequence_no"])
    op.execute("ALTER TABLE session_events ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE session_events DISABLE ROW LEVEL SECURITY")
    op.drop_table("session_events")
    op.execute("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY")
    op.drop_table("sessions")

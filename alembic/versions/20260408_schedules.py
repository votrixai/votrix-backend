"""Add user_agent_schedules table for cron-driven agent workflows.

Revision ID: 20260408a001
Revises: 20260405a001
Create Date: 2026-04-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260408a001"
down_revision = "20260405a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_agent_schedules",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("end_user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("cron_expr", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Scheduler polling query: WHERE enabled = true AND next_run_at <= NOW()
    op.create_index("idx_schedules_next_run", "user_agent_schedules", ["enabled", "next_run_at"])
    op.execute("ALTER TABLE user_agent_schedules ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE user_agent_schedules DISABLE ROW LEVEL SECURITY")
    op.drop_table("user_agent_schedules")

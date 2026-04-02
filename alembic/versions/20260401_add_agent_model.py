"""Add model column to blueprint_agents.

Revision ID: 20260401a001
Revises: 20260331a001
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260401a001"
down_revision = "20260331a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blueprint_agents",
        sa.Column("model", sa.Text(), nullable=False, server_default="claude-sonnet-4-6"),
    )


def downgrade() -> None:
    op.drop_column("blueprint_agents", "model")

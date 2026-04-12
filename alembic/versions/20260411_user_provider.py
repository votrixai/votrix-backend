"""rename anthropic_agent_id to agent_id, add provider to users

Revision ID: 003
Revises: 002
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "anthropic_agent_id", new_column_name="agent_id")
    op.add_column(
        "users",
        sa.Column("provider", sa.Text(), nullable=False, server_default="anthropic"),
    )


def downgrade() -> None:
    op.drop_column("users", "provider")
    op.alter_column("users", "agent_id", new_column_name="anthropic_agent_id")

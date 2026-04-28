"""add user_agent_memory_stores table

Revision ID: 016
Revises: 015
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_agent_memory_stores",
        sa.Column("store_id", sa.Text(), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_slug", sa.Text(), nullable=False),
        sa.UniqueConstraint("user_id", "agent_slug", name="uq_memory_stores_user_slug"),
    )


def downgrade() -> None:
    op.drop_table("user_agent_memory_stores")

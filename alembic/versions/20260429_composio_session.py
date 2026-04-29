"""add composio_session_id to sessions

Revision ID: 019
Revises: 018
Create Date: 2026-04-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("composio_session_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "composio_session_id")

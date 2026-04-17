"""drop sessions.display_name

Revision ID: 011
Revises: 010
Create Date: 2026-04-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("sessions", "display_name")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
    )

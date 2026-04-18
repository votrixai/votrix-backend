"""add provider_session_title to sessions

Revision ID: 010
Revises: 009
Create Date: 2026-04-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("provider_session_title", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "provider_session_title")

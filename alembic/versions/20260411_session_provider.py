"""rename anthropic_session_id to session_id, add provider and agent_id to sessions

Revision ID: 005
Revises: 004
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("sessions", "anthropic_session_id", new_column_name="session_id")
    op.add_column("sessions", sa.Column("provider", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("agent_id", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "agent_id")
    op.drop_column("sessions", "provider")
    op.alter_column("sessions", "session_id", new_column_name="anthropic_session_id")

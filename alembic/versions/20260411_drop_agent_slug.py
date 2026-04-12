"""drop agent_slug from users and sessions

Revision ID: 006
Revises: 005
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "agent_slug")
    op.drop_column("sessions", "agent_slug")


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column("sessions", sa.Column("agent_slug", sa.Text(), nullable=False, server_default=""))
    op.add_column("users", sa.Column("agent_slug", sa.Text(), nullable=False, server_default=""))

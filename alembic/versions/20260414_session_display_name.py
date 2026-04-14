"""add display_name to sessions

Revision ID: 20260414_session_display_name
Revises: 20260411_session_provider
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("display_name", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("sessions", "display_name")

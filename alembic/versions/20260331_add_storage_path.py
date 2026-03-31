"""Add storage_path column and make content nullable.

Revision ID: 20260331a001
Revises:
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "20260331a001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # blueprint_files: make content nullable, add storage_path
    op.alter_column("blueprint_files", "content", existing_type=sa.Text(), nullable=True)
    op.add_column("blueprint_files", sa.Column("storage_path", sa.Text(), nullable=True))

    # user_files: make content nullable, add storage_path
    op.alter_column("user_files", "content", existing_type=sa.Text(), nullable=True)
    op.add_column("user_files", sa.Column("storage_path", sa.Text(), nullable=True))


def downgrade() -> None:
    # user_files: drop storage_path, make content non-nullable
    op.drop_column("user_files", "storage_path")
    op.execute("UPDATE user_files SET content = '' WHERE content IS NULL")
    op.alter_column("user_files", "content", existing_type=sa.Text(), nullable=False)

    # blueprint_files: drop storage_path, make content non-nullable
    op.drop_column("blueprint_files", "storage_path")
    op.execute("UPDATE blueprint_files SET content = '' WHERE content IS NULL")
    op.alter_column("blueprint_files", "content", existing_type=sa.Text(), nullable=False)

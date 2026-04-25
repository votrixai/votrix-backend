"""drop vault_id from users

Revision ID: 015
Revises: 014
Create Date: 2026-04-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "vault_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("vault_id", sa.Text(), nullable=True))

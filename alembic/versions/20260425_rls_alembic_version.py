"""enable RLS on alembic_version and schedules

Revision ID: 016
Revises: 015
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "Users can only access their own schedules"
            ON public.schedules
            FOR ALL
            USING (user_id = auth.uid());
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "Users can only access their own schedules" ON public.schedules;')
    op.execute("ALTER TABLE public.schedules DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY;")

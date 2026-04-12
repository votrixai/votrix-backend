"""add RLS policies and auth trigger for users

Revision ID: 004
Revises: 003
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Auto-populate users on Supabase auth signup
    op.execute("""
        create or replace function public.handle_new_user()
        returns trigger as $$
        begin
            insert into public.users (id)
            values (new.id);
            return new;
        end;
        $$ language plpgsql security definer;
    """)

    op.execute("""
        create trigger on_auth_user_created
            after insert on auth.users
            for each row execute function public.handle_new_user();
    """)

    # Enable RLS and add policy on users
    op.execute("alter table public.users enable row level security;")

    op.execute("""
        create policy "Users can only access their own record"
            on public.users
            for all
            using (id = auth.uid());
    """)


def downgrade() -> None:
    op.execute("drop policy if exists \"Users can only access their own record\" on public.users;")
    op.execute("alter table public.users disable row level security;")
    op.execute("drop trigger if exists on_auth_user_created on auth.users;")
    op.execute("drop function if exists public.handle_new_user();")

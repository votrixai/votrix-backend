"""auth hardening: FK to auth.users, RLS on sessions/session_events, search_path on handle_new_user

Revision ID: 008
Revises: 007
Create Date: 2026-04-14
"""
from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. FK public.users.id -> auth.users.id (cascade delete on signup removal)
    op.execute("""
        alter table public.users
        add constraint users_id_fkey
        foreign key (id) references auth.users(id) on delete cascade;
    """)

    # 2. Harden handle_new_user: pin search_path (prevents search_path hijacking)
    op.execute("""
        create or replace function public.handle_new_user()
        returns trigger
        language plpgsql
        security definer
        set search_path = public
        as $$
        begin
            insert into public.users (id)
            values (new.id);
            return new;
        end;
        $$;
    """)

    # 3. RLS on sessions
    op.execute("alter table public.sessions enable row level security;")
    op.execute("""
        create policy "Users can access their own sessions"
            on public.sessions
            for all
            using (user_id = auth.uid())
            with check (user_id = auth.uid());
    """)

    # 4. RLS on session_events (scoped via parent session ownership)
    op.execute("alter table public.session_events enable row level security;")
    op.execute("""
        create policy "Users can access events for their own sessions"
            on public.session_events
            for all
            using (
                exists (
                    select 1 from public.sessions s
                    where s.id = session_events.session_id
                      and s.user_id = auth.uid()
                )
            )
            with check (
                exists (
                    select 1 from public.sessions s
                    where s.id = session_events.session_id
                      and s.user_id = auth.uid()
                )
            );
    """)


def downgrade() -> None:
    op.execute('drop policy if exists "Users can access events for their own sessions" on public.session_events;')
    op.execute("alter table public.session_events disable row level security;")

    op.execute('drop policy if exists "Users can access their own sessions" on public.sessions;')
    op.execute("alter table public.sessions disable row level security;")

    # Revert handle_new_user to prior form (no search_path)
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

    op.execute("alter table public.users drop constraint if exists users_id_fkey;")

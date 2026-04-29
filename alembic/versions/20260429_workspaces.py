"""add workspaces and workspace_members tables, backfill existing users

Revision ID: 017
Revises: 016
Create Date: 2026-04-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "017"
down_revision: Union[str, None] = "016b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create tables ---
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "workspace_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.Text(), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"),
    )

    # --- Backfill: create a workspace + membership for every existing user ---
    op.execute("""
        DO $$
        DECLARE
            r RECORD;
            ws_id uuid;
        BEGIN
            FOR r IN SELECT id, display_name, created_at FROM users LOOP
                ws_id := gen_random_uuid();
                INSERT INTO workspaces (id, display_name, created_at, updated_at)
                VALUES (ws_id, r.display_name, r.created_at, now());
                INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at, updated_at)
                VALUES (gen_random_uuid(), ws_id, r.id, 'owner', now(), now());
            END LOOP;
        END $$;
    """)

    # --- Update trigger: new users get a workspace automatically ---
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger AS $$
        DECLARE
            ws_id uuid := gen_random_uuid();
        BEGIN
            INSERT INTO public.users (id) VALUES (new.id);
            INSERT INTO public.workspaces (id) VALUES (ws_id);
            INSERT INTO public.workspace_members (id, workspace_id, user_id, role)
                VALUES (gen_random_uuid(), ws_id, new.id, 'owner');
            RETURN new;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    # --- RLS ---
    op.execute("ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "Members can access their workspaces"
            ON public.workspaces
            FOR ALL
            USING (id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = auth.uid()));
    """)

    op.execute("ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "Users can access their own memberships"
            ON public.workspace_members
            FOR ALL
            USING (user_id = auth.uid());
    """)


def downgrade() -> None:
    # Restore original trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger AS $$
        BEGIN
            INSERT INTO public.users (id) VALUES (new.id);
            RETURN new;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)

    op.execute('DROP POLICY IF EXISTS "Users can access their own memberships" ON public.workspace_members;')
    op.execute("ALTER TABLE public.workspace_members DISABLE ROW LEVEL SECURITY;")
    op.execute('DROP POLICY IF EXISTS "Members can access their workspaces" ON public.workspaces;')
    op.execute("ALTER TABLE public.workspaces DISABLE ROW LEVEL SECURITY;")

    op.drop_table("workspace_members")
    op.drop_table("workspaces")

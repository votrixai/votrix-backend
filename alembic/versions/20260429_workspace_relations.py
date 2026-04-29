"""rebuild sessions, events, schedules, agents, memory stores for workspace-scoped model

Revision ID: 018
Revises: 017
Create Date: 2026-04-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Drop RLS policies on old tables ---
    op.execute('DROP POLICY IF EXISTS "Users can access their own sessions" ON public.sessions;')
    op.execute('DROP POLICY IF EXISTS "Users can access events for their own sessions" ON public.session_events;')
    op.execute('DROP POLICY IF EXISTS "Users can only access their own schedules" ON public.schedules;')

    # --- Drop old tables (order matters for FKs) ---
    op.drop_table("user_agent_memory_stores")
    op.drop_table("session_events")
    op.drop_table("schedules")
    op.drop_table("sessions")
    op.drop_table("user_agents")

    # --- Create agent_blueprints ---
    op.create_table(
        "agent_blueprints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_agent_id", sa.Text(), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="anthropic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Create agent_employees ---
    op.create_table(
        "agent_employees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_blueprint_id", UUID(as_uuid=True), sa.ForeignKey("agent_blueprints.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("workspace_id", "agent_blueprint_id", name="uq_agent_employees_workspace_id_agent_blueprint_id"),
    )

    # --- Create sessions (UUID PK, workspace-scoped) ---
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_session_id", sa.Text(), unique=True, nullable=False, index=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("agent_blueprint_id", UUID(as_uuid=True), sa.ForeignKey("agent_blueprints.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Create session_events ---
    op.create_table(
        "session_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Index("ix_session_events_session_id_event_index", "session_id", "event_index"),
    )

    # --- Create schedules (standalone) ---
    op.create_table(
        "schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cron_expression", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Create agent_employee_memory_stores ---
    op.create_table(
        "agent_employee_memory_stores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider_memory_store_id", sa.Text(), unique=True, nullable=False, index=True),
        sa.Column("agent_employee_id", UUID(as_uuid=True), sa.ForeignKey("agent_employees.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- RLS on new tables ---
    _workspace_rls("sessions", "workspace_id")
    _workspace_rls("session_events", via_session=True)
    _workspace_rls("agent_blueprints", public_read=True)
    _workspace_rls("agent_employees", "workspace_id")
    _workspace_rls("agent_employee_memory_stores", via_agent_employee=True)

    op.execute("ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "Authenticated users can access schedules"
            ON public.schedules
            FOR ALL
            USING (true);
    """)


def _workspace_rls(table: str, ws_col: str | None = None, *, via_session: bool = False, via_agent_employee: bool = False, public_read: bool = False) -> None:
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

    if public_read:
        op.execute(f"""
            CREATE POLICY "Authenticated users can access {table}"
                ON public.{table}
                FOR ALL
                USING (true);
        """)
    elif via_session:
        op.execute(f"""
            CREATE POLICY "Workspace members can access {table}"
                ON public.{table}
                FOR ALL
                USING (session_id IN (
                    SELECT s.id FROM public.sessions s
                    JOIN public.workspace_members wm ON wm.workspace_id = s.workspace_id
                    WHERE wm.user_id = auth.uid()
                ));
        """)
    elif via_agent_employee:
        op.execute(f"""
            CREATE POLICY "Workspace members can access {table}"
                ON public.{table}
                FOR ALL
                USING (agent_employee_id IN (
                    SELECT ae.id FROM public.agent_employees ae
                    JOIN public.workspace_members wm ON wm.workspace_id = ae.workspace_id
                    WHERE wm.user_id = auth.uid()
                ));
        """)
    elif ws_col:
        op.execute(f"""
            CREATE POLICY "Workspace members can access {table}"
                ON public.{table}
                FOR ALL
                USING ({ws_col} IN (
                    SELECT workspace_id FROM public.workspace_members WHERE user_id = auth.uid()
                ));
        """)


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for workspace-scoped model rebuild")

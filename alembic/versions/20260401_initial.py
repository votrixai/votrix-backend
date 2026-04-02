"""Initial migration: storage_path, nullable content, org integrations,
agent integration catalog tables, drop blueprint_agents.integrations JSONB.

Revision ID: 20260401a001
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260401a001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- storage_path + nullable content --
    op.alter_column("blueprint_files", "content", existing_type=sa.Text(), nullable=True)
    op.add_column("blueprint_files", sa.Column("storage_path", sa.Text(), nullable=True))
    op.alter_column("user_files", "content", existing_type=sa.Text(), nullable=True)
    op.add_column("user_files", sa.Column("storage_path", sa.Text(), nullable=True))

    # -- org integrations column --
    op.add_column("orgs", sa.Column("integrations", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"))

    # -- agent_integrations (global catalog) --
    op.create_table(
        "agent_integrations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider_slug", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider_config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # -- agent_integration_tools --
    op.create_table(
        "agent_integration_tools",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent_integration_id", UUID(as_uuid=True), sa.ForeignKey("agent_integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("agent_integration_id", "slug", name="uq_integration_tool_slug"),
    )

    # -- blueprint_agent_integrations (agent ↔ integration link) --
    op.create_table(
        "blueprint_agent_integrations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("blueprint_agent_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_integration_id", UUID(as_uuid=True), sa.ForeignKey("agent_integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("blueprint_agent_id", "agent_integration_id", name="uq_blueprint_agent_integration"),
    )

    # -- blueprint_agent_integration_tools (enabled tools per link) --
    op.create_table(
        "blueprint_agent_integration_tools",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("blueprint_agent_integration_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agent_integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_integration_tool_id", UUID(as_uuid=True), sa.ForeignKey("agent_integration_tools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("blueprint_agent_integration_id", "agent_integration_tool_id", name="uq_blueprint_agent_integration_tool"),
    )

    # -- drop old JSONB column, add soft delete --
    op.drop_column("blueprint_agents", "integrations")
    op.add_column("blueprint_agents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # -- rename end_user_agent_links → end_user_agents --
    op.rename_table("end_user_agent_links", "end_user_agents")

    # -- RLS --
    op.execute("ALTER TABLE agent_integrations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_integration_tools ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE blueprint_agent_integrations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE blueprint_agent_integration_tools ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # RLS
    op.execute("ALTER TABLE blueprint_agent_integration_tools DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE blueprint_agent_integrations DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_integration_tools DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_integrations DISABLE ROW LEVEL SECURITY")

    # Drop soft delete, re-add JSONB column
    op.drop_column("blueprint_agents", "deleted_at")
    op.add_column("blueprint_agents", sa.Column("integrations", JSONB(), nullable=False, server_default="[]"))

    # Drop new tables
    op.drop_table("blueprint_agent_integration_tools")
    op.drop_table("blueprint_agent_integrations")
    op.drop_table("agent_integration_tools")
    op.drop_table("agent_integrations")

    # Rename back
    op.rename_table("end_user_agents", "end_user_agent_links")

    # Drop org integrations
    op.drop_column("orgs", "integrations")

    # Revert storage_path + nullable content
    op.drop_column("user_files", "storage_path")
    op.execute("UPDATE user_files SET content = '' WHERE content IS NULL")
    op.alter_column("user_files", "content", existing_type=sa.Text(), nullable=False)
    op.drop_column("blueprint_files", "storage_path")
    op.execute("UPDATE blueprint_files SET content = '' WHERE content IS NULL")
    op.alter_column("blueprint_files", "content", existing_type=sa.Text(), nullable=False)

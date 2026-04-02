"""Refactor integrations: replace blueprint_agent_tools + integrations JSONB
with a new blueprint_agent_integrations table.

Changes:
- Drop blueprint_agent_tools (old tool mapping table)
- Drop blueprint_agents.integrations JSONB column
- Create blueprint_agent_integrations (agent ↔ integration with inline slug/tools)

Revision ID: 20260402a001
Revises: 20260401a001
Create Date: 2026-04-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260402a001"
down_revision = "20260401a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old tool mapping table
    op.drop_table("blueprint_agent_tools")

    # Drop old JSONB integrations column on blueprint_agents
    op.drop_column("blueprint_agents", "integrations")

    # Create new blueprint_agent_integrations table
    op.create_table(
        "blueprint_agent_integrations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("blueprint_agent_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("integration_slug", sa.Text(), nullable=False),
        sa.Column("deferred", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enabled_mcp_tool_slugs", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("blueprint_agent_id", "integration_slug", name="uq_blueprint_agent_integration_slug"),
    )
    op.execute("ALTER TABLE blueprint_agent_integrations ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE blueprint_agent_integrations DISABLE ROW LEVEL SECURITY")
    op.drop_table("blueprint_agent_integrations")

    op.add_column(
        "blueprint_agents",
        sa.Column("integrations", JSONB(), nullable=False, server_default="[]"),
    )

    op.create_table(
        "blueprint_agent_tools",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("blueprint_agent_id", UUID(as_uuid=True), sa.ForeignKey("blueprint_agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", sa.Text(), nullable=False),
        sa.Column("integration_slug", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("blueprint_agent_id", "tool_id", name="uq_blueprint_agent_tool"),
    )

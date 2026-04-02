"""Baseline migration: represents DB state created from initial SQL scripts.

This migration is a no-op. The schema (orgs, blueprint_agents, blueprint_files,
user_files, end_user_accounts, end_user_agents, blueprint_agent_tools) was
created manually and alembic is being introduced at this point.

Revision ID: 20260401a001
Revises:
Create Date: 2026-04-01
"""

revision = "20260401a001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

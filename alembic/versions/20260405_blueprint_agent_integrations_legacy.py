"""Align legacy blueprint_agent_integrations (Supabase 001_initial) with ORM.

Adds integration_slug, deferred, enabled_tool_slugs; migrates from agent_integration_id
and blueprint_agent_integration_tools; drops old columns.

Revision ID: 20260405a001
Revises: 20260403a001
Create Date: 2026-04-05
"""

from alembic import op
from sqlalchemy import text

revision = "20260405a001"
down_revision = "20260403a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text("""
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name = 'blueprint_agent_integrations'
  ) THEN
    RAISE EXCEPTION 'public.blueprint_agent_integrations is missing; apply 20260402a001 (or create the table) before 20260405a001';
  END IF;

  -- Already matches ORM (20260402 success or prior 20260405 run)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'blueprint_agent_integrations'
      AND column_name = 'enabled_tool_slugs'
  ) THEN
    RETURN;
  END IF;

  -- 20260402-style row but one column missing (partial / hand-edited DB)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'blueprint_agent_integrations'
      AND column_name = 'integration_slug'
  ) THEN
    ALTER TABLE blueprint_agent_integrations
      ADD COLUMN IF NOT EXISTS deferred boolean NOT NULL DEFAULT false;
    ALTER TABLE blueprint_agent_integrations
      ADD COLUMN IF NOT EXISTS enabled_tool_slugs text[] NOT NULL DEFAULT '{}';
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint c
      JOIN pg_class t ON c.conrelid = t.oid
      JOIN pg_namespace n ON t.relnamespace = n.oid
      WHERE n.nspname = 'public'
        AND t.relname = 'blueprint_agent_integrations'
        AND c.conname = 'uq_blueprint_agent_integration_slug'
    ) THEN
      ALTER TABLE blueprint_agent_integrations
        ADD CONSTRAINT uq_blueprint_agent_integration_slug
        UNIQUE (blueprint_agent_id, integration_slug);
    END IF;
    RETURN;
  END IF;

  -- Legacy Supabase 001_initial shape
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'blueprint_agent_integrations'
      AND column_name = 'agent_integration_id'
  ) THEN
    RAISE EXCEPTION
      'public.blueprint_agent_integrations has no enabled_tool_slugs, no integration_slug, and no agent_integration_id — table does not match legacy (001_initial) or new (20260402) shape; inspect columns and fix manually';
  END IF;

  ALTER TABLE blueprint_agent_integrations ADD COLUMN integration_slug text;
  ALTER TABLE blueprint_agent_integrations ADD COLUMN deferred boolean NOT NULL DEFAULT false;
  ALTER TABLE blueprint_agent_integrations ADD COLUMN enabled_tool_slugs text[] NOT NULL DEFAULT '{}';

  UPDATE blueprint_agent_integrations bai
  SET integration_slug = ai.slug
  FROM agent_integrations ai
  WHERE bai.agent_integration_id = ai.id;

  DELETE FROM blueprint_agent_integrations WHERE integration_slug IS NULL;

  UPDATE blueprint_agent_integrations bai
  SET enabled_tool_slugs = COALESCE(
    (SELECT array_agg(ait.slug ORDER BY ait.slug)
     FROM blueprint_agent_integration_tools bait
     JOIN agent_integration_tools ait ON ait.id = bait.agent_integration_tool_id
     WHERE bait.blueprint_agent_integration_id = bai.id),
    '{}'::text[]
  );

  ALTER TABLE blueprint_agent_integrations ALTER COLUMN integration_slug SET NOT NULL;

  ALTER TABLE blueprint_agent_integrations
    DROP CONSTRAINT IF EXISTS blueprint_agent_integrations_blueprint_agent_id_agent_integration_id_key;
  ALTER TABLE blueprint_agent_integrations
    DROP CONSTRAINT IF EXISTS blueprint_agent_integrations_agent_integration_id_fkey;

  ALTER TABLE blueprint_agent_integrations DROP COLUMN agent_integration_id;

  DROP TABLE IF EXISTS blueprint_agent_integration_tools;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint c
    JOIN pg_class t ON c.conrelid = t.oid
    JOIN pg_namespace n ON t.relnamespace = n.oid
    WHERE n.nspname = 'public'
      AND t.relname = 'blueprint_agent_integrations'
      AND c.conname = 'uq_blueprint_agent_integration_slug'
  ) THEN
    ALTER TABLE blueprint_agent_integrations
      ADD CONSTRAINT uq_blueprint_agent_integration_slug
      UNIQUE (blueprint_agent_id, integration_slug);
  END IF;
END $$;
""")
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for legacy integration reshape")

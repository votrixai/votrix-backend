-- ============================================================
-- 002_agent_integrations_jsonb.sql
-- Move per-agent integrations from a separate table into a
-- JSONB column on blueprint_agents.
-- ============================================================

-- 1. Add integrations JSONB column to blueprint_agents
alter table blueprint_agents
  add column if not exists integrations jsonb not null default '[]';

-- 2. Migrate existing rows: aggregate agent_integrations into JSONB
--    Existing rows only have integration_slug, so deferred=false and
--    enabled_tool_ids=[] are safe defaults.
update blueprint_agents ba
set integrations = (
  select coalesce(
    json_agg(
      json_build_object(
        'integration_id',    ai.integration_slug,
        'deferred',          false,
        'enabled_tool_ids',  '[]'::json
      )
    ),
    '[]'::json
  )
  from agent_integrations ai
  where ai.blueprint_agent_id = ba.id
);

-- 3. Drop the old table
drop table if exists agent_integrations;

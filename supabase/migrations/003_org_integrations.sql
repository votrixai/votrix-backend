-- ============================================================
-- 003_org_integrations.sql
-- Add integrations TEXT[] column to orgs for per-org activated
-- integration catalog (stores slugs, e.g. 'gmail', 'notion').
-- platform integration is always available and not stored here.
-- ============================================================

alter table orgs
  add column if not exists integrations text[] not null default '{}';

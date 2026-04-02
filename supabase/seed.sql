-- Seed data: Votrix Developers org + Marketing Agent
-- Run via: psql $DATABASE_URL -f supabase/seed.sql
-- Or automatically on: supabase db reset

INSERT INTO orgs (id, display_name, timezone, metadata, integrations)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'Votrix Developers',
    'America/Los_Angeles',
    '{}',
    '{}'
);


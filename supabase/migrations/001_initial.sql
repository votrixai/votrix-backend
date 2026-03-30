-- ============================================================
-- 001_initial.sql — votrix-backend schema
-- ============================================================

create extension if not exists "pgcrypto";

-- ============================================================
-- 1. orgs
-- ============================================================
create table orgs (
  id           uuid primary key default gen_random_uuid(),
  display_name text not null default '',
  timezone     text not null default 'UTC',
  metadata     jsonb not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 2. blueprint_agents
-- ============================================================
create table blueprint_agents (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  slug         text not null default 'default',
  name         text not null default '',

  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (org_id, slug)
);

-- ============================================================
-- 3. agent_integrations
-- ============================================================
create table agent_integrations (
  id                  uuid primary key default gen_random_uuid(),
  blueprint_agent_id  uuid not null references blueprint_agents(id) on delete cascade,
  integration_id      text not null,
  enabled_tool_ids    text[] not null default '{}',
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (blueprint_agent_id, integration_id)
);

create index idx_agent_integrations_agent
  on agent_integrations (blueprint_agent_id);

-- ============================================================
-- 4. blueprint_files — admin/member-owned base files
-- ============================================================
create type node_type as enum ('file', 'directory');

create table blueprint_files (
  id                  uuid primary key default gen_random_uuid(),
  blueprint_agent_id  uuid not null references blueprint_agents(id) on delete cascade,

  -- core identity
  path         text not null,
  name         text not null,
  type         node_type not null default 'file',

  -- content
  content      text not null default '',
  mime_type    text not null default 'text/markdown',
  size_bytes   int not null default 0,

  -- classification: 'skill' | 'skill_asset' | 'prompt' | 'file'
  file_class   text not null default 'file',

  -- derived (set by app on write)
  parent       text not null default '/',
  ext          text not null default '',
  depth        int not null default 0,

  -- ownership / audit
  created_by   text not null default 'system',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (blueprint_agent_id, path)
);

-- ls: list children of a directory
create index idx_blueprint_ls
  on blueprint_files (blueprint_agent_id, parent);

-- glob: prefix scan on path
create index idx_blueprint_glob
  on blueprint_files (blueprint_agent_id, path text_pattern_ops);

-- filter by file_class
create index idx_blueprint_class
  on blueprint_files (blueprint_agent_id, file_class);

-- grep: full-text search
create index idx_blueprint_fts
  on blueprint_files using gin (to_tsvector('english', content));

-- ============================================================
-- 5. user_files — end-user's own independent files
-- ============================================================
create table user_files (
  id                  uuid primary key default gen_random_uuid(),
  blueprint_agent_id  uuid not null references blueprint_agents(id) on delete cascade,
  end_user_id         text not null,

  -- core identity
  path         text not null,
  name         text not null,
  type         node_type not null default 'file',

  -- content
  content      text not null default '',
  mime_type    text not null default 'text/markdown',
  size_bytes   int not null default 0,

  -- classification: 'skill' | 'skill_asset' | 'prompt' | 'file'
  file_class   text not null default 'file',

  -- derived (set by app on write)
  parent       text not null default '/',
  ext          text not null default '',
  depth        int not null default 0,

  -- ownership / audit
  created_by   text not null default 'system',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (blueprint_agent_id, end_user_id, path)
);

-- find all files for a specific end user
create index idx_user_files_by_user
  on user_files (blueprint_agent_id, end_user_id);

-- ls: list children of a directory for an end user
create index idx_user_files_ls
  on user_files (blueprint_agent_id, end_user_id, parent);

-- glob: prefix scan on path
create index idx_user_files_glob
  on user_files (blueprint_agent_id, path text_pattern_ops);

-- ============================================================
-- 6. end_user_accounts — persistent end user data
-- ============================================================
create table end_user_accounts (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  end_user_id  text not null,
  display_name text not null default '',
  sandbox      boolean not null default false,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (org_id, end_user_id)
);

-- Row Level Security
-- ============================================================
alter table blueprint_agents     enable row level security;
alter table agent_integrations   enable row level security;
alter table blueprint_files      enable row level security;
alter table user_files           enable row level security;
alter table end_user_accounts    enable row level security;

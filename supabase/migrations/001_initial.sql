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
  integrations text[] not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 2. blueprint_agents
-- ============================================================
create table blueprint_agents (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  display_name text not null default '',
  deleted_at   timestamptz default null,

  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 3. agent_integrations (global catalog)
-- ============================================================
create table agent_integrations (
  id              uuid primary key default gen_random_uuid(),
  slug            text not null unique,
  display_name    text not null default '',
  description     text not null default '',
  provider_slug   text not null default '',
  provider_config jsonb not null default '{}',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ============================================================
-- 3a. agent_integration_tools (tools per integration)
-- ============================================================
create table agent_integration_tools (
  id                    uuid primary key default gen_random_uuid(),
  agent_integration_id  uuid not null references agent_integrations(id) on delete cascade,
  slug                  text not null,
  display_name          text not null default '',
  description           text not null default '',
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (agent_integration_id, slug)
);

-- ============================================================
-- 3b. blueprint_agent_integrations (agent ↔ integration link)
-- ============================================================
create table blueprint_agent_integrations (
  id                    uuid primary key default gen_random_uuid(),
  blueprint_agent_id    uuid not null references blueprint_agents(id) on delete cascade,
  agent_integration_id  uuid not null references agent_integrations(id) on delete cascade,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (blueprint_agent_id, agent_integration_id)
);

-- ============================================================
-- 3c. blueprint_agent_integration_tools (enabled tools per link)
-- ============================================================
create table blueprint_agent_integration_tools (
  id                              uuid primary key default gen_random_uuid(),
  blueprint_agent_integration_id  uuid not null references blueprint_agent_integrations(id) on delete cascade,
  agent_integration_tool_id       uuid not null references agent_integration_tools(id) on delete cascade,
  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),
  unique (blueprint_agent_integration_id, agent_integration_tool_id)
);

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
  content      text default '',
  storage_path text,
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
-- 5. end_user_accounts
-- ============================================================
create table end_user_accounts (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  display_name text not null default '',
  sandbox      boolean not null default false,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 6. user_files — end-user's own independent files
-- ============================================================
create table user_files (
  id                  uuid primary key default gen_random_uuid(),
  blueprint_agent_id  uuid not null references blueprint_agents(id) on delete cascade,
  user_account_id     uuid not null references end_user_accounts(id) on delete cascade,

  -- core identity
  path         text not null,
  name         text not null,
  type         node_type not null default 'file',

  -- content
  content      text default '',
  storage_path text,
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

  unique (blueprint_agent_id, user_account_id, path)
);

-- find all files for a specific user
create index idx_user_files_by_user
  on user_files (blueprint_agent_id, user_account_id);

-- ls: list children of a directory for a user
create index idx_user_files_ls
  on user_files (blueprint_agent_id, user_account_id, parent);

-- glob: prefix scan on path
create index idx_user_files_glob
  on user_files (blueprint_agent_id, path text_pattern_ops);

-- ============================================================
-- 7. end_user_agents — many-to-many
-- ============================================================
create table end_user_agents (
  id                    uuid primary key default gen_random_uuid(),
  end_user_account_id   uuid not null references end_user_accounts(id) on delete cascade,
  blueprint_agent_id    uuid not null references blueprint_agents(id) on delete cascade,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),

  unique (end_user_account_id, blueprint_agent_id)
);

create index idx_end_user_agents_account
  on end_user_agents (end_user_account_id);

create index idx_end_user_agents_agent
  on end_user_agents (blueprint_agent_id);

-- Row Level Security
-- ============================================================
alter table blueprint_agents                  enable row level security;
alter table agent_integrations                enable row level security;
alter table agent_integration_tools           enable row level security;
alter table blueprint_agent_integrations      enable row level security;
alter table blueprint_agent_integration_tools enable row level security;
alter table blueprint_files                   enable row level security;
alter table end_user_accounts                 enable row level security;
alter table user_files                        enable row level security;
alter table end_user_agents              enable row level security;

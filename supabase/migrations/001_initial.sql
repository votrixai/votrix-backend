-- ============================================================
-- 001_initial.sql — votrix-backend schema
-- ============================================================

create extension if not exists "pgcrypto";

-- ============================================================
-- 1. orgs
-- ============================================================
create table orgs (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null unique,
  display_name text not null default '',
  timezone     text not null default 'UTC',
  metadata     jsonb not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 2. agent_config
-- ============================================================
create table agent_config (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null references orgs(org_id) on delete cascade,
  agent_id     text not null default 'default',
  agent_name   text not null default '',

  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (org_id, agent_id),
  unique (agent_id)
);

-- ============================================================
-- 3. agent_tools_registry
-- ============================================================
create table agent_tools_registry (
  id               uuid primary key default gen_random_uuid(),
  agent_id         text not null references agent_config(agent_id) on delete cascade,
  integration_id   text not null,
  enabled_tool_ids text[] not null default '{}',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (agent_id, integration_id)
);

create index idx_agent_tools_registry_agent
  on agent_tools_registry (agent_id);

-- ============================================================
-- 4. blueprint_files — admin/member-owned base files
-- ============================================================
create type node_type as enum ('file', 'directory');

create table blueprint_files (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null,
  agent_id     text not null default 'default',

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

  foreign key (org_id, agent_id) references agent_config(org_id, agent_id) on delete cascade,
  unique (org_id, agent_id, path)
);

-- ls: list children of a directory
create index idx_blueprint_ls
  on blueprint_files (org_id, agent_id, parent);

-- glob: prefix scan on path
create index idx_blueprint_glob
  on blueprint_files (org_id, agent_id, path text_pattern_ops);

-- filter by file_class
create index idx_blueprint_class
  on blueprint_files (org_id, agent_id, file_class);

-- grep: full-text search
create index idx_blueprint_fts
  on blueprint_files using gin (to_tsvector('english', content));

-- ============================================================
-- 4. user_files — end-user's own independent files
-- ============================================================
create table user_files (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null,
  agent_id     text not null default 'default',
  end_user_id  text not null,

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

  foreign key (org_id, agent_id) references agent_config(org_id, agent_id) on delete cascade,
  unique (org_id, agent_id, end_user_id, path)
);

-- find all files for a specific end user
create index idx_user_files_by_user
  on user_files (org_id, agent_id, end_user_id);

-- ls: list children of a directory for an end user
create index idx_user_files_ls
  on user_files (org_id, agent_id, end_user_id, parent);

-- glob: prefix scan on path
create index idx_user_files_glob
  on user_files (org_id, agent_id, path text_pattern_ops);

-- ============================================================
-- 5. agent_version_log — changelog per version bump (disabled)
-- ============================================================
-- create table agent_version_log (
--   id               uuid primary key default gen_random_uuid(),
--   org_id           text not null,
--   agent_id         text not null,
--   version          int not null,
--   action           text not null,
--   path             text not null,
--   previous_content text,
--   created_at       timestamptz not null default now(),
--
--   unique (org_id, agent_id, version, path)
-- );

-- ============================================================
-- 6. agent_conflicts (disabled)
-- ============================================================
-- create table agent_conflicts (
--   id              uuid primary key default gen_random_uuid(),
--   org_id          text not null,
--   agent_id        text not null,
--   version         int not null,
--   end_user_id     text not null,
--   path            text not null,
--   conflict_type   text not null,
--   base_content    text,
--   end_user_content text,
--   new_content     text,
--   status          text not null default 'unresolved',
--   resolved_at     timestamptz,
--   created_at      timestamptz not null default now(),
--
--   unique (org_id, agent_id, end_user_id, path)
-- );

-- ============================================================
-- 7. end_user_account_info — persistent cross-session end user data
-- ============================================================
create table end_user_account_info (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null,
  agent_id     text not null default 'default',
  end_user_id  text not null,
  display_name text not null default '',
  notes        text not null default '',
  preferences  jsonb not null default '{}',
  metadata     jsonb not null default '{}',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (org_id, agent_id, end_user_id)
);

-- ============================================================
-- 8. sessions
-- ============================================================
create table sessions (
  id           uuid primary key default gen_random_uuid(),
  session_id   text not null unique,
  org_id       text not null,
  agent_id     text not null default 'default',
  end_user_id  text not null default '',
  channel_type text not null default 'web',
  labels       text[] not null default '{}',
  summary      text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 9. session_events — append-only log
-- ============================================================
create table session_events (
  id           uuid primary key default gen_random_uuid(),
  session_id   text not null references sessions(session_id) on delete cascade,
  seq          int not null,
  event_type   text not null,
  event_body   text not null default '',
  event_title  text,
  created_at   timestamptz not null default now(),

  unique (session_id, seq)
);

create index idx_session_events_lookup
  on session_events (session_id, seq);

-- Row Level Security
-- ============================================================
alter table agent_config         enable row level security;
alter table agent_tools_registry enable row level security;
alter table blueprint_files      enable row level security;
alter table user_files           enable row level security;
alter table end_user_account_info enable row level security;
alter table sessions             enable row level security;
alter table session_events       enable row level security;

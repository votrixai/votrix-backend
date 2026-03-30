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
-- 2. agents
-- ============================================================
create table agents (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null references orgs(org_id) on delete cascade,
  agent_id     text not null default 'default',

  -- prompt sections (flat columns)
  prompt_identity  text not null default '',
  prompt_soul      text not null default '',
  prompt_agents    text not null default '',
  prompt_user      text not null default '',
  prompt_tools     text not null default '',
  prompt_bootstrap text not null default '',

  -- versioning
  prompt_version   int not null default 1,

  -- registry (setup state)
  registry     jsonb not null default '{
    "bootstrap_complete": false,
    "modules": {},
    "connections": {},
    "timezone": "UTC"
  }',

  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  unique (org_id, agent_id)
);

-- ============================================================
-- 3. agent_files — virtual filesystem
-- ============================================================
create type node_type as enum ('file', 'directory');

create table agent_files (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null,
  agent_id     text not null default 'default',

  -- override layer: NULL = base (member-owned), set = end user override
  end_user_id  text,

  -- core identity
  path         text not null,
  name         text not null,
  type         node_type not null default 'file',

  -- permissions (admin/member is always rw implicitly)
  end_user_perm text not null default 'r',    -- 'none' | 'r' | 'rw'

  -- content
  content      text not null default '',
  mime_type    text not null default 'text/markdown',
  size_bytes   int not null default 0,

  -- classification: 'skill' | 'skill_asset' | 'prompt' | 'file'
  file_class   text not null default 'file',

  -- versioning: which base version this file/override was created against
  base_version int not null default 1,

  -- derived (set by app on write)
  parent       text not null default '/',
  ext          text not null default '',
  depth        int not null default 0,

  -- ownership / audit
  created_by   text not null default 'system',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),

  foreign key (org_id, agent_id) references agents(org_id, agent_id) on delete cascade,
  unique (org_id, agent_id, coalesce(end_user_id, ''), path)
);

-- ls: list children of a directory
create index idx_agent_files_ls
  on agent_files (org_id, agent_id, parent)
  where end_user_id is null;

-- ls for end user (base + overrides merged)
create index idx_agent_files_ls_user
  on agent_files (org_id, agent_id, parent, end_user_id);

-- glob: prefix scan on path
create index idx_agent_files_glob
  on agent_files (org_id, agent_id, path text_pattern_ops);

-- filter by file_class
create index idx_agent_files_class
  on agent_files (org_id, agent_id, file_class);

-- grep: full-text search
create index idx_agent_files_fts
  on agent_files using gin (to_tsvector('english', content));

-- find all overrides for a specific end user
create index idx_agent_files_end_user
  on agent_files (org_id, agent_id, end_user_id)
  where end_user_id is not null;

-- ============================================================
-- 4. agent_version_log — changelog per version bump (disabled)
-- ============================================================
-- create table agent_version_log (
--   id               uuid primary key default gen_random_uuid(),
--   org_id           text not null,
--   agent_id         text not null,
--   version          int not null,
--   action           text not null,         -- 'created' | 'updated' | 'deleted'
--   path             text not null,
--   previous_content text,                  -- snapshot before change (for diffing)
--   created_at       timestamptz not null default now(),
--
--   unique (org_id, agent_id, version, path)
-- );

-- ============================================================
-- 5. agent_conflicts (disabled)
-- ============================================================
-- create table agent_conflicts (
--   id              uuid primary key default gen_random_uuid(),
--   org_id          text not null,
--   agent_id        text not null,
--   version         int not null,
--   end_user_id     text not null,
--   path            text not null,
--   conflict_type   text not null,          -- 'both_modified' | 'base_deleted'
--   base_content    text,                   -- base at the end user's base_version
--   end_user_content text,                  -- end user's current override
--   new_content     text,                   -- admin's new version (null if deleted)
--   status          text not null default 'unresolved',  -- 'unresolved' | 'resolved_keep_admin' | 'resolved_keep_user' | 'resolved_merged'
--   resolved_at     timestamptz,
--   created_at      timestamptz not null default now(),
--
--   unique (org_id, agent_id, end_user_id, path)
-- );
--
-- create index idx_conflicts_unresolved
--   on agent_conflicts (org_id, agent_id, status)
--   where status = 'unresolved';
--
-- create index idx_conflicts_by_user
--   on agent_conflicts (org_id, agent_id, end_user_id);

-- ============================================================
-- 6. end_user_account_info — persistent cross-session end user data
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
-- 7. sessions
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
-- 8. session_events — append-only log
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

-- ============================================================
-- 9. guidelines — global singletons
-- ============================================================
create table guidelines (
  id            uuid primary key default gen_random_uuid(),
  guideline_id  text not null unique,
  content       text not null default '',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- ============================================================
-- Row Level Security
-- ============================================================
alter table agents              enable row level security;
alter table agent_files         enable row level security;
-- alter table agent_conflicts     enable row level security;
alter table end_user_account_info enable row level security;
alter table sessions            enable row level security;
alter table session_events      enable row level security;

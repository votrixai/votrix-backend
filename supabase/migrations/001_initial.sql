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
-- 3. agent_prompt_files — virtual filesystem
-- ============================================================
create type node_type as enum ('file', 'directory');
create type access_level as enum ('owner', 'org_read', 'org_write');

create table agent_prompt_files (
  id           uuid primary key default gen_random_uuid(),
  org_id       text not null,
  agent_id     text not null default 'default',

  -- core identity
  path         text not null,
  name         text not null,
  type         node_type not null default 'file',
  access_level access_level not null default 'org_read',

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

  foreign key (org_id, agent_id) references agents(org_id, agent_id) on delete cascade,
  unique (org_id, agent_id, path)
);

-- ls: list children of a directory
create index idx_prompt_files_ls
  on agent_prompt_files (org_id, agent_id, parent);

-- glob: prefix scan on path
create index idx_prompt_files_glob
  on agent_prompt_files (org_id, agent_id, path text_pattern_ops);

-- filter by file_class
create index idx_prompt_files_class
  on agent_prompt_files (org_id, agent_id, file_class);

-- grep: full-text search
create index idx_prompt_files_fts
  on agent_prompt_files using gin (to_tsvector('english', content));

-- ============================================================
-- 4. sessions
-- ============================================================
create table sessions (
  id           uuid primary key default gen_random_uuid(),
  session_id   text not null unique,
  org_id       text not null,
  agent_id     text not null default 'default',
  cust_id      text not null default '',
  channel_type text not null default 'web',
  labels       text[] not null default '{}',
  summary      text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ============================================================
-- 5. session_events — append-only log
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
-- 6. guidelines — global singletons
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
alter table agent_prompt_files  enable row level security;
alter table sessions            enable row level security;
alter table session_events      enable row level security;

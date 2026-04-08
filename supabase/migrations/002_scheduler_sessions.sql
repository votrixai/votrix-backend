-- ============================================================
-- 002_scheduler_sessions.sql
-- Adds: sessions, session_events, user_agent_schedules, user_notifications
-- ============================================================

-- ============================================================
-- 1. sessions
-- ============================================================
create table if not exists sessions (
  id         uuid primary key default gen_random_uuid(),
  agent_id   uuid not null references blueprint_agents(id) on delete cascade,
  user_id    uuid not null references end_user_accounts(id) on delete cascade,
  ended_at   timestamptz default null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_sessions_user_agent
  on sessions (user_id, agent_id);

-- ============================================================
-- 2. session_events
-- ============================================================
create table if not exists session_events (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references sessions(id) on delete cascade,
  sequence_no int  not null,
  event_type  text not null,
  event_title text,
  event_body  text not null default '',
  occurred_at timestamptz not null,
  created_at  timestamptz not null default now()
);

create index if not exists idx_session_events_session
  on session_events (session_id, sequence_no);

-- ============================================================
-- 3. user_agent_schedules
-- ============================================================
create table if not exists user_agent_schedules (
  id          uuid primary key default gen_random_uuid(),
  agent_id    uuid not null references blueprint_agents(id) on delete cascade,
  user_id     uuid not null references end_user_accounts(id) on delete cascade,
  message     text not null,
  cron_expr   text not null,
  description text not null default '',
  enabled     boolean not null default true,
  session_id  uuid references sessions(id) on delete set null,
  next_run_at timestamptz not null,
  last_run_at timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists idx_schedules_next_run
  on user_agent_schedules (next_run_at) where enabled = true;

create index if not exists idx_schedules_user
  on user_agent_schedules (user_id);

-- ============================================================
-- 4. user_notifications
-- ============================================================
create table if not exists user_notifications (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references end_user_accounts(id) on delete cascade,
  agent_id       uuid not null references blueprint_agents(id) on delete cascade,
  title          text not null,
  body           text not null default '',
  type           text not null,
  read           boolean not null default false,
  extra_metadata jsonb,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index if not exists idx_notifications_user
  on user_notifications (user_id, read, created_at desc);

-- RLS
alter table sessions              enable row level security;
alter table session_events        enable row level security;
alter table user_agent_schedules  enable row level security;
alter table user_notifications    enable row level security;

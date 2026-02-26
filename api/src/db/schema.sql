-- ====================================================================================
-- ULTRON SAAS - DATABASE SCHEMA V5 (IDEMPOTENT + SIGNUP WORKSPACE TRIGGER)
-- Safe to run in Supabase SQL Editor multiple times.
-- ====================================================================================

-- 1) Extensions
create extension if not exists "pgcrypto";

-- 2) Utility trigger function
create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 3) Enums (guarded)
do $$
begin
  if not exists (select 1 from pg_type where typname = 'user_role') then
    create type public.user_role as enum ('admin', 'editor', 'viewer');
  end if;
  if not exists (select 1 from pg_type where typname = 'platform_type') then
    create type public.platform_type as enum ('meli', 'magalu');
  end if;
  if not exists (select 1 from pg_type where typname = 'job_status') then
    create type public.job_status as enum ('pending', 'processing', 'completed', 'failed');
  end if;
  if not exists (select 1 from pg_type where typname = 'alert_status') then
    create type public.alert_status as enum ('active', 'triggered', 'resolved');
  end if;
  if not exists (select 1 from pg_type where typname = 'visual_analysis_level') then
    create type public.visual_analysis_level as enum ('none', 'lite', 'full');
  end if;
end
$$;

-- ====================================================================================
-- 4) Core multi-tenant tables
-- ====================================================================================

create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name varchar(255) not null,
  plan varchar(50) default 'free',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.workspace_members (
  workspace_id uuid references public.workspaces(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  role public.user_role default 'viewer',
  created_at timestamptz default now(),
  primary key (workspace_id, user_id)
);

create table if not exists public.integrations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  platform public.platform_type not null,
  access_token text,
  refresh_token text,
  expires_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (workspace_id, platform)
);

-- ====================================================================================
-- 5) Listings and history
-- ====================================================================================

create table if not exists public.listings_current (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  platform public.platform_type not null,
  external_id varchar(255) not null,
  raw_data jsonb not null default '{}',
  normalized_data jsonb not null default '{}',
  derived_data jsonb not null default '{}',
  last_synced_at timestamptz default now(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (workspace_id, platform, external_id)
);

create table if not exists public.listing_snapshots (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  listing_id uuid references public.listings_current(id) on delete cascade,
  captured_at timestamptz default now(),
  content_hash varchar(64) not null,
  raw_data jsonb not null,
  normalized_data jsonb not null,
  derived_data jsonb not null
);

-- ====================================================================================
-- 6) Rules, benchmarks, audits
-- ====================================================================================

create table if not exists public.marketplace_rulesets (
  id uuid primary key default gen_random_uuid(),
  platform public.platform_type not null,
  category_id varchar(255),
  rules jsonb not null default '{}',
  version int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (platform, category_id, version)
);

create table if not exists public.category_benchmarks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  platform public.platform_type not null,
  category_id varchar(255) not null,
  query_seed varchar(255),
  filters jsonb default '{}',
  benchmark_window_days int default 7,
  benchmark_data jsonb not null default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.audits (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  listing_id uuid references public.listings_current(id) on delete cascade,
  benchmark_id uuid references public.category_benchmarks(id) on delete set null,
  idempotency_key varchar(255) unique,
  scores jsonb not null default '{}',
  penalties jsonb not null default '[]',
  recommendations jsonb not null default '[]',
  created_at timestamptz default now()
);

-- ====================================================================================
-- 7) Jobs, alerts, logs
-- ====================================================================================

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  type varchar(50) not null,
  status public.job_status default 'pending',
  idempotency_key varchar(255) unique,
  result_summary jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.job_items (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  job_id uuid references public.jobs(id) on delete cascade,
  listing_id uuid references public.listings_current(id) on delete cascade,
  status public.job_status default 'pending',
  error_log text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.alert_rules (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  listing_id uuid null references public.listings_current(id) on delete cascade,
  name varchar(255) not null,
  condition jsonb not null,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.alert_events (
  id uuid primary key default gen_random_uuid(),
  rule_id uuid references public.alert_rules(id) on delete cascade,
  workspace_id uuid references public.workspaces(id) on delete cascade,
  listing_id uuid references public.listings_current(id) on delete cascade,
  status public.alert_status default 'triggered',
  event_data jsonb not null,
  triggered_at timestamptz default now(),
  resolved_at timestamptz
);

create table if not exists public.usage_logs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references public.workspaces(id) on delete cascade,
  feature varchar(100) not null,
  tokens_used int default 0,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- ====================================================================================
-- 8) updated_at triggers
-- ====================================================================================

drop trigger if exists update_workspaces_modtime on public.workspaces;
create trigger update_workspaces_modtime before update on public.workspaces
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_integrations_modtime on public.integrations;
create trigger update_integrations_modtime before update on public.integrations
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_listings_current_modtime on public.listings_current;
create trigger update_listings_current_modtime before update on public.listings_current
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_marketplace_rulesets_modtime on public.marketplace_rulesets;
create trigger update_marketplace_rulesets_modtime before update on public.marketplace_rulesets
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_category_benchmarks_modtime on public.category_benchmarks;
create trigger update_category_benchmarks_modtime before update on public.category_benchmarks
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_jobs_modtime on public.jobs;
create trigger update_jobs_modtime before update on public.jobs
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_job_items_modtime on public.job_items;
create trigger update_job_items_modtime before update on public.job_items
for each row execute procedure public.update_updated_at_column();

drop trigger if exists update_alert_rules_modtime on public.alert_rules;
create trigger update_alert_rules_modtime before update on public.alert_rules
for each row execute procedure public.update_updated_at_column();

-- ====================================================================================
-- 9) Performance indexes
-- ====================================================================================

create index if not exists idx_listings_current_ext_id on public.listings_current(workspace_id, platform, external_id);
create index if not exists idx_listing_snapshots_lookup on public.listing_snapshots(listing_id, captured_at desc);
create index if not exists idx_listing_snapshots_hash on public.listing_snapshots(content_hash);
create index if not exists idx_snapshots_ws_time on public.listing_snapshots(workspace_id, captured_at desc);
create index if not exists idx_benchmarks_lookup on public.category_benchmarks(platform, category_id, query_seed);
create index if not exists idx_rulesets_lookup on public.marketplace_rulesets(platform, category_id);
create index if not exists idx_jobs_workspace_status on public.jobs(workspace_id, status);
create index if not exists idx_audits_listing on public.audits(listing_id, created_at desc);
create index if not exists idx_alert_events_status on public.alert_events(workspace_id, status);

-- ====================================================================================
-- 10) RLS enable
-- ====================================================================================

alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.integrations enable row level security;
alter table public.listings_current enable row level security;
alter table public.listing_snapshots enable row level security;
alter table public.marketplace_rulesets enable row level security;
alter table public.category_benchmarks enable row level security;
alter table public.audits enable row level security;
alter table public.jobs enable row level security;
alter table public.job_items enable row level security;
alter table public.alert_rules enable row level security;
alter table public.alert_events enable row level security;
alter table public.usage_logs enable row level security;

-- ====================================================================================
-- 11) Workspace membership helper
-- ====================================================================================

create or replace function public.user_belongs_to_workspace(ws_id uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.workspace_members
    where workspace_id = ws_id
      and user_id = auth.uid()
  );
$$;

-- ====================================================================================
-- 12) RLS policies (drop+create to stay idempotent)
-- ====================================================================================

drop policy if exists "User can view their workspaces" on public.workspaces;
create policy "User can view their workspaces"
on public.workspaces for select
using (id in (select workspace_id from public.workspace_members where user_id = auth.uid()));

drop policy if exists "User can create workspace" on public.workspaces;
create policy "User can create workspace"
on public.workspaces for insert
with check (true);

drop policy if exists "User can view workspace members" on public.workspace_members;
create policy "User can view workspace members"
on public.workspace_members for select
using (workspace_id in (select workspace_id from public.workspace_members where user_id = auth.uid()));

drop policy if exists "User can join only self" on public.workspace_members;
create policy "User can join only self"
on public.workspace_members for insert
with check (user_id = auth.uid());

drop policy if exists "Workspace isolation for integrations" on public.integrations;
create policy "Workspace isolation for integrations"
on public.integrations for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for listings" on public.listings_current;
create policy "Workspace isolation for listings"
on public.listings_current for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for snapshots" on public.listing_snapshots;
create policy "Workspace isolation for snapshots"
on public.listing_snapshots for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for benchmarks" on public.category_benchmarks;
create policy "Workspace isolation for benchmarks"
on public.category_benchmarks for all
using (workspace_id is null or public.user_belongs_to_workspace(workspace_id))
with check (workspace_id is null or public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for audits" on public.audits;
create policy "Workspace isolation for audits"
on public.audits for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for jobs" on public.jobs;
create policy "Workspace isolation for jobs"
on public.jobs for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for job_items" on public.job_items;
create policy "Workspace isolation for job_items"
on public.job_items for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for alert_rules" on public.alert_rules;
create policy "Workspace isolation for alert_rules"
on public.alert_rules for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for alert_events" on public.alert_events;
create policy "Workspace isolation for alert_events"
on public.alert_events for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Workspace isolation for usage_logs" on public.usage_logs;
create policy "Workspace isolation for usage_logs"
on public.usage_logs for all
using (public.user_belongs_to_workspace(workspace_id))
with check (public.user_belongs_to_workspace(workspace_id));

drop policy if exists "Anyone can read rulesets" on public.marketplace_rulesets;
create policy "Anyone can read rulesets"
on public.marketplace_rulesets for select
using (true);

-- ====================================================================================
-- 13) Signup trigger (auto workspace + admin membership)
-- ====================================================================================

create or replace function public.handle_new_user_workspace()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  ws_id uuid;
  ws_name text;
begin
  ws_name := coalesce(
    new.raw_user_meta_data->>'workspace_name',
    split_part(coalesce(new.email, 'workspace'), '@', 1) || '-workspace'
  );

  insert into public.workspaces(name)
  values (ws_name)
  returning id into ws_id;

  insert into public.workspace_members(workspace_id, user_id, role)
  values (ws_id, new.id, 'admin');

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user_workspace();


-- 0001_initial.sql
-- Governance baseline migration (idempotent).

create table if not exists public.schema_migrations (
  version varchar(64) primary key,
  applied_at timestamptz not null default now()
);

create index if not exists idx_usage_logs_workspace_feature_created
  on public.usage_logs(workspace_id, feature, created_at desc);

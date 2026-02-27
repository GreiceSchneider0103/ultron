# Layout Migration Delivery

## api/src/db/schema.sql
`	sx
// INICIO SUBSTITUIR
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
using (user_id = auth.uid());

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

// FIM SUBSTITUIR
` 

## api/src/db/supabase_functions.sql
`	sx
// INICIO SUBSTITUIR
-- ====================================================================================
-- ULTRON SAAS - Supabase Functions/Triggers Patch
-- Run after schema.sql if you only need helper functions/policies/trigger refresh.
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

-- RLS hotfix: avoid recursive policy on workspace_members
drop policy if exists "User can view workspace members" on public.workspace_members;
create policy "User can view workspace members"
on public.workspace_members for select
using (user_id = auth.uid());

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user_workspace();

// FIM SUBSTITUIR
` 

## api/src/main.py
`	sx
// INICIO SUBSTITUIR
"""Ultron API main entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.src.auth import RequestContext, require_auth_context
from api.src.config import get_settings, settings
from api.src.functions.generator import generate_bullets, generate_description
from api.src.routers import ads, alerts, documents, images_v2, market_research, reports, seo
from api.src.routers.common import not_implemented
from api.src.routers.schemas import AnalyzeRequest, AuditListingRequest, OptimizeTitleRequest
from api.src.services.marketplace import get_connector, marketplace_alias

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ultron_startup", extra={"environment": settings.ENVIRONMENT})
    yield
    logger.info("ultron_shutdown")


app = FastAPI(
    title="Ultron API",
    description="Market/SEO/Ads Intelligence API for Mercado Livre and Magalu",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"name": "Ultron API", "version": app.version, "status": "running"}


@app.get("/health")
async def health(cfg=Depends(get_settings)):
    return {
        "status": "healthy",
        "environment": cfg.ENVIRONMENT,
        "ai_configured": cfg.check_ai_configured(),
        "ml_configured": cfg.check_ml_configured(),
    }


# Legacy routes compatibility
@app.post("/search")
async def legacy_search(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_research.market_search(
        marketplace=req.marketplace,
        query=req.keyword,
        category=None,
        limit=req.limit,
        offset=0,
        ctx=ctx,
    )


@app.post("/research")
async def legacy_research(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_research.market_analyze(req=req, ctx=ctx)


@app.post("/audit")
async def legacy_audit(req: AuditListingRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_analyze_listing(req=req, ctx=ctx)


@app.post("/suggest-title")
async def legacy_suggest_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_optimize_title(req=req, ctx=ctx)


@app.post("/validate-title")
async def legacy_validate_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    connector = get_connector(req.marketplace)
    return connector.validate_title(req.product_title)


@app.post("/generate/titles")
async def legacy_generate_titles(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_optimize_title(req=req, ctx=ctx)


@app.post("/generate/bullets")
async def legacy_generate_bullets(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    bullets = await generate_bullets(keyword=req.keyword, marketplace=marketplace_alias(req.marketplace), n_bullets=5)
    return {"bullets": bullets}


@app.post("/generate/description")
async def legacy_generate_description(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    description = await generate_description(keyword=req.keyword, marketplace=marketplace_alias(req.marketplace))
    return {"description": description}


@app.post("/create-listing")
async def legacy_create_listing(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("seo", "/create-listing")


@app.post("/compare")
async def legacy_compare(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("market-research", "/compare")


@app.post("/operations/sync")
async def operations_sync(
    skus: List[str],
    marketplace: str = "magalu",
    ctx: RequestContext = Depends(require_auth_context),
):
    return await market_research.operations_sync_impl(skus=skus, marketplace=marketplace, ctx=ctx)


app.include_router(market_research.router)
app.include_router(seo.router)
app.include_router(ads.router)
app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(alerts.router)
app.include_router(alerts.monitoring_router)
app.include_router(images_v2.router)

// FIM SUBSTITUIR
` 

## api/src/routers/images_v2.py
`	sx
// INICIO SUBSTITUIR
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from api.src.auth import RequestContext, require_auth_context

router = APIRouter(prefix="/api/v2/images", tags=["images-v2"])


@router.post("/analyze")
async def images_analyze_v2(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    image_urls: List[str] = req.get("image_urls", []) or []
    return {
        "workspace_id": ctx.workspace_id,
        "image_count": len(image_urls),
        "items": [{"url": url, "quality_score": 0.0, "objects": [], "todo": True} for url in image_urls],
        "note": "stub_v2_todo_implement_real_vision_pipeline",
    }


@router.post("/layout-audit")
async def images_layout_audit_v2(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return {
        "workspace_id": ctx.workspace_id,
        "image_url": req.get("image_url"),
        "layout_score": 0.0,
        "recommendations": [],
        "note": "stub_v2_todo_implement_real_layout_audit",
    }

// FIM SUBSTITUIR
` 

## api/src/routers/reports.py
`	sx
// INICIO SUBSTITUIR
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.reports.action_plan import generate_action_plan
from api.src.routers.common import not_implemented
from api.src.strategy.margin_strategy import decide_margin_strategy

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate")
async def reports_generate(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    strategy = decide_margin_strategy(
        cost=float(req.get("cost", 0)),
        min_margin_pct=float(req.get("min_margin_pct", 20)),
        shipping_cost=float(req.get("shipping_cost", 0)),
        commission_pct=float(req.get("commission_pct", 0)),
        lead_time_days=int(req.get("lead_time_days", 5)),
        target_price=float(req.get("target_price", 0)),
    )
    action_plan = generate_action_plan(findings=req.get("findings", {}), constraints={"strategy": strategy})
    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="report_generate",
        status="pending",
        result_summary={"request": req, "strategy": strategy, "action_plan": action_plan},
        supabase_jwt=ctx.token,
    )
    return {"workspace_id": ctx.workspace_id, "report_id": job_id, "status": "pending"}


@router.get("/{report_id}/status")
async def reports_status(report_id: str, ctx: RequestContext = Depends(require_auth_context)):
    job = repository.get_job(workspace_id=ctx.workspace_id, job_id=report_id, supabase_jwt=ctx.token)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found.")
    return {"workspace_id": ctx.workspace_id, "report_id": report_id, "status": job.get("status"), "result": job.get("result_summary")}


@router.get("/{report_id}/download")
async def reports_download(report_id: str, ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("reports", f"/api/reports/{report_id}/download")


@router.get("/v2/insights")
async def reports_insights_v2(ctx: RequestContext = Depends(require_auth_context)):
    client = repository._make_client(supabase_jwt=ctx.token)
    if not client:
        raise HTTPException(status_code=503, detail="Supabase unavailable")

    def _count(table: str, filters: Dict[str, Any]) -> int:
        query = client.table(table).select("id", count="exact", head=True)
        for key, value in filters.items():
            query = query.eq(key, value)
        resp = query.execute()
        return int(resp.count or 0)

    listings_count = _count("listings_current", {"workspace_id": ctx.workspace_id})
    alerts_count = _count("alert_events", {"workspace_id": ctx.workspace_id, "status": "triggered"})
    jobs_open = (
        client.table("jobs")
        .select("id", count="exact", head=True)
        .eq("workspace_id", ctx.workspace_id)
        .in_("status", ["pending", "processing"])
        .execute()
    )
    audits_count = _count("audits", {"workspace_id": ctx.workspace_id})

    return {
        "workspace_id": ctx.workspace_id,
        "metrics": [
            {"label": "Listings monitorados", "value": listings_count, "delta": 0, "tone": "neutral"},
            {"label": "Jobs em andamento", "value": int(jobs_open.count or 0), "delta": 0, "tone": "warning"},
            {"label": "Alertas ativos", "value": alerts_count, "delta": 0, "tone": "danger"},
            {"label": "Auditorias executadas", "value": audits_count, "delta": 0, "tone": "success"},
        ],
        "next_actions": [
            {"title": "Rodar nova pesquisa de mercado", "href": "/pesquisa"},
            {"title": "Executar auditoria em anuncio principal", "href": "/auditoria"},
            {"title": "Criar alerta de queda de preco", "href": "/monitoramento"},
            {"title": "Gerar relatorio de estrategia", "href": "/relatorios"},
        ],
    }

// FIM SUBSTITUIR
` 

## web/app/auditoria/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { AdAuditPage } from '@/components/pages/ad-audit-page'

export default async function AuditoriaPage() {
  return withProtectedShell((ctx) => <AdAuditPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/biblioteca/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { LibraryPage } from '@/components/pages/library-page'

export default async function BibliotecaPage() {
  return withProtectedShell((ctx) => <LibraryPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/configuracoes/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { SettingsPage } from '@/components/pages/settings-page'

export default async function ConfiguracoesPage() {
  return withProtectedShell((ctx) => <SettingsPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/dashboard/page.tsx
`	sx
// INICIO SUBSTITUIR
import { redirect } from 'next/navigation'

export default function DashboardLegacyRedirect() {
  redirect('/home')
}

// FIM SUBSTITUIR
` 

## web/app/gerar-anuncio/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { GenerateAdPage } from '@/components/pages/generate-ad-page'

export default async function GerarAnuncioPage() {
  return withProtectedShell((ctx) => <GenerateAdPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/globals.css
`	sx
// INICIO SUBSTITUIR
@import "tailwindcss";

:root {
  --font-size: 16px;
  --background: #f7f8fa;
  --foreground: #0f172a;
  --card: #ffffff;
  --card-foreground: #0f172a;
  --muted: #eef1f6;
  --muted-foreground: #64748b;
  --primary: #2563eb;
  --primary-foreground: #ffffff;
  --border: #e2e8f0;
  --success: #16a34a;
  --warning: #f59e0b;
  --danger: #ef4444;
  --radius: 0.75rem;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-inter);
  --font-mono: var(--font-geist-mono);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-border: var(--border);
  --radius-lg: var(--radius);
}

@layer base {
  * {
    @apply border-border;
  }

  html {
    font-size: var(--font-size);
  }

  body {
    @apply bg-background text-foreground font-sans antialiased;
  }
}

.ultron-scrollbar::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.ultron-scrollbar::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.ultron-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

// FIM SUBSTITUIR
` 

## web/app/home/page.tsx
`	sx
// INICIO SUBSTITUIR
import { DashboardHome } from '@/components/pages/dashboard-home'
import { withProtectedShell } from '@/components/layout/protected-app-page'

export default async function HomePage() {
  return withProtectedShell((ctx) => <DashboardHome workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/layout.tsx
`	sx
// INICIO SUBSTITUIR
import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Ultron SaaS",
  description: "Ultron Marketplace AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}

// FIM SUBSTITUIR
` 

## web/app/login/page.tsx
`	sx
// INICIO SUBSTITUIR
import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ message?: string | string[] }>
}) {
  const resolvedSearchParams = await searchParams
  const message = Array.isArray(resolvedSearchParams?.message)
    ? resolvedSearchParams.message[0]
    : resolvedSearchParams?.message

  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (session) redirect('/home')

  async function signIn(formData: FormData) {
    'use server'
    const email = String(formData.get('email') || '')
    const password = String(formData.get('password') || '')

    const supabase = await createClient()
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) redirect('/login?message=Erro ao fazer login')
    redirect('/home')
  }

  async function signUp(formData: FormData) {
    'use server'
    const email = String(formData.get('email') || '')
    const password = String(formData.get('password') || '')

    const supabase = await createClient()
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) redirect('/login?message=Erro ao criar conta')
    if (!data.session) {
      redirect('/login?message=Conta criada. Confirme seu e-mail para entrar')
    }
    redirect('/home')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-white p-8 shadow-md">
        <h1 className="text-center text-2xl font-bold text-gray-900">Ultron SaaS</h1>

        {message && (
          <p className="rounded-md bg-red-100 p-4 text-sm text-red-600">
            {message}
          </p>
        )}

        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              name="email"
              type="email"
              required
              className="mt-1 w-full rounded-md border px-3 py-2 text-black focus:border-blue-500 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Senha</label>
            <input
              name="password"
              type="password"
              required
              className="mt-1 w-full rounded-md border px-3 py-2 text-black focus:border-blue-500 focus:ring-blue-500"
            />
          </div>

          <div className="flex gap-4 pt-4">
            <button
              formAction={signIn}
              className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              Entrar
            </button>
            <button
              formAction={signUp}
              className="w-full rounded-md border border-blue-600 px-4 py-2 text-blue-600 hover:bg-blue-50"
            >
              Criar Conta
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/margem/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MarginPage } from '@/components/pages/margin-page'

export default async function MargemPage() {
  return withProtectedShell((ctx) => <MarginPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/minha-conta/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MyAccountPage } from '@/components/pages/my-account-page'

export default async function MinhaContaPage() {
  return withProtectedShell((ctx) => (
    <MyAccountPage
      email={ctx.user.email ?? 'usuario@exemplo.com'}
      workspaceName={ctx.workspace.name}
      role={ctx.role}
      workspaceId={ctx.workspaceId}
    />
  ))
}

// FIM SUBSTITUIR
` 

## web/app/monitoramento/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MonitoringPage } from '@/components/pages/monitoring-page'

export default async function MonitoramentoPage() {
  return withProtectedShell((ctx) => <MonitoringPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/page.tsx
`	sx
// INICIO SUBSTITUIR
import { redirect } from 'next/navigation'

import { createClient } from '@/utils/supabase/server'

export default async function RootPage() {
  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    redirect('/login')
  }

  redirect('/home')
}

// FIM SUBSTITUIR
` 

## web/app/pesquisa/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { MarketResearchPage } from '@/components/pages/market-research-page'

export default async function PesquisaPage() {
  return withProtectedShell((ctx) => <MarketResearchPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/regras/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { RulesPage } from '@/components/pages/rules-page'

export default async function RegrasPage() {
  return withProtectedShell(() => <RulesPage />)
}

// FIM SUBSTITUIR
` 

## web/app/relatorios/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { ReportsPage } from '@/components/pages/reports-page'

export default async function RelatoriosPage() {
  return withProtectedShell((ctx) => <ReportsPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/app/system-check/page.tsx
`	sx
// INICIO SUBSTITUIR
import { createClient } from '@/utils/supabase/server'

export default async function SystemCheckPage() {
  const supabase = await createClient()

  const { error: erroBanco } = await supabase.from('marketplace_rulesets').select('id').limit(1)

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Ultron System Check</h1>
      <hr />

      <div style={{ marginTop: '20px' }}>
        <h3>Status da Conexao:</h3>
        {erroBanco ? (
          <p style={{ color: 'red' }}>Erro ao acessar tabela: {erroBanco.message}</p>
        ) : (
          <p style={{ color: 'green' }}>Banco de dados conectado e acessivel.</p>
        )}
      </div>

      <div style={{ background: '#f4f4f4', padding: '15px', borderRadius: '8px' }}>
        <p>
          <strong>Dica:</strong> Este check usa a tabela &quot;marketplace_rulesets&quot; do schema V5. Se
          aparecer &quot;relation not found&quot;, aplique o SQL do schema atualizado.
        </p>
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/tools/alerts/page.tsx
`	sx
// INICIO SUBSTITUIR
import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function AlertsToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Alerts</h1>
          <p className="mt-2 text-slate-300">Gerencie regras e eventos de alerta.</p>
        </header>

        <ApiConsole
          title="Listar regras"
          description="GET /api/alerts"
          workspaceId={workspaceId}
          defaultPath="/api/alerts"
          defaultMethod="GET"
          defaultQuery={{}}
        />

        <ApiConsole
          title="Criar regra"
          description="POST /api/alerts"
          workspaceId={workspaceId}
          defaultPath="/api/alerts"
          defaultMethod="POST"
          defaultBody={{
            name: 'Preco abaixo do limite',
            condition: {
              field: 'price',
              op: 'lt',
              value: 99.9,
            },
            is_active: true,
          }}
        />

        <ApiConsole
          title="Listar eventos"
          description="GET /api/alerts/events"
          workspaceId={workspaceId}
          defaultPath="/api/alerts/events"
          defaultMethod="GET"
          defaultQuery={{}}
        />
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/tools/custom/page.tsx
`	sx
// INICIO SUBSTITUIR
import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function CustomToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Custom API</h1>
          <p className="mt-2 text-slate-300">
            Execute qualquer endpoint da API usando seu token autenticado.
          </p>
        </header>

        <ApiConsole
          title="Request customizada"
          description="Edite metodo, path, query e body livremente."
          workspaceId={workspaceId}
          defaultPath="/api/market-research/search"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            query: 'tenis',
            limit: 5,
            offset: 0,
          }}
          defaultBody={{}}
          lockPath={false}
        />
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/tools/market-research/page.tsx
`	sx
// INICIO SUBSTITUIR
import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function MarketResearchToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Market Research</h1>
          <p className="mt-2 text-slate-300">Consumo direto dos endpoints de pesquisa de mercado.</p>
        </header>

        <ApiConsole
          title="Buscar listings"
          description="GET /api/market-research/search"
          workspaceId={workspaceId}
          defaultPath="/api/market-research/search"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            query: 'tenis corrida',
            limit: 10,
            offset: 0,
          }}
        />

        <ApiConsole
          title="Analisar mercado"
          description="POST /api/market-research/analyze"
          workspaceId={workspaceId}
          defaultPath="/api/market-research/analyze"
          defaultMethod="POST"
          defaultBody={{
            keyword: 'tenis corrida',
            marketplace: 'mercadolivre',
            limit: 10,
          }}
        />
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/tools/page.tsx
`	sx
// INICIO SUBSTITUIR
import Link from 'next/link'

import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function ToolsHomePage() {
  const { workspaceId } = await getWorkspaceContext()

  const cards = [
    {
      href: '/tools/market-research',
      title: 'Market Research',
      description: 'Busca de produtos, analise de concorrencia e validacao de catalogo.',
    },
    {
      href: '/tools/seo',
      title: 'SEO',
      description: 'Keywords, sugestao de titulos e auditoria de listing.',
    },
    {
      href: '/tools/alerts',
      title: 'Alerts',
      description: 'Criacao e leitura de regras/eventos de monitoramento.',
    },
    {
      href: '/tools/custom',
      title: 'Custom API',
      description: 'Monte requests para qualquer endpoint /api/*.',
    },
  ]

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Ferramentas da API</h1>
          <p className="mt-2 text-slate-300">Workspace ativo: {workspaceId}</p>
        </header>

        <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {cards.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="rounded-xl border border-slate-800 bg-slate-900 p-5 transition hover:border-cyan-400"
            >
              <h2 className="text-xl font-semibold">{card.title}</h2>
              <p className="mt-2 text-sm text-slate-400">{card.description}</p>
            </Link>
          ))}
        </section>
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/tools/seo/page.tsx
`	sx
// INICIO SUBSTITUIR
import ApiConsole from '@/components/api-console'
import ToolsNav from '@/components/tools-nav'
import { getWorkspaceContext } from '@/utils/workspace/server'

export default async function SeoToolsPage() {
  const { workspaceId } = await getWorkspaceContext()

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <ToolsNav />
        <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">SEO</h1>
          <p className="mt-2 text-slate-300">Teste rapido dos endpoints de SEO.</p>
        </header>

        <ApiConsole
          title="Extrair keywords"
          description="GET /api/seo/keywords"
          workspaceId={workspaceId}
          defaultPath="/api/seo/keywords"
          defaultMethod="GET"
          defaultQuery={{
            marketplace: 'mercadolivre',
            product_title: 'Tenis Nike corrida masculino amortecimento',
            limit: 20,
          }}
        />

        <ApiConsole
          title="Otimizar titulo"
          description="POST /api/seo/optimize-title"
          workspaceId={workspaceId}
          defaultPath="/api/seo/optimize-title"
          defaultMethod="POST"
          defaultBody={{
            marketplace: 'mercadolivre',
            product_title: 'Tenis Nike corrida masculino',
            limit: 5,
          }}
        />
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/app/usuarios/page.tsx
`	sx
// INICIO SUBSTITUIR
import { withProtectedShell } from '@/components/layout/protected-app-page'
import { UsersPage } from '@/components/pages/users-page'

export default async function UsuariosPageRoute() {
  return withProtectedShell((ctx) => <UsersPage workspaceId={ctx.workspaceId} />)
}

// FIM SUBSTITUIR
` 

## web/components/api-console.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useState } from 'react'

import { createClient } from '@/utils/supabase/client'

type ApiConsoleProps = {
  title: string
  description: string
  workspaceId: string
  defaultPath: string
  defaultMethod?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  defaultQuery?: Record<string, string | number | boolean>
  defaultBody?: unknown
  lockPath?: boolean
}

function safeStringify(value: unknown) {
  return JSON.stringify(value, null, 2)
}

export default function ApiConsole({
  title,
  description,
  workspaceId,
  defaultPath,
  defaultMethod = 'GET',
  defaultQuery = {},
  defaultBody = {},
  lockPath = true,
}: ApiConsoleProps) {
  const [method, setMethod] = useState<'GET' | 'POST' | 'PUT' | 'DELETE'>(defaultMethod)
  const [path, setPath] = useState(defaultPath)
  const [queryText, setQueryText] = useState(safeStringify(defaultQuery))
  const [bodyText, setBodyText] = useState(safeStringify(defaultBody))
  const [loading, setLoading] = useState(false)
  const [statusCode, setStatusCode] = useState<number | null>(null)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  async function runRequest() {
    setLoading(true)
    setError('')
    setResult('')
    setStatusCode(null)

    try {
      const parsedQuery = queryText.trim() ? JSON.parse(queryText) : {}
      const parsedBody = bodyText.trim() ? JSON.parse(bodyText) : {}

      const supabase = createClient()
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.access_token) {
        throw new Error('Sessao expirada. Faca login novamente.')
      }

      const query = new URLSearchParams()
      Object.entries(parsedQuery as Record<string, unknown>).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          query.set(key, String(value))
        }
      })

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const normalizedPath = path.startsWith('/') ? path : `/${path}`
      const url = `${baseUrl}${normalizedPath}${query.toString() ? `?${query.toString()}` : ''}`

      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'X-Workspace-Id': workspaceId,
          ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
        },
        body: method !== 'GET' ? JSON.stringify(parsedBody) : undefined,
      })

      setStatusCode(response.status)

      const text = await response.text()
      try {
        setResult(safeStringify(JSON.parse(text)))
      } catch {
        setResult(text)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao chamar endpoint')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
        <p className="mt-1 text-sm text-slate-400">{description}</p>
      </div>

      <div className="grid gap-4">
        <div className="grid gap-3 md:grid-cols-[120px_1fr]">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as 'GET' | 'POST' | 'PUT' | 'DELETE')}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
          >
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>DELETE</option>
          </select>
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            disabled={lockPath}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
          />
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Query params (JSON)
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            rows={6}
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100"
          />
        </label>

        {method !== 'GET' && (
          <label className="grid gap-2 text-sm text-slate-300">
            Body (JSON)
            <textarea
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              rows={8}
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100"
            />
          </label>
        )}

        <button
          type="button"
          onClick={runRequest}
          disabled={loading}
          className="w-fit rounded-md bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-60"
        >
          {loading ? 'Executando...' : 'Executar endpoint'}
        </button>

        {statusCode !== null && (
          <p className="text-sm text-slate-300">
            Status: <span className="font-semibold">{statusCode}</span>
          </p>
        )}

        {error && <p className="text-sm text-red-300">{error}</p>}

        {result && (
          <pre className="overflow-x-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100">
            {result}
          </pre>
        )}
      </div>
    </section>
  )
}

// FIM SUBSTITUIR
` 

## web/components/layout/app-shell.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { type ReactNode, useMemo, useState } from 'react'

import { createClient } from '@/utils/supabase/client'

type AppShellProps = {
  children: ReactNode
  userEmail: string
  workspaceName: string
}

const primaryNav = [
  { href: '/home', label: 'Dashboard' },
  { href: '/pesquisa', label: 'Pesquisa de Mercado' },
  { href: '/auditoria', label: 'Auditoria de Anuncio' },
  { href: '/gerar-anuncio', label: 'Gerar Anuncio' },
  { href: '/monitoramento', label: 'Monitoramento & Alertas' },
  { href: '/relatorios', label: 'Relatorios' },
  { href: '/biblioteca', label: 'Biblioteca' },
  { href: '/regras', label: 'Regras por Marketplace' },
  { href: '/margem', label: 'Margem & Estrategia' },
]

const secondaryNav = [
  { href: '/configuracoes', label: 'Configuracoes' },
  { href: '/usuarios', label: 'Usuarios' },
  { href: '/minha-conta', label: 'Minha Conta' },
]

export function AppShell({ children, userEmail, workspaceName }: AppShellProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const initials = useMemo(() => (userEmail?.slice(0, 2).toUpperCase() || 'UL'), [userEmail])

  async function onSignOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
  }

  function NavItem({ href, label }: { href: string; label: string }) {
    const active = pathname === href || (href !== '/home' && pathname.startsWith(href))
    return (
      <Link
        href={href}
        className={`flex items-center rounded-lg px-3 py-2 text-sm transition ${
          active ? 'bg-primary text-primary-foreground' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
        }`}
      >
        {!collapsed ? label : label.slice(0, 2)}
      </Link>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className={`hidden border-r border-border bg-white lg:flex lg:flex-col ${collapsed ? 'w-20' : 'w-64'}`}>
        <div className="border-b border-border px-4 py-4">
          <p className="text-lg font-semibold text-slate-900">{collapsed ? 'U' : 'Ultron'}</p>
          {!collapsed ? <p className="text-xs text-slate-500">Marketplace AI</p> : null}
        </div>
        <nav className="ultron-scrollbar flex-1 space-y-1 overflow-y-auto px-3 py-3">
          {primaryNav.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </nav>
        <div className="space-y-1 border-t border-border px-3 py-3">
          {secondaryNav.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
          <button
            type="button"
            className="w-full rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
            onClick={onSignOut}
          >
            {collapsed ? 'Sair' : 'Sair'}
          </button>
          <button
            type="button"
            className="w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50"
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? 'Expandir' : 'Recolher'}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center gap-3 border-b border-border bg-white px-4">
          <input
            className="w-full max-w-md rounded-lg border border-border bg-slate-50 px-3 py-2 text-sm outline-none focus:border-primary"
            placeholder="Buscar anuncio, SKU, palavra-chave..."
          />
          <div className="hidden rounded-lg border border-border px-3 py-1.5 text-sm text-slate-700 md:block">
            ML
          </div>
          <div className="hidden rounded-lg border border-border px-3 py-1.5 text-sm text-slate-700 md:block">
            {workspaceName}
          </div>
          <button className="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-primary-foreground">
            Nova analise
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
            {initials}
          </div>
        </header>

        <main className="ultron-scrollbar flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/layout/protected-app-page.tsx
`	sx
// INICIO SUBSTITUIR
import type { ReactNode } from 'react'

import { AppShell } from '@/components/layout/app-shell'
import { getWorkspaceContext } from '@/utils/workspace/server'

export async function withProtectedShell(children: (ctx: Awaited<ReturnType<typeof getWorkspaceContext>>) => ReactNode) {
  const ctx = await getWorkspaceContext()
  return (
    <AppShell userEmail={ctx.user.email ?? 'usuario'} workspaceName={ctx.workspace.name}>
      {children(ctx)}
    </AppShell>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/ad-audit-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { FormEvent, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { compareVsCompetitors, getListingDetails, searchMarketplaceListings } from '@/services/market.service'
import { auditListing } from '@/services/seo.service'

export function AdAuditPage({ workspaceId }: { workspaceId: string }) {
  const [listingId, setListingId] = useState('')
  const [keyword, setKeyword] = useState('tenis corrida')
  const [marketplace, setMarketplace] = useState('mercadolivre')

  const myListingAction = useApiAction<Record<string, unknown>>()
  const competitorsAction = useApiAction<Record<string, unknown>>()
  const auditAction = useApiAction<Record<string, unknown>>()
  const compareAction = useApiAction<Record<string, unknown>>()

  async function onLoadMyListing(e: FormEvent) {
    e.preventDefault()
    if (!listingId) return
    await myListingAction.run(() => getListingDetails(workspaceId, listingId, marketplace))
  }

  async function onLoadCompetitors() {
    await competitorsAction.run(() =>
      searchMarketplaceListings(workspaceId, { marketplace, query: keyword, limit: 10, offset: 0 })
    )
  }

  async function onAudit() {
    await auditAction.run(() => auditListing(workspaceId, { listing_id: listingId, marketplace, keyword }))
  }

  async function onCompare() {
    await compareAction.run(() =>
      compareVsCompetitors(workspaceId, { listing_id: listingId, marketplace, keyword })
    )
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Auditoria de Anuncio</h1>

      <Card>
        <form onSubmit={onLoadMyListing} className="grid gap-3 md:grid-cols-4">
          <select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
          >
            <option value="mercadolivre">Mercado Livre</option>
            <option value="magalu">Magalu</option>
          </select>
          <input
            value={listingId}
            onChange={(e) => setListingId(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="ID do meu anuncio"
          />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm"
            placeholder="Keyword principal"
          />
          <button className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white">Carregar anuncio</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onLoadCompetitors}>
            Buscar concorrentes
          </button>
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onAudit}>
            Rodar auditoria
          </button>
          <button type="button" className="rounded-lg border border-border px-3 py-2 text-sm" onClick={onCompare}>
            Comparar vs concorrentes
          </button>
        </div>
      </Card>

      {myListingAction.error ? <ErrorState message={myListingAction.error} /> : null}
      {competitorsAction.error ? <ErrorState message={competitorsAction.error} /> : null}
      {auditAction.error ? <ErrorState message={auditAction.error} /> : null}
      {compareAction.error ? <ErrorState message={compareAction.error} /> : null}

      {myListingAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Meu anuncio</h3>
          <div className="mt-3">
            <JsonView value={myListingAction.data} />
          </div>
        </Card>
      ) : null}

      {competitorsAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Concorrentes</h3>
          <div className="mt-3">
            <JsonView value={competitorsAction.data} />
          </div>
        </Card>
      ) : null}

      {auditAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Auditoria</h3>
          <div className="mt-3">
            <JsonView value={auditAction.data} />
          </div>
        </Card>
      ) : null}

      {compareAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Comparativo</h3>
          <div className="mt-3">
            <JsonView value={compareAction.data} />
          </div>
        </Card>
      ) : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/dashboard-home.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import Link from 'next/link'
import { useEffect } from 'react'

import { useApiAction } from '@/hooks/use-api-action'
import { getDashboardInsights } from '@/services/reports.service'
import { Badge, Card, EmptyState, ErrorState, Skeleton } from '@/components/ui/primitives'

export function DashboardHome({ workspaceId }: { workspaceId: string }) {
  const insights = useApiAction<Record<string, unknown>>()

  useEffect(() => {
    insights.run(() => getDashboardInsights(workspaceId)).catch(() => null)
  }, [insights, workspaceId])

  const metrics = (insights.data?.metrics as Array<{ label: string; value: number; delta?: number; tone?: string }>) || []
  const actions = (insights.data?.next_actions as Array<{ title: string; href: string }>) || []

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Dashboard</h1>

      {insights.loading && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <Skeleton className="h-4 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
            </Card>
          ))}
        </div>
      )}

      {insights.error ? <ErrorState message={insights.error} onRetry={() => insights.run(() => getDashboardInsights(workspaceId)).catch(() => null)} /> : null}

      {!insights.loading && !insights.error && metrics.length === 0 ? (
        <EmptyState title="Sem indicadores ainda" description="Execute uma pesquisa ou auditoria para alimentar o dashboard." />
      ) : null}

      {metrics.length > 0 && (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((m) => (
            <Card key={m.label}>
              <div className="flex items-start justify-between">
                <p className="text-sm text-muted-foreground">{m.label}</p>
                <Badge tone={(m.tone as 'neutral' | 'success' | 'warning' | 'danger') || 'neutral'}>
                  {m.delta ? `${m.delta > 0 ? '+' : ''}${m.delta}` : '0'}
                </Badge>
              </div>
              <p className="mt-2 text-3xl font-semibold">{m.value}</p>
            </Card>
          ))}
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="text-xl font-semibold">Proximas 10 acoes</h2>
          {actions.length === 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">Nenhuma acao gerada ainda.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {actions.map((a, i) => (
                <li key={`${a.title}-${i}`} className="flex items-center justify-between rounded-lg border border-border bg-slate-50 px-3 py-2">
                  <span className="text-sm text-slate-700">{a.title}</span>
                  <Link href={a.href} className="text-sm font-semibold text-primary hover:underline">
                    Abrir
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="text-xl font-semibold">Atalhos rapidos</h2>
          <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {[
              { href: '/pesquisa', label: 'Pesquisar por link' },
              { href: '/auditoria', label: 'Rodar auditoria' },
              { href: '/gerar-anuncio', label: 'Gerar anuncio' },
              { href: '/monitoramento', label: 'Criar alerta' },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-slate-700 hover:border-primary hover:text-primary"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </Card>
      </section>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/generate-ad-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { extractProductSpec, parseDocument } from '@/services/documents.service'
import { analyzeImages } from '@/services/images.service'
import { suggestTitleVariants, validateTitle } from '@/services/seo.service'

export function GenerateAdPage({ workspaceId }: { workspaceId: string }) {
  const [step, setStep] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState('')
  const [title, setTitle] = useState('Tenis de corrida amortecimento premium')
  const [documentId, setDocumentId] = useState('')

  const docAction = useApiAction<Record<string, unknown>>()
  const extractAction = useApiAction<Record<string, unknown>>()
  const imageAction = useApiAction<Record<string, unknown>>()
  const titlesAction = useApiAction<Record<string, unknown>>()
  const validateAction = useApiAction<Record<string, unknown>>()

  async function onUploadDocument() {
    if (!file) return
    const data = await docAction.run(() => parseDocument(workspaceId, file))
    if (data?.document_id) {
      setDocumentId(String(data.document_id))
    }
  }

  async function onExtractSpecs() {
    if (!documentId) return
    await extractAction.run(() => extractProductSpec(workspaceId, documentId))
  }

  async function onAnalyzeImage() {
    if (!imageUrl) return
    await imageAction.run(() => analyzeImages(workspaceId, { image_urls: [imageUrl] }))
  }

  async function onGenerateTitles() {
    await titlesAction.run(() =>
      suggestTitleVariants(workspaceId, { marketplace: 'mercadolivre', product_title: title, limit: 5 })
    )
  }

  async function onValidateTitle() {
    await validateAction.run(() =>
      validateTitle(workspaceId, { marketplace: 'mercadolivre', product_title: title, limit: 5 })
    )
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Gerar Anuncio do Zero</h1>

      <Card>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStep(s)}
              className={`rounded-md px-3 py-2 text-sm ${step === s ? 'bg-primary text-white' : 'border border-border bg-white'}`}
            >
              Etapa {s}
            </button>
          ))}
        </div>
      </Card>

      {step === 1 && (
        <Card>
          <h2 className="text-xl font-semibold">1. Enviar documento</h2>
          <input
            type="file"
            accept=".pdf"
            className="mt-3"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={onUploadDocument} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
              Enviar PDF
            </button>
            <button type="button" onClick={onExtractSpecs} className="rounded-md border border-border px-3 py-2 text-sm">
              Extrair especificacoes
            </button>
          </div>
          {docAction.error ? <ErrorState message={docAction.error} /> : null}
          {extractAction.error ? <ErrorState message={extractAction.error} /> : null}
          {docAction.data ? <div className="mt-3"><JsonView value={docAction.data} /></div> : null}
          {extractAction.data ? <div className="mt-3"><JsonView value={extractAction.data} /></div> : null}
        </Card>
      )}

      {step === 2 && (
        <Card>
          <h2 className="text-xl font-semibold">2. Analise de imagens</h2>
          <input
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
            placeholder="https://..."
          />
          <button type="button" onClick={onAnalyzeImage} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Analisar imagem
          </button>
          {imageAction.error ? <ErrorState message={imageAction.error} /> : null}
          {imageAction.data ? <div className="mt-3"><JsonView value={imageAction.data} /></div> : null}
        </Card>
      )}

      {step === 3 && (
        <Card>
          <h2 className="text-xl font-semibold">3. Gerar conteudo</h2>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
          />
          <button type="button" onClick={onGenerateTitles} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Sugerir variacoes de titulo
          </button>
          {titlesAction.error ? <ErrorState message={titlesAction.error} /> : null}
          {titlesAction.data ? <div className="mt-3"><JsonView value={titlesAction.data} /></div> : null}
        </Card>
      )}

      {step === 4 && (
        <Card>
          <h2 className="text-xl font-semibold">4. Validar regras</h2>
          <button type="button" onClick={onValidateTitle} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Validar titulo
          </button>
          {validateAction.error ? <ErrorState message={validateAction.error} /> : null}
          {validateAction.data ? <div className="mt-3"><JsonView value={validateAction.data} /></div> : null}
        </Card>
      )}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/json-view.tsx
`	sx
// INICIO SUBSTITUIR
export function JsonView({ value }: { value: unknown }) {
  return (
    <pre className="ultron-scrollbar overflow-x-auto rounded-lg border border-border bg-slate-950 p-3 text-xs text-slate-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/library-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { extractProductSpec, parseDocument } from '@/services/documents.service'
import { analyzeImages } from '@/services/images.service'

export function LibraryPage({ workspaceId }: { workspaceId: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [documentId, setDocumentId] = useState('')
  const [imageUrl, setImageUrl] = useState('')

  const upload = useApiAction<Record<string, unknown>>()
  const extract = useApiAction<Record<string, unknown>>()
  const image = useApiAction<Record<string, unknown>>()

  async function onUpload() {
    if (!file) return
    const data = await upload.run(() => parseDocument(workspaceId, file))
    if (data?.document_id) setDocumentId(String(data.document_id))
  }

  async function onExtract() {
    if (!documentId) return
    await extract.run(() => extractProductSpec(workspaceId, documentId))
  }

  async function onImageAnalyze() {
    if (!imageUrl) return
    await image.run(() => analyzeImages(workspaceId, { image_urls: [imageUrl] }))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Biblioteca (Docs & Imagens)</h1>

      <Card>
        <h2 className="text-xl font-semibold">Documentos</h2>
        <input type="file" accept=".pdf" className="mt-3" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={onUpload} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Upload PDF
          </button>
          <input
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
            placeholder="document_id"
          />
          <button type="button" onClick={onExtract} className="rounded-md border border-border px-3 py-2 text-sm">
            Extrair texto
          </button>
        </div>
        {upload.error ? <div className="mt-3"><ErrorState message={upload.error} /></div> : null}
        {extract.error ? <div className="mt-3"><ErrorState message={extract.error} /></div> : null}
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Imagens</h2>
        <input
          value={imageUrl}
          onChange={(e) => setImageUrl(e.target.value)}
          className="mt-3 w-full rounded-md border border-border px-3 py-2 text-sm"
          placeholder="URL da imagem"
        />
        <button type="button" onClick={onImageAnalyze} className="mt-3 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
          Analisar imagem
        </button>
        {image.error ? <div className="mt-3"><ErrorState message={image.error} /></div> : null}
      </Card>

      {upload.data ? <Card><h3 className="text-lg font-semibold">Upload</h3><div className="mt-3"><JsonView value={upload.data} /></div></Card> : null}
      {extract.data ? <Card><h3 className="text-lg font-semibold">Extract</h3><div className="mt-3"><JsonView value={extract.data} /></div></Card> : null}
      {image.data ? <Card><h3 className="text-lg font-semibold">Image analyze</h3><div className="mt-3"><JsonView value={image.data} /></div></Card> : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/margin-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { FormEvent, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { generateReport, getReportStatus } from '@/services/reports.service'

export function MarginPage({ workspaceId }: { workspaceId: string }) {
  const [cost, setCost] = useState(100)
  const [targetPrice, setTargetPrice] = useState(190)
  const [reportId, setReportId] = useState('')
  const create = useApiAction<{ report_id: string; status: string }>()
  const status = useApiAction<Record<string, unknown>>()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const result = await create.run(() =>
      generateReport(workspaceId, {
        cost,
        min_margin_pct: 25,
        shipping_cost: 18,
        commission_pct: 14,
        lead_time_days: 7,
        target_price: targetPrice,
        findings: { module: 'margem' },
      })
    )
    setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Margem & Estrategia</h1>
      <Card>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={onSubmit}>
          <input type="number" value={cost} onChange={(e) => setCost(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Custo" />
          <input type="number" value={targetPrice} onChange={(e) => setTargetPrice(Number(e.target.value))} className="rounded-md border border-border px-3 py-2 text-sm" placeholder="Preco alvo" />
          <button className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">Calcular estrategia</button>
          <button type="button" onClick={onStatus} className="rounded-md border border-border px-3 py-2 text-sm">
            Consultar ultimo report
          </button>
        </form>
      </Card>
      {create.error ? <ErrorState message={create.error} /> : null}
      {status.error ? <ErrorState message={status.error} /> : null}
      {create.data ? <Card><JsonView value={create.data} /></Card> : null}
      {status.data ? <Card><JsonView value={status.data} /></Card> : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/market-research-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { FormEvent, useState } from 'react'

import { Card, EmptyState, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { analyzeMarket, getListingDetails, searchMarketplaceListings } from '@/services/market.service'
import { extractKeywordsFromTopListings } from '@/services/seo.service'
import { JsonView } from '@/components/pages/json-view'

export function MarketResearchPage({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState('tenis corrida')
  const [marketplace, setMarketplace] = useState('mercadolivre')
  const [selectedId, setSelectedId] = useState('')

  const searchAction = useApiAction<{ count: number; items: Array<Record<string, unknown>> }>()
  const detailAction = useApiAction<Record<string, unknown>>()
  const keywordsAction = useApiAction<Record<string, unknown>>()
  const analyzeAction = useApiAction<Record<string, unknown>>()

  async function onSearch(e: FormEvent) {
    e.preventDefault()
    await searchAction.run(async () => {
      const data = await searchMarketplaceListings(workspaceId, { marketplace, query, limit: 20, offset: 0 })
      if (data.items?.[0]?.id) setSelectedId(String(data.items[0].id))
      return { count: data.count, items: data.items as Array<Record<string, unknown>> }
    })
  }

  async function onLoadDetails() {
    if (!selectedId) return
    await detailAction.run(() => getListingDetails(workspaceId, selectedId, marketplace))
  }

  async function onKeywords() {
    await keywordsAction.run(() =>
      extractKeywordsFromTopListings(workspaceId, {
        marketplace,
        product_title: query,
        limit: 15,
      })
    )
  }

  async function onAnalyze() {
    await analyzeAction.run(() => analyzeMarket(workspaceId, { keyword: query, marketplace, limit: 20 }))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Pesquisa de Mercado</h1>

      <Card>
        <form onSubmit={onSearch} className="grid gap-3 md:grid-cols-[160px_1fr_auto]">
          <select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
          >
            <option value="mercadolivre">Mercado Livre</option>
            <option value="magalu">Magalu</option>
          </select>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded-lg border border-border bg-white px-3 py-2 text-sm"
            placeholder="Cole o link ou descreva o produto"
          />
          <button className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground" disabled={searchAction.loading}>
            {searchAction.loading ? 'Pesquisando...' : 'Pesquisar'}
          </button>
        </form>
      </Card>

      {searchAction.error ? <ErrorState message={searchAction.error} /> : null}

      {!searchAction.loading && (searchAction.data?.items?.length ?? 0) === 0 ? (
        <EmptyState title="Sem resultados" description="Ajuste os filtros e tente novamente." />
      ) : null}

      {searchAction.data?.items?.length ? (
        <Card>
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Top anuncios ({searchAction.data.count})</h2>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="rounded-md border border-border bg-white px-3 py-2 text-sm" onClick={onLoadDetails}>
                Detalhar anuncio
              </button>
              <button type="button" className="rounded-md border border-border bg-white px-3 py-2 text-sm" onClick={onKeywords}>
                Extrair keywords
              </button>
              <button type="button" className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white" onClick={onAnalyze}>
                Insights e gaps
              </button>
            </div>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-slate-500">
                <tr>
                  <th className="py-2 pr-3">ID</th>
                  <th className="py-2 pr-3">Titulo</th>
                  <th className="py-2 pr-3">Preco</th>
                </tr>
              </thead>
              <tbody>
                {searchAction.data.items.map((item, i) => (
                  <tr
                    key={`${String(item.id ?? i)}-${i}`}
                    className={`cursor-pointer border-t border-border ${selectedId === String(item.id ?? '') ? 'bg-slate-50' : ''}`}
                    onClick={() => setSelectedId(String(item.id ?? ''))}
                  >
                    <td className="py-2 pr-3">{String(item.id ?? '-')}</td>
                    <td className="py-2 pr-3">{String(item.title ?? '-')}</td>
                    <td className="py-2 pr-3">{String(item.price ?? '-')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      {detailAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Detalhe do anuncio</h3>
          <div className="mt-3">
            <JsonView value={detailAction.data} />
          </div>
        </Card>
      ) : null}

      {keywordsAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Keywords extraidas</h3>
          <div className="mt-3">
            <JsonView value={keywordsAction.data} />
          </div>
        </Card>
      ) : null}

      {analyzeAction.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Analise e insights</h3>
          <div className="mt-3">
            <JsonView value={analyzeAction.data} />
          </div>
        </Card>
      ) : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/monitoring-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useCallback, useEffect, useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { createAlert, listAlertEvents, listAlerts } from '@/services/alerts.service'

export function MonitoringPage({ workspaceId }: { workspaceId: string }) {
  const [alertName, setAlertName] = useState('Queda brusca de preco')

  const rules = useApiAction<{ items: Array<Record<string, unknown>> }>()
  const events = useApiAction<{ items: Array<Record<string, unknown>> }>()
  const create = useApiAction<{ id: string }>()

  const loadAll = useCallback(async () => {
    await Promise.all([rules.run(() => listAlerts(workspaceId)), events.run(() => listAlertEvents(workspaceId))])
  }, [events, rules, workspaceId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadAll().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadAll])

  async function onCreate() {
    await create.run(() =>
      createAlert(workspaceId, {
        name: alertName,
        condition: { field: 'price', op: 'lt', value: 99.9 },
        is_active: true,
      })
    )
    await loadAll()
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Monitoramento & Alertas</h1>

      <Card>
        <h2 className="text-xl font-semibold">Criar alerta</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <input
            value={alertName}
            onChange={(e) => setAlertName(e.target.value)}
            className="min-w-[280px] rounded-md border border-border px-3 py-2 text-sm"
          />
          <button type="button" onClick={onCreate} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Criar
          </button>
        </div>
        {create.error ? <div className="mt-3"><ErrorState message={create.error} /></div> : null}
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Regras ativas</h2>
        {rules.error ? <div className="mt-3"><ErrorState message={rules.error} onRetry={() => loadAll()} /></div> : null}
        <div className="mt-3">
          <JsonView value={rules.data ?? { items: [] }} />
        </div>
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Historico de eventos</h2>
        {events.error ? <div className="mt-3"><ErrorState message={events.error} onRetry={() => loadAll()} /></div> : null}
        <div className="mt-3">
          <JsonView value={events.data ?? { items: [] }} />
        </div>
      </Card>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/my-account-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { Card, Chip } from '@/components/ui/primitives'

export function MyAccountPage({
  email,
  workspaceName,
  role,
  workspaceId,
}: {
  email: string
  workspaceName: string
  role: string
  workspaceId: string
}) {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Minha Conta</h1>
      <Card className="space-y-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Email</p>
          <p className="text-sm text-slate-800">{email}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Workspace</p>
          <p className="text-sm text-slate-800">{workspaceName}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip>{role}</Chip>
          <Chip>{workspaceId}</Chip>
        </div>
      </Card>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/reports-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useState } from 'react'

import { JsonView } from '@/components/pages/json-view'
import { Card, ErrorState } from '@/components/ui/primitives'
import { useApiAction } from '@/hooks/use-api-action'
import { generateReport, getReportStatus } from '@/services/reports.service'

export function ReportsPage({ workspaceId }: { workspaceId: string }) {
  const [reportId, setReportId] = useState('')
  const create = useApiAction<{ report_id: string; status: string }>()
  const status = useApiAction<Record<string, unknown>>()

  async function onGenerate() {
    const payload = {
      cost: 100,
      min_margin_pct: 25,
      shipping_cost: 18,
      commission_pct: 14,
      lead_time_days: 7,
      target_price: 189,
      findings: { source: 'ui-report-generator' },
    }
    const result = await create.run(() => generateReport(workspaceId, payload))
    setReportId(result.report_id)
  }

  async function onStatus() {
    if (!reportId) return
    await status.run(() => getReportStatus(workspaceId, reportId))
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Relatorios</h1>
      <Card>
        <h2 className="text-xl font-semibold">Gerar relatorio estrategico</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={onGenerate} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
            Gerar relatorio
          </button>
          <input
            value={reportId}
            onChange={(e) => setReportId(e.target.value)}
            className="rounded-md border border-border px-3 py-2 text-sm"
            placeholder="Report ID"
          />
          <button type="button" onClick={onStatus} className="rounded-md border border-border px-3 py-2 text-sm">
            Consultar status
          </button>
        </div>
        {create.error ? <div className="mt-3"><ErrorState message={create.error} /></div> : null}
        {status.error ? <div className="mt-3"><ErrorState message={status.error} /></div> : null}
      </Card>
      {create.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Criacao</h3>
          <div className="mt-3"><JsonView value={create.data} /></div>
        </Card>
      ) : null}
      {status.data ? (
        <Card>
          <h3 className="text-lg font-semibold">Status</h3>
          <div className="mt-3"><JsonView value={status.data} /></div>
        </Card>
      ) : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/rules-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useCallback, useEffect, useState } from 'react'

import { Card, EmptyState, ErrorState } from '@/components/ui/primitives'
import { createClient } from '@/utils/supabase/client'

type RulesetRow = {
  id: string
  platform: string
  category_id: string | null
  version: number | null
  updated_at: string | null
}

export function RulesPage() {
  const [items, setItems] = useState<RulesetRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const supabase = createClient()
    const { data, error } = await supabase
      .from('marketplace_rulesets')
      .select('id,platform,category_id,version,updated_at')
      .order('updated_at', { ascending: false })
      .limit(50)
    if (error) {
      setError(error.message)
    } else {
      setItems((data as RulesetRow[]) ?? [])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      load().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Regras por Marketplace</h1>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      {loading ? <Card><p className="text-sm text-muted-foreground">Carregando regras...</p></Card> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState title="Sem regras cadastradas" description="Adicione regras no painel Supabase ou via seed." />
      ) : null}
      {items.length > 0 ? (
        <Card>
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2 pr-3">Platform</th>
                <th className="py-2 pr-3">Category</th>
                <th className="py-2 pr-3">Version</th>
                <th className="py-2 pr-3">Updated</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="py-2 pr-3">{item.platform}</td>
                  <td className="py-2 pr-3">{item.category_id ?? '-'}</td>
                  <td className="py-2 pr-3">{item.version ?? '-'}</td>
                  <td className="py-2 pr-3">{item.updated_at ? new Date(item.updated_at).toLocaleString('pt-BR') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : null}
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/settings-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'

import { Card, ErrorState } from '@/components/ui/primitives'
import { getWorkspaceSettings, updateWorkspaceName } from '@/services/settings.service'

export function SettingsPage({ workspaceId }: { workspaceId: string }) {
  const [name, setName] = useState('')
  const [plan, setPlan] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getWorkspaceSettings(workspaceId)
      setName(data?.name ?? '')
      setPlan(data?.plan ?? '')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      load().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const data = await updateWorkspaceName(workspaceId, name)
      setName(data.name ?? name)
      setPlan(data.plan ?? plan)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao salvar')
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Configuracoes</h1>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      <Card>
        {loading ? (
          <p className="text-sm text-muted-foreground">Carregando...</p>
        ) : (
          <form onSubmit={onSubmit} className="grid gap-3 md:max-w-xl">
            <label className="text-sm text-slate-600">Nome do workspace</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="rounded-md border border-border px-3 py-2 text-sm" />
            <label className="text-sm text-slate-600">Plano</label>
            <input value={plan} disabled className="rounded-md border border-border bg-slate-50 px-3 py-2 text-sm" />
            <button className="w-fit rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">Salvar</button>
          </form>
        )}
      </Card>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/pages/users-page.tsx
`	sx
// INICIO SUBSTITUIR
'use client'

import { useCallback, useEffect, useState } from 'react'

import { Card, ErrorState } from '@/components/ui/primitives'
import { getWorkspaceMembers } from '@/services/settings.service'

type Member = {
  user_id: string
  role: string
  created_at: string
}

export function UsersPage({ workspaceId }: { workspaceId: string }) {
  const [members, setMembers] = useState<Member[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = (await getWorkspaceMembers(workspaceId)) as Member[]
      setMembers(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar usuarios')
    } finally {
      setLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      load().catch(() => null)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-semibold">Usuarios</h1>
      {error ? <ErrorState message={error} onRetry={() => load()} /> : null}
      <Card>
        {loading ? (
          <p className="text-sm text-muted-foreground">Carregando membros...</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2 pr-3">User ID</th>
                <th className="py-2 pr-3">Role</th>
                <th className="py-2 pr-3">Criado em</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={`${m.user_id}-${m.created_at}`} className="border-t border-border">
                  <td className="py-2 pr-3">{m.user_id}</td>
                  <td className="py-2 pr-3">{m.role}</td>
                  <td className="py-2 pr-3">{new Date(m.created_at).toLocaleString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

// FIM SUBSTITUIR
` 

## web/components/tools-nav.tsx
`	sx
// INICIO SUBSTITUIR
import Link from 'next/link'

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/tools', label: 'Ferramentas' },
  { href: '/tools/market-research', label: 'Market Research' },
  { href: '/tools/seo', label: 'SEO' },
  { href: '/tools/alerts', label: 'Alerts' },
  { href: '/tools/custom', label: 'Custom API' },
]

export default function ToolsNav() {
  return (
    <nav className="flex flex-wrap gap-2">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 hover:border-cyan-400 hover:text-cyan-300"
        >
          {link.label}
        </Link>
      ))}
    </nav>
  )
}

// FIM SUBSTITUIR
` 

## web/components/ui/primitives.tsx
`	sx
// INICIO SUBSTITUIR
import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-border bg-card p-5 shadow-sm ${className}`}>{children}</section>
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-slate-100 text-slate-700',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    danger: 'bg-red-100 text-red-700',
  }
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>
}

export function Chip({ children }: { children: ReactNode }) {
  return <span className="inline-flex rounded-md border border-border bg-white px-2 py-1 text-xs text-slate-600">{children}</span>
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className}`} />
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <Card className="text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </Card>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <Card className="border-red-200 bg-red-50">
      <p className="text-sm text-red-700">{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="mt-3 rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700"
          onClick={onRetry}
        >
          Tentar novamente
        </button>
      ) : null}
    </Card>
  )
}

// FIM SUBSTITUIR
` 

## web/hooks/use-api-action.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { useCallback, useState } from 'react'

export function useApiAction<T>() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [data, setData] = useState<T | null>(null)

  const run = useCallback(async (fn: () => Promise<T>) => {
    setLoading(true)
    setError('')
    try {
      const response = await fn()
      setData(response)
      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro desconhecido'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, data, setData, setError, run }
}

// FIM SUBSTITUIR
` 

## web/lib/api-client.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { createClient } from '@/utils/supabase/client'

import type { ApiError } from '@/lib/api-types'

type ApiRequestParams = {
  path: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  query?: Record<string, string | number | boolean | null | undefined>
  body?: unknown
  workspaceId?: string
  timeoutMs?: number
}

function toQueryString(query?: ApiRequestParams['query']) {
  if (!query) return ''
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    qs.set(key, String(value))
  }
  const result = qs.toString()
  return result ? `?${result}` : ''
}

export async function apiRequest<T>({
  path,
  method = 'GET',
  query,
  body,
  workspaceId,
  timeoutMs = 15000,
}: ApiRequestParams): Promise<T> {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    const err: ApiError = { message: 'Sessao expirada. Faca login novamente.' }
    throw err
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${baseUrl}${path}${toQueryString(query)}`, {
      method,
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        ...(workspaceId ? { 'X-Workspace-Id': workspaceId } : {}),
        ...(method !== 'GET' ? { 'Content-Type': 'application/json' } : {}),
      },
      body: method !== 'GET' ? JSON.stringify(body ?? {}) : undefined,
    })

    const text = await response.text()
    let parsed: unknown = {}
    if (text) {
      try {
        parsed = JSON.parse(text)
      } catch {
        parsed = { raw: text }
      }
    }

    if (!response.ok) {
      const err: ApiError = {
        message: (parsed as { detail?: string })?.detail || `Falha na API (${response.status})`,
        status: response.status,
        detail: parsed,
      }
      throw err
    }

    return parsed as T
  } finally {
    clearTimeout(timer)
  }
}

// FIM SUBSTITUIR
` 

## web/lib/api-types.ts
`	sx
// INICIO SUBSTITUIR
export type ApiError = {
  message: string
  status?: number
  detail?: unknown
}

export type ListingNormalized = {
  id?: string
  title?: string
  price?: number
  final_price_estimate?: number
  seller?: { id?: string; nickname?: string; reputation?: string }
  [key: string]: unknown
}

export type MarketDashboard = {
  [key: string]: unknown
}

export type AuditReport = {
  scores?: Record<string, number>
  recommendations?: Array<string | { title?: string; description?: string }>
  [key: string]: unknown
}

export type SeoInsights = {
  keywords?: string[]
  titles?: string[]
  [key: string]: unknown
}

export type AlertEvent = {
  id: string
  status?: string
  triggered_at?: string
  event_data?: Record<string, unknown>
}

// FIM SUBSTITUIR
` 

## web/middleware.ts
`	sx
// INICIO SUBSTITUIR
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export default async function middleware(request: NextRequest) {
  const response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  await supabase.auth.getUser()

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}

// FIM SUBSTITUIR
` 

## web/services/alerts.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'
import type { AlertEvent } from '@/lib/api-types'

export async function listAlerts(workspaceId: string) {
  return apiRequest<{ items: Array<Record<string, unknown>> }>({
    path: '/api/alerts',
    method: 'GET',
    workspaceId,
  })
}

export async function createAlert(workspaceId: string, payload: { name: string; condition: Record<string, unknown>; listing_id?: string; is_active?: boolean }) {
  return apiRequest<{ id: string }>({
    path: '/api/alerts',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function listAlertEvents(workspaceId: string) {
  return apiRequest<{ items: AlertEvent[] }>({
    path: '/api/alerts/events',
    method: 'GET',
    workspaceId,
  })
}

// FIM SUBSTITUIR
` 

## web/services/documents.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { createClient } from '@/utils/supabase/client'

export async function parseDocument(workspaceId: string, file: File) {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) {
    throw new Error('Sessao expirada.')
  }

  const form = new FormData()
  form.append('file', file)

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const response = await fetch(`${baseUrl}/api/documents/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'X-Workspace-Id': workspaceId,
    },
    body: form,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Falha no upload (${response.status})`)
  }

  return response.json()
}

export async function extractProductSpec(workspaceId: string, documentId: string) {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session?.access_token) {
    throw new Error('Sessao expirada.')
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const response = await fetch(`${baseUrl}/api/documents/${documentId}/extract`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      'X-Workspace-Id': workspaceId,
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Falha no extract (${response.status})`)
  }

  return response.json()
}

// FIM SUBSTITUIR
` 

## web/services/images.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'

export async function analyzeImages(workspaceId: string, payload: { image_urls: string[] }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/v2/images/analyze',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function layoutAudit(workspaceId: string, payload: { image_url: string }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/v2/images/layout-audit',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

// FIM SUBSTITUIR
` 

## web/services/listings.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'

export async function getMyListings(workspaceId: string, params: { marketplace: string; limit?: number; offset?: number }) {
  return apiRequest<{ items: Array<Record<string, unknown>>; count: number }>({
    path: '/api/market-research/my-listings',
    method: 'GET',
    workspaceId,
    query: params,
  })
}

// FIM SUBSTITUIR
` 

## web/services/market.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'
import type { ListingNormalized } from '@/lib/api-types'

export async function searchMarketplaceListings(workspaceId: string, params: { marketplace: string; query: string; limit?: number; offset?: number }) {
  return apiRequest<{ workspace_id: string; count: number; items: ListingNormalized[] }>({
    path: '/api/market-research/search',
    method: 'GET',
    workspaceId,
    query: params,
  })
}

export async function getListingDetails(workspaceId: string, productId: string, marketplace: string) {
  return apiRequest<{ workspace_id: string; normalized: ListingNormalized }>({
    path: `/api/market-research/product/${productId}`,
    method: 'GET',
    workspaceId,
    query: { marketplace },
  })
}

export async function compareVsCompetitors(workspaceId: string, payload: Record<string, unknown>) {
  return apiRequest<Record<string, unknown>>({
    path: '/compare',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function analyzeMarket(workspaceId: string, payload: { keyword: string; marketplace: string; limit?: number }) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/market-research/analyze',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

// FIM SUBSTITUIR
` 

## web/services/reports.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'

export async function generateReport(workspaceId: string, payload: Record<string, unknown>) {
  return apiRequest<{ report_id: string; status: string }>({
    path: '/api/reports/generate',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function getReportStatus(workspaceId: string, reportId: string) {
  return apiRequest<Record<string, unknown>>({
    path: `/api/reports/${reportId}/status`,
    method: 'GET',
    workspaceId,
  })
}

export async function getDashboardInsights(workspaceId: string) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/reports/v2/insights',
    method: 'GET',
    workspaceId,
  })
}

// FIM SUBSTITUIR
` 

## web/services/seo.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { apiRequest } from '@/lib/api-client'

export async function extractKeywordsFromTopListings(
  workspaceId: string,
  params: { marketplace: string; product_title: string; limit?: number; category?: string }
) {
  return apiRequest<{ keywords: string[] }>({
    path: '/api/seo/keywords',
    method: 'GET',
    workspaceId,
    query: params,
  })
}

export async function suggestTitleVariants(
  workspaceId: string,
  payload: { marketplace: string; product_title: string; limit?: number; category?: string }
) {
  return apiRequest<{ titles: string[] }>({
    path: '/api/seo/optimize-title',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function validateTitle(workspaceId: string, payload: { marketplace: string; product_title: string; limit?: number }) {
  return apiRequest<Record<string, unknown>>({
    path: '/validate-title',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

export async function auditListing(
  workspaceId: string,
  payload: { listing_id: string; marketplace: string; keyword?: string }
) {
  return apiRequest<Record<string, unknown>>({
    path: '/api/seo/analyze-listing',
    method: 'POST',
    workspaceId,
    body: payload,
  })
}

// FIM SUBSTITUIR
` 

## web/services/settings.service.ts
`	sx
// INICIO SUBSTITUIR
'use client'

import { createClient } from '@/utils/supabase/client'

export async function getWorkspaceMembers(workspaceId: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspace_members')
    .select('workspace_id,user_id,role,created_at')
    .eq('workspace_id', workspaceId)
    .order('created_at', { ascending: false })

  if (error) throw new Error(error.message)
  return data ?? []
}

export async function getWorkspaceSettings(workspaceId: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspaces')
    .select('id,name,plan,created_at,updated_at')
    .eq('id', workspaceId)
    .maybeSingle()

  if (error) throw new Error(error.message)
  return data
}

export async function updateWorkspaceName(workspaceId: string, name: string) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('workspaces')
    .update({ name })
    .eq('id', workspaceId)
    .select('id,name,plan,updated_at')
    .single()

  if (error) throw new Error(error.message)
  return data
}

// FIM SUBSTITUIR
` 

## web/utils/workspace/server.ts
`	sx
// INICIO SUBSTITUIR
import { redirect } from 'next/navigation'

import { createClient } from '@/utils/supabase/server'

type WorkspaceContext = {
  user: { id: string; email: string | null }
  workspaceId: string
  role: string
  workspace: { id: string; name: string; plan: string | null }
}

export async function getWorkspaceContext(): Promise<WorkspaceContext> {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  let { data: membership } = await supabase
    .from('workspace_members')
    .select('workspace_id, role, workspaces(id, name, plan)')
    .eq('user_id', user.id)
    .limit(1)
    .maybeSingle()

  if (!membership?.workspace_id) {
    const workspaceName = `${(user.email ?? 'workspace').split('@')[0]}-workspace`
    const { data: createdWorkspace } = await supabase
      .from('workspaces')
      .insert({ name: workspaceName })
      .select('id, name, plan')
      .single()

    if (createdWorkspace?.id) {
      await supabase.from('workspace_members').insert({
        workspace_id: createdWorkspace.id,
        user_id: user.id,
        role: 'admin',
      })
    }

    const retry = await supabase
      .from('workspace_members')
      .select('workspace_id, role, workspaces(id, name, plan)')
      .eq('user_id', user.id)
      .limit(1)
      .maybeSingle()

    membership = retry.data
  }

  if (!membership?.workspace_id) redirect('/dashboard')
  const workspace = Array.isArray(membership.workspaces) ? membership.workspaces[0] : membership.workspaces
  if (!workspace?.id) redirect('/dashboard')

  return {
    user: { id: user.id, email: user.email ?? null },
    workspaceId: membership.workspace_id,
    role: membership.role,
    workspace: {
      id: workspace.id,
      name: workspace.name,
      plan: workspace.plan ?? 'free',
    },
  }
}

// FIM SUBSTITUIR
` 



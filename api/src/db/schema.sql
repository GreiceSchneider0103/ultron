-- ============================================================
-- ULTRON — Schema Supabase (PostgreSQL)
-- Execute no SQL Editor do Supabase Dashboard
-- Cole em: api/src/db/schema.sql
-- ============================================================

create extension if not exists "uuid-ossp";

-- ── listings ──────────────────────────────────────────────────
create table if not exists listings (
  id                   uuid primary key default uuid_generate_v4(),
  marketplace          text not null,
  listing_id           text not null,
  url                  text,
  title                text,
  price                numeric(12,2),
  price_original       numeric(12,2),
  shipping_cost        numeric(12,2) default 0,
  final_price_estimate numeric(12,2),
  seller_id            text,
  seller_name          text,
  seller_reputation    text,
  review_count         int default 0,
  rating               numeric(3,2) default 0,
  media_count          int default 0,
  badges               jsonb default '{}',
  attributes           jsonb default '{}',
  seo_terms            text[] default '{}',
  scraped_at           timestamptz default now(),
  created_at           timestamptz default now(),
  updated_at           timestamptz default now(),

  constraint uq_listings unique (marketplace, listing_id)
);

create index if not exists idx_listings_marketplace on listings(marketplace);
create index if not exists idx_listings_price       on listings(price);
create index if not exists idx_listings_scraped_at  on listings(scraped_at desc);
create index if not exists idx_listings_seo_terms   on listings using gin(seo_terms);

-- ── price_history ─────────────────────────────────────────────
create table if not exists price_history (
  id          uuid primary key default uuid_generate_v4(),
  listing_id  uuid references listings(id) on delete cascade,
  price       numeric(12,2) not null,
  shipping    numeric(12,2) default 0,
  recorded_at timestamptz default now()
);
create index if not exists idx_price_history_listing on price_history(listing_id);

-- ── market_researches ─────────────────────────────────────────
create table if not exists market_researches (
  id                 uuid primary key default uuid_generate_v4(),
  keyword            text not null,
  marketplace        text not null,
  total_collected    int default 0,
  price_range        jsonb default '{}',
  top_seo_terms      jsonb default '[]',
  competitor_summary jsonb default '{}',
  gaps               jsonb default '[]',
  research_at        timestamptz default now()
);

-- ── listing_audits ────────────────────────────────────────────
create table if not exists listing_audits (
  id                    uuid primary key default uuid_generate_v4(),
  listing_id            text not null,
  marketplace           text not null,
  seo_score             numeric(5,1),
  conversion_score      numeric(5,1),
  competitiveness_score numeric(5,1),
  overall_score         numeric(5,1),
  seo_breakdown         jsonb default '{}',
  conversion_breakdown  jsonb default '{}',
  top_actions           text[] default '{}',
  generated_titles      text[] default '{}',
  audit_at              timestamptz default now()
);

-- ── generated_listings ────────────────────────────────────────
create table if not exists generated_listings (
  id                uuid primary key default uuid_generate_v4(),
  keyword           text not null,
  marketplace       text not null,
  attributes        jsonb default '{}',
  titulos           text[] default '{}',
  bullets           text[] default '{}',
  descricao         text,
  keywords_ads      text[] default '{}',
  pauta_fotografica jsonb default '[]',
  sugestao_preco    jsonb default '{}',
  ab_test_ideas     jsonb default '[]',
  market_context    jsonb default '{}',
  created_at        timestamptz default now()
);

-- ── Trigger: updated_at automático ───────────────────────────
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

create trigger listings_updated_at
  before update on listings
  for each row execute function set_updated_at();
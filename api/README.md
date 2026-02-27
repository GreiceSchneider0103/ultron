# ULTRON API

API FastAPI para Market Research, SEO, Ads, Documents, Reports e Alerts.

## Start (unico)

```bash
uvicorn api.src.main:app --reload
```

## Setup rapido

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r api/requirements.txt
copy api\.env.example .env
```

## Migrações versionadas (mínimo)

Este projeto usa migrações SQL versionadas em `api/migrations/versions`.

- Dev (SQLite local):

```bash
python api/scripts/apply_migrations.py
```

- Staging (Postgres/Supabase SQL editor):
  - Aplicar os arquivos `api/migrations/versions/*.sql` em ordem (0001, 0002, ...).
  - Registrar versão em `public.schema_migrations`.

## Auth e Workspace

- Todos os endpoints em `/api/*` exigem `Authorization: Bearer <supabase_jwt>`.
- O `workspace_id` pode vir no claim `workspace_id` do JWT ou no header `X-Workspace-Id`.

## Entrypoints

- Oficial: `api/src/main.py`
- Compat legado: `api/main.py` (wrapper)

## Prefixos principais

- `/api/market-research`
- `/api/seo`
- `/api/ads`
- `/api/documents`
- `/api/reports`
- `/api/alerts`
- Compat Postman: `/api/monitoring`

## Not implemented

Endpoints ainda nao finalizados retornam HTTP 501 no formato:

```json
{
  "error": "not_implemented",
  "module": "ads",
  "endpoint": "/api/ads/create",
  "message": "This endpoint is planned but not implemented yet."
}
```

## Testes smoke (contrato e endpoints)

```bash
python -m pytest -q api/tests/test_contract_smoke.py api/tests/test_endpoints_smoke.py
```

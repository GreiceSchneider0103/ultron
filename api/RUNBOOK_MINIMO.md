# Runbook Mínimo (uso interno)

## 1) Subir serviço

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r api/requirements.txt
python api/scripts/apply_migrations.py
uvicorn api.src.main:app --reload
```

## 2) Validar rapidamente

```bash
python -m compileall api/src -q
python -m pytest -q api/tests/test_contract_smoke.py api/tests/test_endpoints_smoke.py
```

Health check:

```bash
curl http://localhost:8000/health
```

## 3) Diagnóstico de 503 (proxy/backend)

1. Confirmar API no ar em `:8000` e `/health` = `healthy`.
2. Verificar `SUPABASE_URL`/chaves no `.env` (503 comum quando cliente DB indisponível).
3. Verificar logs com `trace_id` retornado no header `X-Trace-Id`.
4. No frontend, confirmar chamadas via `/api/proxy/...` e não backend direto.

## 4) Reset rápido local

1. Parar servidor.
2. Remover banco SQLite local (`ultron.db`) apenas em ambiente dev.
3. Rodar `python api/scripts/apply_migrations.py`.
4. Subir novamente com `uvicorn`.

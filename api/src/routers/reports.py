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

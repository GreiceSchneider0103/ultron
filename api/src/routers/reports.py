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

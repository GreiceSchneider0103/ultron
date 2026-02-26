from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.routers.schemas import AlertsCreateRequest, AlertsUpdateRequest

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
monitoring_router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.post("")
async def alerts_create(req: AlertsCreateRequest, ctx: RequestContext = Depends(require_auth_context)):
    alert_id = repository.create_alert_rule(
        workspace_id=ctx.workspace_id,
        name=req.name,
        condition=req.condition,
        listing_id=req.listing_id,
        is_active=req.is_active,
        supabase_jwt=ctx.token,
    )
    if not alert_id:
        raise HTTPException(status_code=500, detail="Failed to create alert rule.")
    return {"id": alert_id}


@router.get("")
async def alerts_list(ctx: RequestContext = Depends(require_auth_context)):
    return {"items": repository.list_alert_rules(workspace_id=ctx.workspace_id, supabase_jwt=ctx.token)}


@router.put("/{alert_id}")
async def alerts_update(alert_id: str, req: AlertsUpdateRequest, ctx: RequestContext = Depends(require_auth_context)):
    payload = req.model_dump(exclude_none=True)
    ok = repository.update_alert_rule(workspace_id=ctx.workspace_id, alert_id=alert_id, data=payload, supabase_jwt=ctx.token)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update alert rule.")
    return {"ok": True}


@router.delete("/{alert_id}")
async def alerts_delete(alert_id: str, ctx: RequestContext = Depends(require_auth_context)):
    ok = repository.delete_alert_rule(workspace_id=ctx.workspace_id, alert_id=alert_id, supabase_jwt=ctx.token)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete alert rule.")
    return {"ok": True}


@router.get("/events")
async def alerts_events(ctx: RequestContext = Depends(require_auth_context)):
    return {"items": repository.list_alert_events(workspace_id=ctx.workspace_id, supabase_jwt=ctx.token)}


@monitoring_router.post("/alerts")
async def monitoring_alerts_create(req: AlertsCreateRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await alerts_create(req=req, ctx=ctx)


@monitoring_router.get("/alerts")
async def monitoring_alerts_list(
    marketplace: Optional[str] = None,
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    return await alerts_list(ctx=ctx)


@monitoring_router.get("/events")
async def monitoring_events(
    product_id: Optional[str] = None,
    marketplace: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    return await alerts_events(ctx=ctx)

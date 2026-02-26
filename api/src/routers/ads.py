from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from api.src.auth import RequestContext, require_auth_context
from api.src.routers.common import not_implemented
from api.src.routers.schemas import AdsCreateRequest

router = APIRouter(prefix="/api/ads", tags=["ads"])


@router.get("/campaigns")
async def ads_campaigns(
    marketplace: str,
    status: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("ads", "/api/ads/campaigns")


@router.get("/campaigns/{campaign_id}/performance")
async def ads_campaign_performance(
    campaign_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = "daily",
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("ads", f"/api/ads/campaigns/{campaign_id}/performance")


@router.put("/campaigns/{campaign_id}")
async def ads_campaign_update(
    campaign_id: str,
    req: Dict[str, Any],
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("ads", f"/api/ads/campaigns/{campaign_id}")


@router.get("/recommendations")
async def ads_recommendations(
    marketplace: str,
    product_id: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("ads", "/api/ads/recommendations")


@router.post("/create")
async def ads_create(req: AdsCreateRequest, ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("ads", "/api/ads/create")


@router.post("/bulk-create")
async def ads_bulk_create(req: List[AdsCreateRequest], ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("ads", "/api/ads/bulk-create")

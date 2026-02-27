from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.services.asset_storage import register_link_asset
from api.src.services.governance import track_expensive_call
from api.src.services.multimodal import analyze_image_set

router = APIRouter(prefix="/api/v2/images", tags=["images-v2"])


@router.post("/analyze")
async def images_analyze_v2(req: Dict[str, Any], request: Request, ctx: RequestContext = Depends(require_auth_context)):
    trace_id = getattr(request.state, "trace_id", None)
    track_expensive_call(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        feature="images_analyze",
        trace_id=trace_id,
        metadata={"endpoint": "/api/v2/images/analyze"},
        supabase_jwt=ctx.token,
    )
    image_urls: List[str] = req.get("image_urls", []) or []
    category = req.get("category")
    analysis = analyze_image_set(image_urls=image_urls, category=category)
    assets = [register_link_asset(link=url, kind="images") for url in image_urls]
    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="image_analyze",
        status="completed",
        result_summary={"assets": assets, "analysis": analysis},
        supabase_jwt=ctx.token,
    )
    return {
        "workspace_id": ctx.workspace_id,
        "image_count": len(image_urls),
        "analysis_id": job_id,
        "assets": assets,
        **analysis,
    }


@router.post("/layout-audit")
async def images_layout_audit_v2(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    image_url = req.get("image_url")
    category = req.get("category")
    analysis = analyze_image_set(image_urls=[image_url] if image_url else [], category=category)
    return {
        "workspace_id": ctx.workspace_id,
        "image_url": image_url,
        "layout_score": round((analysis["cover_strength_score"] + analysis["angle_variety_score"]) / 2, 1),
        "recommendations": analysis["missing_shots"][:4] + analysis["quality_issues"][:4],
        "missing_shots": analysis["missing_shots"],
        "quality_issues": analysis["quality_issues"],
    }

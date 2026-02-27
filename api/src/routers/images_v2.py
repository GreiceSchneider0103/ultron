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

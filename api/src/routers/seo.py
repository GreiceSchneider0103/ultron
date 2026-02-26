from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.src.auth import RequestContext, require_auth_context
from api.src.db import repository
from api.src.functions.generator import generate_titles
from api.src.orchestrator.agent import MarketAgent
from api.src.reports.audit_report import generate_audit_report
from api.src.routers.common import not_implemented
from api.src.routers.schemas import AnalyzeRequest, AuditListingRequest, OptimizeTitleRequest
from api.src.services.marketplace import get_agent, marketplace_alias

router = APIRouter(prefix="/api/seo", tags=["seo"])


@router.get("/keywords")
async def seo_keywords(
    marketplace: str,
    product_title: str,
    category: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50),
    ctx: RequestContext = Depends(require_auth_context),
):
    terms = [part.strip(".,;:!?").lower() for part in product_title.split() if len(part) >= 4]
    dedup = list(dict.fromkeys(terms))
    return {"workspace_id": ctx.workspace_id, "marketplace": marketplace_alias(marketplace), "keywords": dedup[:limit]}


@router.post("/analyze-listing")
async def seo_analyze_listing(
    req: AuditListingRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    result = await agent.audit_listing(
        listing_id=req.listing_id,
        marketplace=marketplace_alias(req.marketplace),
        keyword=req.keyword,
    )
    listing_id = repository.upsert_listings_current(
        workspace_id=ctx.workspace_id,
        platform=req.marketplace,
        external_id=req.listing_id,
        raw_data={},
        normalized_data={},
        derived_data={"source": "seo_analyze_listing"},
        supabase_jwt=ctx.token,
    )
    if listing_id:
        repository.insert_audit(
            workspace_id=ctx.workspace_id,
            listing_id=listing_id,
            scores=result.model_dump().get("seo_score", {}),
            recommendations=result.model_dump().get("top_actions", []),
            supabase_jwt=ctx.token,
        )
    audit_payload = generate_audit_report(
        scores={"seo": result.seo_score.score, "conversion": result.conversion_score.score, "competitiveness": result.competitiveness_score.score},
        recommendations=result.top_actions,
        metadata={"version": 1},
    )
    return {"audit": result.model_dump(), "report": audit_payload}


@router.post("/optimize-title")
async def seo_optimize_title(
    req: OptimizeTitleRequest,
    ctx: RequestContext = Depends(require_auth_context),
):
    titles = await generate_titles(
        keyword=req.product_title,
        marketplace=marketplace_alias(req.marketplace),
        n_variants=req.limit,
    )
    return {"workspace_id": ctx.workspace_id, "titles": titles}


@router.get("/ranking")
async def seo_ranking(
    product_id: str,
    marketplace: str,
    keyword: str,
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("seo", "/api/seo/ranking")


@router.post("/competitor-keywords")
async def seo_competitor_keywords(
    req: AnalyzeRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    research = await agent.research_market(req.keyword, marketplace_alias(req.marketplace), limit=req.limit)
    return {"workspace_id": ctx.workspace_id, "keywords": research.top_seo_terms}

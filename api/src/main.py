"""Ultron API main entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.src.auth import RequestContext, require_auth_context
from api.src.config import get_settings, settings
from api.src.connectors.base import BaseConnector
from api.src.connectors.magalu import MagaluConnector
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.contracts import validate_against_contract
from api.src.db import repository
from api.src.functions import function_calls
from api.src.functions.generator import generate_bullets, generate_description, generate_titles
from api.src.orchestrator.agent import MarketAgent
from api.src.reports import generate_action_plan, generate_audit_report, generate_market_dashboard
from api.src.strategy.margin_strategy import decide_margin_strategy

logger = logging.getLogger(__name__)


def _marketplace_alias(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"mercadolivre", "mercado_livre", "meli"}:
        return "mercado_livre"
    if normalized in {"magalu", "magazine_luiza"}:
        return "magalu"
    raise HTTPException(status_code=400, detail=f"Unsupported marketplace: {value}")


def _not_implemented(module: str, endpoint: str, message: str = "This endpoint is planned but not implemented yet.") -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_implemented",
            "module": module,
            "endpoint": endpoint,
            "message": message,
        },
    )


def _not_implemented_from_stub(stub: dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=501, content=stub)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ultron_startup", extra={"environment": settings.ENVIRONMENT})
    yield
    logger.info("ultron_shutdown")


app = FastAPI(
    title="Ultron API",
    description="Market/SEO/Ads Intelligence API for Mercado Livre and Magalu",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connectors() -> Dict[str, BaseConnector]:
    return {
        "mercado_livre": MercadoLivreConnector(settings.ml_seller_access_token),
        "magalu": MagaluConnector(),
    }


def get_connector(marketplace: str) -> BaseConnector:
    connectors = get_connectors()
    key = _marketplace_alias(marketplace)
    if key not in connectors:
        raise HTTPException(status_code=400, detail=f"Marketplace {marketplace} not supported")
    return connectors[key]


def get_agent() -> MarketAgent:
    return MarketAgent(get_connectors())


class AnalyzeRequest(BaseModel):
    keyword: str = Field(..., min_length=2)
    marketplace: str = "mercadolivre"
    limit: int = Field(default=30, ge=1, le=100)


class AuditListingRequest(BaseModel):
    listing_id: str
    marketplace: str = "mercadolivre"
    keyword: Optional[str] = None


class OptimizeTitleRequest(BaseModel):
    product_title: str
    marketplace: str = "mercadolivre"
    category: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=10)


class CompetitorPricingRequest(BaseModel):
    product_ids: List[str] = Field(default_factory=list)
    marketplace: str = "mercadolivre"
    include_shipping: bool = True
    include_promotions: bool = True


class AdsCreateRequest(BaseModel):
    marketplace: str = "mercadolivre"
    product_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class AlertsCreateRequest(BaseModel):
    name: str
    condition: Dict[str, Any] = Field(default_factory=dict)
    listing_id: Optional[str] = None
    is_active: bool = True


class AlertsUpdateRequest(BaseModel):
    name: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


market_research_router = APIRouter(prefix="/api/market-research", tags=["market-research"])
seo_router = APIRouter(prefix="/api/seo", tags=["seo"])
ads_router = APIRouter(prefix="/api/ads", tags=["ads"])
documents_router = APIRouter(prefix="/api/documents", tags=["documents"])
reports_router = APIRouter(prefix="/api/reports", tags=["reports"])
alerts_router = APIRouter(prefix="/api/alerts", tags=["alerts"])
monitoring_router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@app.get("/")
async def root():
    return {"name": "Ultron API", "version": app.version, "status": "running"}


@app.get("/health")
async def health(cfg=Depends(get_settings)):
    return {
        "status": "healthy",
        "environment": cfg.ENVIRONMENT,
        "ai_configured": cfg.check_ai_configured(),
        "ml_configured": cfg.check_ml_configured(),
    }


@market_research_router.get("/search")
async def market_search(
    marketplace: str,
    query: str,
    category: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ctx: RequestContext = Depends(require_auth_context),
):
    listings = await function_calls.search_listings(
        query=query,
        marketplace=marketplace,
        category=category,
        limit=limit,
        offset=offset,
    )
    return {
        "workspace_id": ctx.workspace_id,
        "marketplace": _marketplace_alias(marketplace),
        "query": query,
        "count": len(listings),
        "items": listings,
    }


@market_research_router.get("/product/{product_id}")
async def market_product_details(
    product_id: str,
    marketplace: str,
    ctx: RequestContext = Depends(require_auth_context),
):
    normalized_data = await function_calls.get_listing_detail(marketplace=marketplace, listing_id=product_id)
    valid, err = validate_against_contract(normalized_data, "listing_normalized.schema.json")
    return {"workspace_id": ctx.workspace_id, "normalized": normalized_data, "contract_valid": valid, "contract_error": err}


@market_research_router.post("/competitor-pricing")
async def competitor_pricing(
    req: CompetitorPricingRequest,
    ctx: RequestContext = Depends(require_auth_context),
):
    connector = get_connector(req.marketplace)
    items: List[Dict[str, Any]] = []
    prices: List[float] = []
    for product_id in req.product_ids:
        raw = await connector.get_listing_details(product_id)
        normalized = await connector.normalize(raw)
        data = normalized.model_dump() if hasattr(normalized, "model_dump") else normalized
        items.append(data)
        if data.get("final_price_estimate"):
            prices.append(float(data["final_price_estimate"]))
    return {
        "workspace_id": ctx.workspace_id,
        "marketplace": _marketplace_alias(req.marketplace),
        "items": items,
        "stats": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": (sum(prices) / len(prices)) if prices else 0,
        },
    }


@market_research_router.get("/trends")
async def market_trends(
    marketplace: str,
    category: str,
    period: str = "30d",
    ctx: RequestContext = Depends(require_auth_context),
):
    stub = function_calls.get_trends(query=category, region="BR", timeframe=period)
    return _not_implemented_from_stub(stub)


@market_research_router.post("/analyze")
async def market_analyze(
    req: AnalyzeRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    result = await agent.research_market(
        keyword=req.keyword,
        marketplace=_marketplace_alias(req.marketplace),
        limit=req.limit,
    )
    normalized = [item.to_contract_payload() for item in result.listings]
    dashboard = generate_market_dashboard(
        normalized_listings=normalized,
        clusters={},
        metrics={
            "price_range": result.price_range,
            "competitor_summary": result.competitor_summary,
            "gaps": result.gaps,
        },
    )
    valid, err = validate_against_contract(dashboard, "report_outputs.schema.json")
    return {
        "research": result.model_dump(),
        "dashboard": dashboard,
        "contract_valid": valid,
        "contract_error": err,
    }


@seo_router.get("/keywords")
async def seo_keywords(
    marketplace: str,
    product_title: str,
    category: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50),
    ctx: RequestContext = Depends(require_auth_context),
):
    terms = [part.strip(".,;:!?").lower() for part in product_title.split() if len(part) >= 4]
    dedup = list(dict.fromkeys(terms))
    return {"workspace_id": ctx.workspace_id, "marketplace": _marketplace_alias(marketplace), "keywords": dedup[:limit]}


@seo_router.post("/analyze-listing")
async def seo_analyze_listing(
    req: AuditListingRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    result = await agent.audit_listing(
        listing_id=req.listing_id,
        marketplace=_marketplace_alias(req.marketplace),
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
        my_listing={"scores": {"seo": result.seo_score.score, "conversion": result.conversion_score.score, "competitiveness": result.competitiveness_score.score}},
        top_competitors=[],
        ruleset={"version": 1},
    )
    return {"audit": result.model_dump(), "report": audit_payload}


@seo_router.post("/optimize-title")
async def seo_optimize_title(
    req: OptimizeTitleRequest,
    ctx: RequestContext = Depends(require_auth_context),
):
    titles = await generate_titles(
        keyword=req.product_title,
        marketplace=_marketplace_alias(req.marketplace),
        n_variants=req.limit,
    )
    return {"workspace_id": ctx.workspace_id, "titles": titles}


@seo_router.get("/ranking")
async def seo_ranking(
    product_id: str,
    marketplace: str,
    keyword: str,
    ctx: RequestContext = Depends(require_auth_context),
):
    stub = function_calls.get_my_listing_performance(listing_id=product_id, metrics=["rank"], timeframe="7d")
    return _not_implemented_from_stub(stub)


@seo_router.post("/competitor-keywords")
async def seo_competitor_keywords(
    req: AnalyzeRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    research = await agent.research_market(req.keyword, _marketplace_alias(req.marketplace), limit=req.limit)
    return {"workspace_id": ctx.workspace_id, "keywords": research.top_seo_terms}


@ads_router.get("/campaigns")
async def ads_campaigns(
    marketplace: str,
    status: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(require_auth_context),
):
    return _not_implemented("ads", "/api/ads/campaigns")


@ads_router.get("/campaigns/{campaign_id}/performance")
async def ads_campaign_performance(
    campaign_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = "daily",
    ctx: RequestContext = Depends(require_auth_context),
):
    return _not_implemented("ads", f"/api/ads/campaigns/{campaign_id}/performance")


@ads_router.put("/campaigns/{campaign_id}")
async def ads_campaign_update(
    campaign_id: str,
    req: Dict[str, Any],
    ctx: RequestContext = Depends(require_auth_context),
):
    return _not_implemented("ads", f"/api/ads/campaigns/{campaign_id}")


@ads_router.get("/recommendations")
async def ads_recommendations(
    marketplace: str,
    product_id: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    return _not_implemented("ads", "/api/ads/recommendations")


@ads_router.post("/create")
async def ads_create(req: AdsCreateRequest, ctx: RequestContext = Depends(require_auth_context)):
    return _not_implemented("ads", "/api/ads/create")


@ads_router.post("/bulk-create")
async def ads_bulk_create(req: List[AdsCreateRequest], ctx: RequestContext = Depends(require_auth_context)):
    return _not_implemented("ads", "/api/ads/bulk-create")


@documents_router.post("/upload")
async def documents_upload(
    file: Optional[UploadFile] = File(default=None),
    ctx: RequestContext = Depends(require_auth_context),
):
    job_id = repository.create_job(
        workspace_id=ctx.workspace_id,
        job_type="document_upload",
        status="pending",
        result_summary={"filename": file.filename if file else None},
        supabase_jwt=ctx.token,
    )
    return {"workspace_id": ctx.workspace_id, "document_id": job_id, "status": "pending"}


@documents_router.get("/{document_id}/extract")
async def documents_extract(
    document_id: str,
    extract_type: Optional[str] = None,
    ctx: RequestContext = Depends(require_auth_context),
):
    stub = function_calls.read_pdf(file_id=document_id)
    return _not_implemented_from_stub(stub) if stub.get("status") == "not_implemented" else stub


@documents_router.post("/analyze")
async def documents_analyze(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    stub = function_calls.extract_product_specs(document_text=req.get("text", ""))
    return _not_implemented_from_stub(stub) if stub.get("status") == "not_implemented" else stub


@reports_router.post("/generate")
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


@reports_router.get("/{report_id}/status")
async def reports_status(report_id: str, ctx: RequestContext = Depends(require_auth_context)):
    job = repository.get_job(workspace_id=ctx.workspace_id, job_id=report_id, supabase_jwt=ctx.token)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found.")
    return {"workspace_id": ctx.workspace_id, "report_id": report_id, "status": job.get("status"), "result": job.get("result_summary")}


@reports_router.get("/{report_id}/download")
async def reports_download(report_id: str, ctx: RequestContext = Depends(require_auth_context)):
    return _not_implemented("reports", f"/api/reports/{report_id}/download")


@alerts_router.post("")
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


@alerts_router.get("")
async def alerts_list(ctx: RequestContext = Depends(require_auth_context)):
    return {"items": repository.list_alert_rules(workspace_id=ctx.workspace_id, supabase_jwt=ctx.token)}


@alerts_router.put("/{alert_id}")
async def alerts_update(alert_id: str, req: AlertsUpdateRequest, ctx: RequestContext = Depends(require_auth_context)):
    payload = req.model_dump(exclude_none=True)
    ok = repository.update_alert_rule(workspace_id=ctx.workspace_id, alert_id=alert_id, data=payload, supabase_jwt=ctx.token)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update alert rule.")
    return {"ok": True}


@alerts_router.delete("/{alert_id}")
async def alerts_delete(alert_id: str, ctx: RequestContext = Depends(require_auth_context)):
    ok = repository.delete_alert_rule(workspace_id=ctx.workspace_id, alert_id=alert_id, supabase_jwt=ctx.token)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete alert rule.")
    return {"ok": True}


@alerts_router.get("/events")
async def alerts_events(ctx: RequestContext = Depends(require_auth_context)):
    return {"items": repository.list_alert_events(workspace_id=ctx.workspace_id, supabase_jwt=ctx.token)}


# Monitoring compatibility aliases used by Postman collection
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


# Legacy routes compatibility
@app.post("/search")
async def legacy_search(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_search(
        marketplace=req.marketplace,
        query=req.keyword,
        category=None,
        limit=req.limit,
        offset=0,
        ctx=ctx,
    )


@app.post("/research")
async def legacy_research(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_analyze(req=req, ctx=ctx, agent=get_agent())


@app.post("/audit")
async def legacy_audit(req: AuditListingRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo_analyze_listing(req=req, ctx=ctx, agent=get_agent())


@app.post("/suggest-title")
async def legacy_suggest_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo_optimize_title(req=req, ctx=ctx)


@app.post("/validate-title")
async def legacy_validate_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    connector = get_connector(req.marketplace)
    return connector.validate_title(req.product_title)


@app.post("/generate/titles")
async def legacy_generate_titles(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo_optimize_title(req=req, ctx=ctx)


@app.post("/generate/bullets")
async def legacy_generate_bullets(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    bullets = await generate_bullets(keyword=req.keyword, marketplace=_marketplace_alias(req.marketplace), n_bullets=5)
    return {"bullets": bullets}


@app.post("/generate/description")
async def legacy_generate_description(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    description = await generate_description(keyword=req.keyword, marketplace=_marketplace_alias(req.marketplace))
    return {"description": description}


@app.post("/create-listing")
async def legacy_create_listing(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return _not_implemented("seo", "/create-listing")


@app.post("/compare")
async def legacy_compare(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return _not_implemented("market-research", "/compare")


@app.post("/operations/sync")
async def operations_sync(
    skus: List[str],
    marketplace: str = "magalu",
    ctx: RequestContext = Depends(require_auth_context),
):
    connector = get_connector(marketplace)
    results = {"synced": 0, "failed": 0, "errors": []}
    for sku in skus:
        try:
            raw = await connector.get_listing_details(sku)
            normalized = await connector.normalize(raw)
            normalized_data = normalized.model_dump() if hasattr(normalized, "model_dump") else normalized
            listing_uuid = repository.upsert_listings_current(
                workspace_id=ctx.workspace_id,
                platform=marketplace,
                external_id=sku,
                raw_data=raw,
                normalized_data=normalized_data,
                derived_data={"source": "operations_sync"},
                supabase_jwt=ctx.token,
            )
            if listing_uuid:
                repository.insert_snapshot_if_changed(
                    workspace_id=ctx.workspace_id,
                    listing_uuid=listing_uuid,
                    raw_data=raw,
                    normalized_data=normalized_data,
                    derived_data={"source": "operations_sync"},
                    supabase_jwt=ctx.token,
                )
                results["synced"] += 1
            else:
                results["failed"] += 1
        except Exception as exc:
            results["failed"] += 1
            results["errors"].append(str(exc))
    return results


app.include_router(market_research_router)
app.include_router(seo_router)
app.include_router(ads_router)
app.include_router(documents_router)
app.include_router(reports_router)
app.include_router(alerts_router)
app.include_router(monitoring_router)

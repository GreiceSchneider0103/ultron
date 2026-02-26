"""Ultron API main entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.src.auth import RequestContext, require_auth_context
from api.src.config import get_settings, settings
from api.src.functions.generator import generate_bullets, generate_description
from api.src.routers import ads, alerts, documents, market_research, reports, seo
from api.src.routers.common import not_implemented
from api.src.routers.schemas import AnalyzeRequest, AuditListingRequest, OptimizeTitleRequest
from api.src.services.marketplace import get_connector, marketplace_alias

logger = logging.getLogger(__name__)


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


# Legacy routes compatibility
@app.post("/search")
async def legacy_search(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_research.market_search(
        marketplace=req.marketplace,
        query=req.keyword,
        category=None,
        limit=req.limit,
        offset=0,
        ctx=ctx,
    )


@app.post("/research")
async def legacy_research(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await market_research.market_analyze(req=req, ctx=ctx)


@app.post("/audit")
async def legacy_audit(req: AuditListingRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_analyze_listing(req=req, ctx=ctx)


@app.post("/suggest-title")
async def legacy_suggest_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_optimize_title(req=req, ctx=ctx)


@app.post("/validate-title")
async def legacy_validate_title(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    connector = get_connector(req.marketplace)
    return connector.validate_title(req.product_title)


@app.post("/generate/titles")
async def legacy_generate_titles(req: OptimizeTitleRequest, ctx: RequestContext = Depends(require_auth_context)):
    return await seo.seo_optimize_title(req=req, ctx=ctx)


@app.post("/generate/bullets")
async def legacy_generate_bullets(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    bullets = await generate_bullets(keyword=req.keyword, marketplace=marketplace_alias(req.marketplace), n_bullets=5)
    return {"bullets": bullets}


@app.post("/generate/description")
async def legacy_generate_description(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    description = await generate_description(keyword=req.keyword, marketplace=marketplace_alias(req.marketplace))
    return {"description": description}


@app.post("/create-listing")
async def legacy_create_listing(req: AnalyzeRequest, ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("seo", "/create-listing")


@app.post("/compare")
async def legacy_compare(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    return not_implemented("market-research", "/compare")


@app.post("/operations/sync")
async def operations_sync(
    skus: List[str],
    marketplace: str = "magalu",
    ctx: RequestContext = Depends(require_auth_context),
):
    return await market_research.operations_sync_impl(skus=skus, marketplace=marketplace, ctx=ctx)


app.include_router(market_research.router)
app.include_router(seo.router)
app.include_router(ads.router)
app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(alerts.router)
app.include_router(alerts.monitoring_router)

"""Ultron API main entrypoint."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.src.auth import RequestContext, require_auth_context
from api.src.config import get_settings, settings
from api.src.db.mercado_livre import MercadoLivreRules
from api.src.functions.generator import generate_bullets, generate_description
from api.src.routers import ads, alerts, documents, images_v2, market_research, reports, seo
from api.src.routers.common import error_payload
from api.src.routers.schemas import AnalyzeRequest, AuditListingRequest, OptimizeTitleRequest
from api.src.services.monitoring_scheduler import get_scheduler_health, scheduler_loop
from api.src.services.marketplace import get_agent, get_connector, marketplace_alias

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ultron_startup", extra={"environment": settings.ENVIRONMENT})
    scheduler_stop_event: asyncio.Event | None = None
    scheduler_task: asyncio.Task | None = None
    if settings.monitor_scheduler_should_run:
        scheduler_stop_event = asyncio.Event()
        scheduler_task = asyncio.create_task(scheduler_loop(scheduler_stop_event))
        app.state.monitor_scheduler_stop_event = scheduler_stop_event
        app.state.monitor_scheduler_task = scheduler_task
    else:
        logger.info(
            "monitor_scheduler_disabled",
            extra={
                "enabled_by_config": settings.MONITOR_SCHEDULER_ENABLED,
                "environment": settings.ENVIRONMENT,
            },
        )
    yield
    if scheduler_stop_event and scheduler_task:
        scheduler_stop_event.set()
        try:
            await asyncio.wait_for(scheduler_task, timeout=5)
        except Exception:
            scheduler_task.cancel()
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


def _trace_id_from_request(request: Request) -> str | None:
    return getattr(request.state, "trace_id", None)


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or str(uuid4())
    request.state.trace_id = trace_id
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Trace-Id"] = trace_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        logger.info(
            "request_completed trace_id=%s method=%s path=%s status=%s duration_ms=%s workspace_id=%s",
            trace_id,
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            request.headers.get("x-workspace-id", ""),
        )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=error_payload(
            error_code="validation_error",
            message="Request validation failed.",
            detail=exc.errors(),
            trace_id=_trace_id_from_request(request),
        ),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail and "message" in detail:
        payload = dict(detail)
        if "trace_id" not in payload and _trace_id_from_request(request):
            payload["trace_id"] = _trace_id_from_request(request)
        return JSONResponse(status_code=exc.status_code, content=payload)

    message = detail if isinstance(detail, str) else "Request failed."
    payload = error_payload(
        error_code="http_error",
        message=message,
        detail=None if isinstance(detail, str) else detail,
        trace_id=_trace_id_from_request(request),
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content=error_payload(
            error_code="internal_error",
            message="Unexpected internal server error.",
            detail=str(exc),
            trace_id=_trace_id_from_request(request),
        ),
    )


@app.get("/")
async def root():
    return {"name": "Ultron API", "version": app.version, "status": "running"}


@app.get("/health")
async def health(cfg=Depends(get_settings)):
    scheduler_state = get_scheduler_health()
    return {
        "status": "healthy",
        "environment": cfg.ENVIRONMENT,
        "ai_configured": cfg.check_ai_configured(),
        "ml_configured": cfg.check_ml_configured(),
        "monitor_scheduler_active": scheduler_state.get("scheduler_active", False),
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
async def legacy_create_listing(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    marketplace = str(req.get("marketplace") or req.get("platform") or "mercadolivre")
    product_data = req.get("product_data") or req.get("payload") or {}
    platform_rules_id = req.get("platform_rules_id")

    if not isinstance(product_data, dict):
        raise HTTPException(status_code=400, detail="product_data must be an object.")

    keyword = str(req.get("keyword") or product_data.get("title") or product_data.get("name") or "").strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Missing keyword or product_data.title/product_data.name.")

    marketplace_key = marketplace_alias(marketplace)
    attributes = product_data.get("attributes") if isinstance(product_data.get("attributes"), dict) else {}
    structured_spec = product_data.get("structured_spec") if isinstance(product_data.get("structured_spec"), dict) else {}
    listing_attrs = structured_spec.get("listing_attributes") if isinstance(structured_spec.get("listing_attributes"), dict) else {}
    for key, value in listing_attrs.items():
        if key not in attributes or attributes.get(key) in (None, "", 0):
            attributes[key] = value
    agent = get_agent()
    generated = await agent.create_listing(keyword=keyword, marketplace=marketplace_key, attributes=attributes)

    if generated.get("error"):
        raise HTTPException(status_code=422, detail=str(generated["error"]))

    titles = generated.get("titulos") if isinstance(generated.get("titulos"), list) else []
    title = str(req.get("title") or (titles[0] if titles else product_data.get("title") or keyword)).strip()
    bullets = generated.get("bullets") if isinstance(generated.get("bullets"), list) else []
    description = generated.get("descricao") if isinstance(generated.get("descricao"), str) else ""
    if structured_spec and description:
        spec_attrs = structured_spec.get("attributes") if isinstance(structured_spec.get("attributes"), dict) else {}
        spec_parts = []
        for field in ("material", "largura_cm", "altura_cm", "profundidade_cm", "peso_kg", "densidade"):
            val = spec_attrs.get(field)
            if val is not None and val != "":
                spec_parts.append(f"{field}: {val}")
        if spec_parts:
            description = f"{description}\n\nFicha tecnica extraida: " + " | ".join(spec_parts)
    media_checklist = (
        generated.get("pauta_fotografica") if isinstance(generated.get("pauta_fotografica"), list) else []
    )
    faq = product_data.get("faq") if isinstance(product_data.get("faq"), list) else []

    connector = get_connector(marketplace)
    title_validation = connector.validate_title(title)

    mandatory_validation: dict[str, Any]
    if marketplace_key == "mercado_livre":
        ml_rules = MercadoLivreRules()
        listing_validation = ml_rules.validate_listing(
            {
                "title": title,
                "attributes": attributes,
                "category_id": product_data.get("category_id", ""),
            }
        )
        missing = [issue for issue in listing_validation.get("issues", []) if "Missing mandatory attribute" in issue]
        mandatory_validation = {
            "valid": len(missing) == 0,
            "missing": missing,
            "issues": listing_validation.get("issues", []),
        }
    else:
        required = ["cor", "material", "largura_cm", "altura_cm"]
        missing = [attr for attr in required if not attributes.get(attr)]
        mandatory_validation = {"valid": len(missing) == 0, "missing": missing}

    validation = {
        "title": title_validation,
        "mandatory_attributes": mandatory_validation,
        "is_ready": bool(title_validation.get("is_valid")) and bool(mandatory_validation.get("valid")),
    }

    return {
        "workspace_id": ctx.workspace_id,
        "marketplace": marketplace_key,
        "platform_rules_id": platform_rules_id,
        "payload": {
            "title": title,
            "bullets": bullets,
            "description": description,
            "attributes": attributes,
            "media_checklist": media_checklist,
            "faq": faq,
        },
        "validation": validation,
    }


@app.post("/compare")
async def legacy_compare(req: Dict[str, Any], ctx: RequestContext = Depends(require_auth_context)):
    marketplace = str(req.get("marketplace") or "mercadolivre")
    my_listing_id = str(req.get("my_listing_id") or req.get("listing_id") or "").strip()
    filters = req.get("filters") if isinstance(req.get("filters"), dict) else {}

    if not my_listing_id:
        raise HTTPException(status_code=400, detail="Missing my_listing_id or listing_id.")

    my_listing_resp = await market_research.market_product_details(
        product_id=my_listing_id,
        marketplace=marketplace,
        ctx=ctx,
    )
    my_listing = my_listing_resp.get("normalized") or {}
    if not my_listing:
        raise HTTPException(status_code=404, detail=f"Listing {my_listing_id} not found.")

    query = str(req.get("query") or req.get("keyword") or "").strip()
    if not query:
        title = str(my_listing.get("title") or "").strip()
        query = " ".join(title.split()[:4]) if title else my_listing_id

    limit = int(req.get("limit") or filters.get("limit") or 10)
    limit = max(1, min(limit, 20))
    offset = int(req.get("offset") or filters.get("offset") or 0)
    category = req.get("category") or filters.get("category")

    competitors_resp = await market_research.market_search(
        marketplace=marketplace,
        query=query,
        category=category,
        limit=limit,
        offset=offset,
        ctx=ctx,
    )
    raw_competitors = competitors_resp.get("items") or []

    canonical_my_id = str(my_listing.get("listing_id") or my_listing.get("id") or my_listing_id)
    competitors: list[dict[str, Any]] = []
    for item in raw_competitors:
        cid = str(item.get("listing_id") or item.get("id") or "")
        if cid and cid == canonical_my_id:
            continue
        competitors.append(
            {
                "listing_id": cid or None,
                "title": item.get("title"),
                "price": item.get("price"),
                "final_price_estimate": item.get("final_price_estimate"),
                "seller": item.get("seller"),
                "badges": item.get("badges"),
                "social_proof": item.get("social_proof"),
            }
        )

    my_price = _to_float(my_listing.get("final_price_estimate") or my_listing.get("price"))
    comp_prices = [
        _to_float(c.get("final_price_estimate") or c.get("price"))
        for c in competitors
        if _to_float(c.get("final_price_estimate") or c.get("price")) > 0
    ]

    highlights: list[str] = []
    gaps: list[str] = []
    recommendations: list[str] = []

    if comp_prices:
        avg_comp_price = sum(comp_prices) / len(comp_prices)
        delta_pct = ((my_price - avg_comp_price) / avg_comp_price * 100) if avg_comp_price else 0
        highlights.append(f"Preco do anuncio vs media dos concorrentes: {delta_pct:+.1f}%.")
        if delta_pct > 10:
            gaps.append("Preco acima da media de mercado.")
        elif delta_pct < -10:
            highlights.append("Preco competitivo abaixo da media.")

    text_blocks = my_listing.get("text_blocks") or {}
    bullets = text_blocks.get("bullets") if isinstance(text_blocks, dict) else []
    if not bullets:
        gaps.append("Anuncio sem bullets de destaque.")

    media_count = int(my_listing.get("media_count") or 0)
    if media_count < 5:
        gaps.append("Quantidade de imagens abaixo do recomendado (5+).")

    try:
        audit_result = await seo.seo_analyze_listing(
            req=AuditListingRequest(listing_id=my_listing_id, marketplace=marketplace, keyword=query),
            ctx=ctx,
            agent=get_agent(),
        )
        report = audit_result.get("report") if isinstance(audit_result, dict) else {}
        recommendations = [str(item) for item in (report.get("recommendations") or [])][:10]
    except Exception:
        recommendations = []

    if not recommendations:
        recommendations = [
            "Revisar titulo com keyword principal e limite da plataforma.",
            "Completar atributos obrigatorios da categoria.",
            "Aumentar cobertura de imagens e prova social.",
        ]

    diff_report = {
        "highlights": highlights,
        "gaps": gaps,
        "recommendations": recommendations,
        "competitors": competitors,
    }

    return {
        "workspace_id": ctx.workspace_id,
        "marketplace": marketplace_alias(marketplace),
        "my_listing_id": canonical_my_id,
        "query": query,
        "diff_report": diff_report,
    }


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
app.include_router(images_v2.router)

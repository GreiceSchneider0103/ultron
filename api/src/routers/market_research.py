from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from api.src.auth import RequestContext, require_auth_context
from api.src.contracts.validator import validate_against_contract
from api.src.db import repository
from api.src.functions import function_calls
from api.src.orchestrator.agent import MarketAgent
from api.src.reports.market_dashboard import generate_market_dashboard
from api.src.routers.common import not_implemented
from api.src.routers.schemas import AnalyzeRequest, CompetitorPricingRequest
from api.src.services.marketplace import get_agent, get_connector, marketplace_alias

router = APIRouter(prefix="/api/market-research", tags=["market-research"])


@router.get("/search")
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
        "marketplace": marketplace_alias(marketplace),
        "query": query,
        "count": len(listings),
        "items": listings,
    }


@router.get("/product/{product_id}")
async def market_product_details(
    product_id: str,
    marketplace: str,
    ctx: RequestContext = Depends(require_auth_context),
):
    normalized_data = await function_calls.get_listing_detail(marketplace=marketplace, listing_id=product_id)
    contract_valid = True
    contract_error = None
    try:
        validate_against_contract(normalized_data, "listing_normalized.schema.json")
    except Exception as exc:
        contract_valid = False
        contract_error = str(exc)
    return {"workspace_id": ctx.workspace_id, "normalized": normalized_data, "contract_valid": contract_valid, "contract_error": contract_error}


@router.post("/competitor-pricing")
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
        "marketplace": marketplace_alias(req.marketplace),
        "items": items,
        "stats": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": (sum(prices) / len(prices)) if prices else 0,
        },
    }


@router.get("/trends")
async def market_trends(
    marketplace: str,
    category: str,
    period: str = "30d",
    ctx: RequestContext = Depends(require_auth_context),
):
    return not_implemented("market-research", "/api/market-research/trends")


@router.post("/analyze")
async def market_analyze(
    req: AnalyzeRequest,
    ctx: RequestContext = Depends(require_auth_context),
    agent: MarketAgent = Depends(get_agent),
):
    result = await agent.research_market(
        keyword=req.keyword,
        marketplace=marketplace_alias(req.marketplace),
        limit=req.limit,
    )
    normalized = [item.to_contract_payload() for item in result.listings]
    dashboard = generate_market_dashboard(
        listings=normalized,
        price_range=result.price_range,
        competitor_summary=result.competitor_summary,
    )
    valid = True
    err = None
    try:
        validate_against_contract({"market_dashboard": dashboard}, "report_outputs.schema.json")
    except Exception as exc:
        valid = False
        err = str(exc)
    return {
        "research": result.model_dump(),
        "dashboard": dashboard,
        "contract_valid": valid,
        "contract_error": err,
    }


async def operations_sync_impl(
    skus: List[str],
    marketplace: str,
    ctx: RequestContext,
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

from __future__ import annotations

from typing import Any, Literal, Optional

from api.src.connectors.magalu import MagaluConnector
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.reports import (
    generate_ab_test_plan as _generate_ab_test_plan,
    generate_action_plan as _generate_action_plan,
    generate_audit_report as _generate_audit_report,
    generate_market_dashboard as _generate_market_dashboard,
)
from api.src.types.listing import ListingNormalized


def _not_implemented(reason: str, todo: list[str]) -> dict[str, Any]:
    return {"status": "not_implemented", "reason": reason, "todo": todo}


def _get_connector(marketplace: str):
    if marketplace in {"mercadolivre", "mercado_livre", "meli"}:
        return MercadoLivreConnector()
    return MagaluConnector()


async def search_listings(
    query: str,
    marketplace: str,
    category: Optional[str] = None,
    filters: Optional[dict[str, Any]] = None,
    sort: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    connector = _get_connector(marketplace)
    items = await connector.search_and_normalize(query=query, category_id=category, limit=limit, offset=offset)
    return [i.to_contract_payload() if isinstance(i, ListingNormalized) else i for i in items]


async def get_listing_detail(marketplace: str, listing_id: str) -> dict[str, Any]:
    connector = _get_connector(marketplace)
    raw = await connector.get_listing_details(listing_id)
    normalized = await connector.normalize(raw)
    return normalized.to_contract_payload() if isinstance(normalized, ListingNormalized) else raw


async def get_seller_profile(marketplace: str, seller_id: str) -> dict[str, Any]:
    connector = _get_connector(marketplace)
    if hasattr(connector, "get_seller_details"):
        return await connector.get_seller_details(seller_id)
    return _not_implemented("seller_profile_unavailable", ["Implement seller endpoint for this marketplace connector."])


async def get_category_attributes(marketplace: str, category_id: str) -> dict[str, Any]:
    return _not_implemented("category_attributes_not_connected", ["Integrate marketplace category attributes endpoint."])


async def get_top_sellers(category_or_query: str, marketplace: str, limit: int = 10) -> dict[str, Any]:
    return _not_implemented("top_sellers_not_connected", ["Aggregate sellers by volume/reviews from search_listings results."])


def extract_keywords_from_listings(listings: list[dict[str, Any]]) -> list[str]:
    terms: list[str] = []
    for item in listings:
        terms.extend(item.get("seo_terms", []))
    return list(dict.fromkeys([t for t in terms if len(t) > 2]))


def cluster_keywords(keywords: list[str], method: Literal["prefix", "simple"] = "simple") -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = {}
    for kw in keywords:
        key = kw[:3] if method == "prefix" else kw.split(" ")[0]
        clusters.setdefault(key, []).append(kw)
    return clusters


def suggest_title_patterns(category: str, top_listings: list[dict[str, Any]]) -> list[str]:
    titles = [item.get("title", "") for item in top_listings if item.get("title")]
    return [f"{category}: {t[:60]}" for t in titles[:5]]


def get_trends(query: str, region: str, timeframe: str) -> dict[str, Any]:
    return _not_implemented("trends_not_connected", ["Integrate Google Trends connector."])


def get_my_listings(marketplace: str, filters: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return _not_implemented("my_listings_not_connected", ["Integrate seller account listing APIs."])


def get_my_listing_performance(listing_id: str, metrics: list[str], timeframe: str) -> dict[str, Any]:
    return _not_implemented("my_listing_performance_not_connected", ["Integrate ads/analytics metrics sources."])


def compare_my_vs_market(my_listing: dict[str, Any], competitor_set: list[dict[str, Any]]) -> dict[str, Any]:
    my_price = my_listing.get("final_price_estimate") or my_listing.get("price", 0)
    competitor_prices = [c.get("final_price_estimate") or c.get("price", 0) for c in competitor_set if c.get("price") is not None]
    avg_market = (sum(competitor_prices) / len(competitor_prices)) if competitor_prices else 0
    return {
        "my_price": my_price,
        "market_avg_price": avg_market,
        "delta_pct": ((my_price - avg_market) / avg_market * 100) if avg_market else 0,
    }


def read_pdf(file_id: str) -> dict[str, Any]:
    return _not_implemented("pdf_pipeline_not_implemented", ["Implement OCR and table extraction for uploaded files."])


def extract_product_specs(document_text: str) -> dict[str, Any]:
    return _not_implemented("spec_extraction_not_implemented", ["Implement NLP extractor for specs."])


def match_catalog_product_to_listing(specs: dict[str, Any], listings: list[dict[str, Any]]) -> dict[str, Any]:
    return _not_implemented("catalog_matching_not_implemented", ["Implement semantic matching for specs vs listings."])


def analyze_listing_images(image_urls: list[str]) -> dict[str, Any]:
    return _not_implemented("image_analysis_not_implemented", ["Implement image quality and coverage checks."])


def detect_objects_and_scenes(image: str) -> dict[str, Any]:
    return _not_implemented("object_detection_not_implemented", ["Integrate CV model for object/scene detection."])


def score_image_set(image_analysis: dict[str, Any]) -> dict[str, Any]:
    return _not_implemented("image_scoring_not_implemented", ["Define image score rubric and compute score."])


def generate_market_dashboard(normalized_listings: list[dict[str, Any]], clusters: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return _generate_market_dashboard(normalized_listings=normalized_listings, clusters=clusters, metrics=metrics)


def generate_audit_report(my_listing: dict[str, Any], top_competitors: list[dict[str, Any]], ruleset: dict[str, Any]) -> dict[str, Any]:
    return _generate_audit_report(my_listing=my_listing, top_competitors=top_competitors, ruleset=ruleset)


def generate_action_plan(findings: dict[str, Any], constraints: dict[str, Any]) -> dict[str, Any]:
    return _generate_action_plan(findings=findings, constraints=constraints)


def generate_ab_test_plan(hypotheses: list[dict[str, Any]], priority_rules: dict[str, Any]) -> dict[str, Any]:
    return _generate_ab_test_plan(hypotheses=hypotheses, priority_rules=priority_rules)


def create_listing_from_scratch(specs: dict[str, Any], keyword_pack: list[str], ruleset: dict[str, Any]) -> dict[str, Any]:
    return _not_implemented("create_listing_from_scratch_not_implemented", ["Bridge generator output with ruleset and marketplace constraints."])

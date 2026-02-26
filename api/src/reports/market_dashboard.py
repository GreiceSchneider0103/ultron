from __future__ import annotations

from typing import Any


def generate_market_dashboard(normalized_listings: list[dict], clusters: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    attribute_map: dict[str, dict[str, int]] = {"cor": {}, "material": {}}
    for row in normalized_listings:
        attrs = row.get("attributes", {})
        cor = attrs.get("cor")
        material = attrs.get("material")
        if cor:
            attribute_map["cor"][cor] = attribute_map["cor"].get(cor, 0) + 1
        if material:
            attribute_map["material"][material] = attribute_map["material"].get(material, 0) + 1

    return {
        "price_range": metrics.get("price_range", {}),
        "competitor_summary": metrics.get("competitor_summary", {}),
        "attribute_map": attribute_map,
        "gaps": metrics.get("gaps", []),
        "clusters": clusters,
    }

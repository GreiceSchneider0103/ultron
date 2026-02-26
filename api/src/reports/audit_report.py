from __future__ import annotations

from typing import Any


def generate_audit_report(my_listing: dict[str, Any], top_competitors: list[dict[str, Any]], ruleset: dict[str, Any]) -> dict[str, Any]:
    scores = my_listing.get("scores", {})
    recommendations = my_listing.get("recommendations", [])
    weak_points = []
    if scores:
        for key, value in scores.items():
            if isinstance(value, (int, float)) and value < 70:
                weak_points.append(f"{key} below target: {value}")

    return {
        "scores": scores,
        "weak_points": weak_points,
        "recommendations": recommendations,
        "competitor_count": len(top_competitors),
        "ruleset_version": ruleset.get("version"),
    }

from __future__ import annotations

from typing import Any


def decide_margin_strategy(
    cost: float,
    min_margin_pct: float,
    shipping_cost: float,
    commission_pct: float,
    lead_time_days: int,
    target_price: float,
) -> dict[str, Any]:
    total_cost = cost + shipping_cost + (target_price * commission_pct / 100)
    margin_pct = ((target_price - total_cost) / max(target_price, 1)) * 100
    mode = "compete_by_value"
    if margin_pct >= min_margin_pct and lead_time_days <= 3:
        mode = "compete_by_price"

    floor_price = total_cost / max(1 - (min_margin_pct / 100), 0.01)
    return {
        "strategy": mode,
        "estimated_margin_pct": round(margin_pct, 2),
        "price_limits": {
            "floor_price": round(floor_price, 2),
            "target_price": round(target_price, 2),
        },
    }

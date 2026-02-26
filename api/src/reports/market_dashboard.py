from __future__ import annotations


def generate_market_dashboard(listings: list, price_range: dict, competitor_summary: dict) -> dict:
    """Stub de dashboard. Retorna estrutura mínima compatível com o contrato."""
    return {
        "type": "market_dashboard",
        "listings_count": len(listings),
        "price_range": price_range,
        "competitor_summary": competitor_summary,
    }

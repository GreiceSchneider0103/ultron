from __future__ import annotations

from typing import Dict

from fastapi import HTTPException

from api.src.config import settings
from api.src.connectors.base import BaseConnector
from api.src.connectors.magalu import MagaluConnector
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.orchestrator.agent import MarketAgent


def marketplace_alias(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"mercadolivre", "mercado_livre", "meli"}:
        return "mercado_livre"
    if normalized in {"magalu", "magazine_luiza"}:
        return "magalu"
    raise HTTPException(status_code=400, detail=f"Unsupported marketplace: {value}")


def get_connectors() -> Dict[str, BaseConnector]:
    return {
        "mercado_livre": MercadoLivreConnector(settings.ml_seller_access_token),
        "magalu": MagaluConnector(),
    }


def get_connector(marketplace: str) -> BaseConnector:
    connectors = get_connectors()
    key = marketplace_alias(marketplace)
    if key not in connectors:
        raise HTTPException(status_code=400, detail=f"Marketplace {marketplace} not supported")
    return connectors[key]


def get_agent() -> MarketAgent:
    return MarketAgent(get_connectors())

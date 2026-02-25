"""
Orquestrador — MarketAgent.

Coordena todo o fluxo:
  objetivo → coleta → normaliza → pontua → recomenda → gera relatório

Fluxos disponíveis:
  1. research_market()    → Pesquisa de mercado completa
  2. audit_listing()      → Auditoria de anúncio existente
  3. create_listing()     → Gerar anúncio do zero
  4. compare_listings()   → Comparar dois anúncios
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
import structlog

from api.src.config import get_settings
from api.src.connectors.base import BaseConnector
from api.src.connectors.mercado_livre import MercadoLivreConnector
from api.src.connectors.magalu import MagaluConnector
from api.src.pipeline.pipeline import DataPipeline
from api.src.scoring.seo import SEOScorer
from api.src.scoring.conversion import ConversionScorer, CompetitivenessScorer
from api.src.functions.generator import (
    generate_titles,
    generate_bullets,
    generate_description,
    generate_full_listing,
    generate_audit_recommendations,
)
from api.src.types.listing import (
    ListingAuditResult,
    ListingNormalized,
    Marketplace,
    MarketResearchResult,
)

log = structlog.get_logger()
settings = get_settings()


def _get_connectors() -> dict[str, BaseConnector]:
    connectors: dict[str, BaseConnector] = {
        "mercado_livre": MercadoLivreConnector(),
        "magalu": MagaluConnector(),
    }
    return connectors


class MarketAgent:
    """
    Agente principal. Instância única por request (stateless por design).
    """

    def __init__(self, connectors: Optional[dict[str, BaseConnector]] = None):
        self.connectors = connectors or _get_connectors()
        self.pipeline = DataPipeline()
        self.seo_scorer = SEOScorer()
        self.conv_scorer = ConversionScorer()
        self.comp_scorer = CompetitivenessScorer()

    # ── 1. Pesquisa de Mercado ────────────────────────────────

    async def research_market(
        self,
        keyword: str,
        marketplace: str = "mercado_livre",
        limit: int = 50,
    ) -> MarketResearchResult:
        """
        Coleta top anúncios → normaliza → agrega métricas → retorna resultado.
        """
        connector = self._get_connector(marketplace)
        mp_enum = Marketplace(marketplace)

        log.info("research_start", keyword=keyword, marketplace=marketplace)

        # Coleta e normalização via conector
        listings: list[ListingNormalized] = await connector.search_and_normalize(
            query=keyword,
            limit=limit,
        )

        if not listings:
            log.warning("no_listings_found", keyword=keyword)
            return MarketResearchResult(
                keyword=keyword,
                marketplace=mp_enum,
                total_collected=0,
                listings=[],
                price_range={"min": 0, "max": 0, "avg": 0, "median": 0},
                top_seo_terms=[],
                competitor_summary={},
                gaps=[],
            )

        # Pipeline: dedup + enrich + aggregate
        result = await self.pipeline.run(
            raw_listings=listings,
            keyword=keyword,
            marketplace=mp_enum,
            save=False,  # sem Supabase por enquanto
        )

        log.info(
            "research_done",
            keyword=keyword,
            total=result.total_collected,
            gaps=len(result.gaps),
        )
        return result

    # ── 2. Auditoria de Anúncio ───────────────────────────────

    async def audit_listing(
        self,
        listing_id: str,
        marketplace: str = "mercado_livre",
        keyword: Optional[str] = None,
        my_listing: Optional[ListingNormalized] = None,
    ) -> ListingAuditResult:
        """
        Audita um anúncio vs top concorrentes.
        Pode receber o objeto pronto (my_listing) ou buscar pelo listing_id.
        """
        connector = self._get_connector(marketplace)
        mp_enum = Marketplace(marketplace)

        # Busca anúncio se não fornecido
        if my_listing is None:
            raw = await connector.get_listing_details(listing_id)
            my_listing = await connector.normalize(raw)

        kw = keyword or my_listing.title.split()[:4]
        kw_str = keyword or " ".join(my_listing.title.split()[:4])

        # Busca concorrentes
        research = await self.research_market(kw_str, marketplace, limit=30)
        competitors = research.listings[:20]
        top_terms = [item["term"] for item in research.top_seo_terms[:15]]

        # Scores
        seo = self.seo_scorer.score(my_listing, competitors)
        conv = self.conv_scorer.score(my_listing, competitors)
        comp = self.comp_scorer.score(my_listing, competitors)

        overall = round(seo.score * 0.35 + conv.score * 0.40 + comp.score * 0.25, 1)

        # Geração de texto com IA
        titles = await generate_titles(
            keyword=kw_str,
            marketplace=marketplace,
            attributes=my_listing.attributes.model_dump(exclude_none=True),
            top_terms=top_terms,
        )

        ai_recs = {}
        if settings.check_ai_configured():
            ai_recs = await generate_audit_recommendations(
                listing=my_listing,
                competitors=competitors,
                seo_score=seo.score,
                conversion_score=conv.score,
                top_seo_terms=top_terms,
            )

        top_actions = (
            [a["acao"] for a in ai_recs.get("acoes", [])[:10]]
            if ai_recs
            else seo.suggestions[:5] + conv.suggestions[:3] + comp.suggestions[:2]
        )

        return ListingAuditResult(
            listing_id=listing_id,
            marketplace=mp_enum,
            seo_score=seo,
            conversion_score=conv,
            competitiveness_score=comp,
            overall_score=overall,
            top_actions=top_actions,
            generated_titles=titles,
        )

    # ── 3. Criar Anúncio do Zero ──────────────────────────────

    async def create_listing(
        self,
        keyword: str,
        marketplace: str = "mercado_livre",
        attributes: Optional[dict] = None,
    ) -> dict:
        """
        Gera anúncio completo (títulos, bullets, descrição, keywords ADS,
        pauta fotográfica, sugestão de preço e ideias de A/B test).
        """
        if not settings.check_ai_configured():
            return {
                "error": "IA não configurada. Defina OPENAI_API_KEY ou ANTHROPIC_API_KEY no .env"
            }

        # Coleta contexto de mercado
        research = await self.research_market(keyword, marketplace, limit=30)
        top_terms = [item["term"] for item in research.top_seo_terms[:15]]

        result = await generate_full_listing(
            keyword=keyword,
            marketplace=marketplace,
            attributes=attributes,
            top_terms=top_terms,
            price_range=research.price_range,
        )

        result["market_context"] = {
            "keyword": keyword,
            "total_competitors": research.total_collected,
            "price_range": research.price_range,
            "top_seo_terms": top_terms,
            "gaps": research.gaps,
        }

        return result

    # ── 4. Comparar dois anúncios ─────────────────────────────

    async def compare_listings(
        self,
        listing_id_a: str,
        listing_id_b: str,
        marketplace: str = "mercado_livre",
    ) -> dict:
        connector = self._get_connector(marketplace)

        raw_a, raw_b = await asyncio.gather(
            connector.get_listing_details(listing_id_a),
            connector.get_listing_details(listing_id_b),
        )
        listing_a = await connector.normalize(raw_a)
        listing_b = await connector.normalize(raw_b)

        seo_a = self.seo_scorer.score(listing_a)
        seo_b = self.seo_scorer.score(listing_b)
        conv_a = self.conv_scorer.score(listing_a)
        conv_b = self.conv_scorer.score(listing_b)

        return {
            "listing_a": {
                "id": listing_id_a,
                "title": listing_a.title,
                "price": listing_a.price,
                "seo_score": seo_a.score,
                "conv_score": conv_a.score,
            },
            "listing_b": {
                "id": listing_id_b,
                "title": listing_b.title,
                "price": listing_b.price,
                "seo_score": seo_b.score,
                "conv_score": conv_b.score,
            },
            "winner": listing_id_a if (seo_a.score + conv_a.score) > (seo_b.score + conv_b.score) else listing_id_b,
        }

    # ── Helpers ───────────────────────────────────────────────

    def _get_connector(self, marketplace: str) -> BaseConnector:
        connector = self.connectors.get(marketplace)
        if not connector:
            raise ValueError(
                f"Connector '{marketplace}' não encontrado. "
                f"Disponíveis: {list(self.connectors.keys())}"
            )
        return connector
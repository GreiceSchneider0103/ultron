"""
pipeline/pipeline.py — Pipeline de dados do Ultron.
COLOQUE EM: api/src/pipeline/pipeline.py
Crie também: api/src/pipeline/__init__.py (arquivo vazio)

Fluxo:
  list[ListingNormalized]
    → Deduplicator   (remove duplicatas por marketplace+id)
    → Enricher       (expande seo_terms, corrige final_price)
    → MarketAggregator (métricas: price_range, top_terms, gaps)
    → (SupabaseStorage — opcional, ativado via save=True)
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Optional

import structlog

from api.src.types.listing import (
    ListingNormalized,
    Marketplace,
    MarketResearchResult,
)

log = structlog.get_logger()


# ── 1. Deduplicador ───────────────────────────────────────────

class Deduplicator:
    @staticmethod
    def _title_key(title: str) -> str:
        return " ".join((title or "").lower().replace("-", " ").split())

    @staticmethod
    def run(listings: list[ListingNormalized]) -> list[ListingNormalized]:
        seen: set[str] = set()
        seen_title_keys: set[str] = set()
        unique: list[ListingNormalized] = []
        for item in listings:
            key = f"{item.marketplace.value}:{item.listing_id}"
            title_key = Deduplicator._title_key(item.title)
            if key in seen:
                continue
            if title_key and title_key in seen_title_keys:
                continue
            seen.add(key)
            if title_key:
                seen_title_keys.add(title_key)
            unique.append(item)
        removed = len(listings) - len(unique)
        if removed:
            log.info("dedup_removed", count=removed)
        return unique


# ── 2. Enricher ───────────────────────────────────────────────

class Enricher:
    STOP_WORDS = {
        "com", "para", "por", "que", "sem", "uma", "uns", "umas",
        "como", "mais", "mas", "seu", "sua", "dos", "das", "num",
        "numa", "este", "essa", "isso", "aqui", "pode", "seus",
    }

    def run(self, listings: list[ListingNormalized]) -> list[ListingNormalized]:
        return [self._enrich(l) for l in listings]

    def _enrich(self, listing: ListingNormalized) -> ListingNormalized:
        if len(listing.seo_terms) < 3:
            listing.seo_terms = self._extract_terms(listing)
        if listing.final_price_estimate == 0:
            listing.final_price_estimate = listing.price + listing.shipping_cost
        return listing

    def _extract_terms(self, listing: ListingNormalized) -> list[str]:
        sources = [listing.title]
        sources.extend(listing.text_blocks.bullets)
        if listing.text_blocks.descricao:
            sources.append(listing.text_blocks.descricao[:500])

        attrs = listing.attributes
        for val in [attrs.cor, attrs.material, attrs.tipo_produto, attrs.tecido]:
            if val:
                sources.append(val)

        text = " ".join(sources).lower()
        words = [
            w.strip(".,;:!?\"'()-/")
            for w in text.split()
            if len(w) > 3 and w not in self.STOP_WORDS
        ]
        freq = Counter(words)
        return [w for w, _ in freq.most_common(30)]


# ── 3. Aggregator ─────────────────────────────────────────────

class MarketAggregator:

    def aggregate(
        self,
        listings: list[ListingNormalized],
        keyword: str,
        marketplace: Marketplace,
    ) -> MarketResearchResult:
        prices = [l.price for l in listings if l.price > 0]
        price_range = {
            "min": round(min(prices), 2) if prices else 0,
            "max": round(max(prices), 2) if prices else 0,
            "avg": round(sum(prices) / len(prices), 2) if prices else 0,
            "median": self._median(prices),
        }

        all_terms: list[str] = []
        for l in listings:
            all_terms.extend(l.seo_terms)
        top_seo_terms = [
            {"term": t, "freq": f}
            for t, f in Counter(all_terms).most_common(30)
        ]

        return MarketResearchResult(
            keyword=keyword,
            marketplace=marketplace,
            total_collected=len(listings),
            listings=listings,
            price_range=price_range,
            top_seo_terms=top_seo_terms,
            competitor_summary=self._competitor_summary(listings),
            gaps=self._detect_gaps(listings, prices),
        )

    @staticmethod
    def _median(values: list[float]) -> float:
        if not values:
            return 0
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return round((s[mid - 1] + s[mid]) / 2 if n % 2 == 0 else s[mid], 2)

    @staticmethod
    def _competitor_summary(listings: list[ListingNormalized]) -> dict:
        total = len(listings)
        if total == 0:
            return {}
        return {
            "total_analyzed": total,
            "frete_gratis_pct": round(
                sum(1 for l in listings if l.badges.frete_gratis) / total * 100, 1
            ),
            "full_pct": round(
                sum(1 for l in listings if l.badges.full) / total * 100, 1
            ),
            "ads_pct": round(
                sum(1 for l in listings if l.badges.anuncio_patrocinado) / total * 100, 1
            ),
            "avg_media_count": round(
                sum(l.media_count for l in listings) / total, 1
            ),
            "avg_reviews": round(
                sum(l.social_proof.avaliacoes_total for l in listings) / total, 1
            ),
            "avg_rating": round(
                sum(l.social_proof.nota_media for l in listings) / total, 2
            ),
        }

    @staticmethod
    def _detect_gaps(listings: list[ListingNormalized], prices: list[float]) -> list[dict]:
        if not prices:
            return []
        gaps = []
        avg = sum(prices) / len(prices)
        total = len(listings)

        cheap = [l for l in listings if l.price < avg * 0.7]
        if len(cheap) < 3:
            gaps.append({
                "type": "price_gap",
                "label": "Segmento econômico pouco explorado",
                "description": f"Menos de 3 anúncios abaixo de R$ {avg*0.7:.0f}",
                "opportunity": "Versão econômica pode capturar demanda reprimida.",
            })

        if sum(1 for l in listings if not l.badges.frete_gratis) > total * 0.6:
            gaps.append({
                "type": "shipping_gap",
                "label": "Maioria cobra frete",
                "description": f"Mais de 60% dos anúncios cobram frete",
                "opportunity": "Frete grátis pode ser diferencial decisivo de conversão.",
            })

        if sum(1 for l in listings if l.media_count < 5) > total * 0.5:
            gaps.append({
                "type": "content_gap",
                "label": "Anúncios com poucas fotos",
                "description": "Maioria tem < 5 imagens",
                "opportunity": "Galeria completa (8+ fotos) se destaca visualmente.",
            })

        return gaps


# ── 4. Storage Supabase ───────────────────────────────────────

class SupabaseStorage:
    """
    Persiste listings no Supabase.
    Usa o supabase_client já existente no repo (src/supabase_client.py).
    """

    def __init__(self, db):
        self.db = db  # supabase client já inicializado

    async def upsert_listings(self, listings: list[ListingNormalized]) -> int:
        rows = [self._to_row(l) for l in listings]
        try:
            result = (
                self.db.table("listings")
                .upsert(rows, on_conflict="marketplace,listing_id")
                .execute()
            )
            saved = len(result.data or [])
            log.info("storage_upsert", saved=saved)
            return saved
        except Exception as exc:
            log.error("storage_error", error=str(exc))
            return 0

    @staticmethod
    def _to_row(l: ListingNormalized) -> dict:
        return {
            "marketplace": l.marketplace.value,
            "listing_id": l.listing_id,
            "url": l.url,
            "title": l.title,
            "price": l.price,
            "price_original": l.price_original,
            "shipping_cost": l.shipping_cost,
            "final_price_estimate": l.final_price_estimate,
            "seller_id": l.seller.seller_id,
            "seller_name": l.seller.nome,
            "seller_reputation": l.seller.reputacao.value,
            "review_count": l.social_proof.avaliacoes_total,
            "rating": l.social_proof.nota_media,
            "media_count": l.media_count,
            "badges": l.badges.model_dump(),
            "attributes": l.attributes.model_dump(exclude_none=True),
            "seo_terms": l.seo_terms,
            "scraped_at": l.scraped_at.isoformat(),
        }


# ── 5. Facade — DataPipeline ───────────────────────────────────

class DataPipeline:
    """
    Use assim no agent.py:
        pipeline = DataPipeline()
        result = await pipeline.run(raw_listings, keyword, marketplace)
    """

    def __init__(self, storage: Optional[SupabaseStorage] = None):
        self.dedup = Deduplicator()
        self.enricher = Enricher()
        self.aggregator = MarketAggregator()
        self.storage = storage

    async def run(
        self,
        raw_listings: list[ListingNormalized],
        keyword: str,
        marketplace: Marketplace,
        save: bool = False,
    ) -> MarketResearchResult:
        unique = self.dedup.run(raw_listings)
        enriched = self.enricher.run(unique)
        result = self.aggregator.aggregate(enriched, keyword, marketplace)
        if save and self.storage:
            await self.storage.upsert_listings(enriched)
        return result

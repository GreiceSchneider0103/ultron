"""
Connector Magalu — Scraping HTTP controlado com headers de browser.

A Magalu não oferece API pública para parceiros externos.
Este conector usa a API interna do site (endpoints JSON não documentados,
mas estáveis) com delay configurável para não gerar bloqueio.

Rate limit sugerido: 1,5 s entre requisições (configurável via MAGALU_SCRAPING_DELAY_MS).
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Optional
import structlog

from api.src.config import get_settings
from api.src.connectors.base import BaseConnector
from api.src.utils.measurements import parse_length_to_cm
from api.src.types.listing import (
    Badges, ListingAttributes, ListingNormalized, Marketplace,
    MediaItem, MediaType, Seller, SellerReputation,
    SocialProof, TextBlocks,
)

log = structlog.get_logger()
settings = get_settings()


class MagaluConnector(BaseConnector):
    marketplace_name = "magalu"

    # Endpoints internos do site — suficientemente estáveis
    SEARCH_URL = "https://www.magazineluiza.com.br/busca/{query}/"
    SEARCH_API = "https://www.magazineluiza.com.br/busca/{query}/?page={page}&go=0"
    PRODUCT_API = "https://www.magazineluiza.com.br/{slug}/p/{sku}/"

    def __init__(self):
        delay_ms = settings.magalu_scraping_delay_ms
        super().__init__()
        self.rate_limit_delay = delay_ms / 1000

    def _default_headers(self) -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.magazineluiza.com.br/",
            "sec-ch-ua-platform": '"Windows"',
        }

    # ── Busca ─────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        category_id: Optional[str] = None,
        limit: int = 48,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Usa o endpoint de busca do Magalu.
        Retorna lista de produtos em formato normalizado internamente.
        """
        slug = query.lower().replace(" ", "%20")
        page = (offset // 48) + 1
        url = self.SEARCH_API.format(query=slug, page=page)

        try:
            html = await self._get_html(url)
            return self._parse_search_html(html, limit)
        except Exception as exc:
            log.error("magalu_search_error", error=str(exc), query=query)
            return []

    async def get_listing_details(self, listing_id: str) -> dict[str, Any]:
        """
        Busca dados completos de um produto pelo SKU/ID.
        O Magalu usa URLs no formato /produto-nome/p/IDSKU/
        """
        # listing_id deve ser o SKU (ex: "232671800")
        api_url = f"https://www.magazineluiza.com.br/produto/{listing_id}/"
        try:
            html = await self._get_html(api_url)
            return self._parse_product_html(html, listing_id)
        except Exception as exc:
            log.error("magalu_detail_error", error=str(exc), id=listing_id)
            return {}

    async def get_seller_details(self, seller_id: str) -> dict[str, Any]:
        """Magalu não expõe perfil público de seller via API."""
        return {"seller_id": seller_id, "nome": "Magalu / Parceiro"}

    # ── Normalização ──────────────────────────────────────────

    async def normalize(self, raw: dict[str, Any]) -> ListingNormalized:
        price = float(raw.get("price") or 0)
        shipping = 0.0 if raw.get("free_shipping") else float(raw.get("shipping_cost") or 0)

        seller = Seller(
            seller_id=raw.get("seller_id", "magalu"),
            nome=raw.get("seller_name", "Magazine Luiza"),
            reputacao=SellerReputation.GOLD,  # Magalu marketplace parceiros variam
        )

        attributes = self._extract_attributes(raw.get("attributes", {}))
        badges = self._extract_badges(raw)
        media = self._extract_media(raw.get("images", []))
        text_blocks = TextBlocks(
            bullets=raw.get("bullets", []),
            descricao=raw.get("description"),
        )
        seo_terms = self._extract_seo_terms(raw.get("title", ""))

        return ListingNormalized(
            marketplace=Marketplace.MAGALU,
            listing_id=raw.get("sku", raw.get("id", "")),
            url=raw.get("url", ""),
            price=price,
            price_original=raw.get("original_price"),
            shipping_cost=shipping,
            final_price_estimate=price + shipping,
            installments_max=raw.get("installments_max"),
            installments_value=raw.get("installments_value"),
            category_path=raw.get("category_path", []),
            title=raw.get("title", ""),
            attributes=attributes,
            text_blocks=text_blocks,
            media=media,
            media_count=len(media),
            seller=seller,
            social_proof=SocialProof(
                avaliacoes_total=raw.get("review_count", 0),
                nota_media=float(raw.get("rating") or 0),
            ),
            badges=badges,
            seo_terms=seo_terms,
            scraped_at=datetime.utcnow(),
        )

    # ── Parsers HTML internos ──────────────────────────────────

    async def _get_html(self, url: str) -> str:
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_search_html(self, html: str, limit: int) -> list[dict]:
        """
        Extrai dados de produtos do HTML da página de busca.
        O Magalu embute JSON no script __NEXT_DATA__.
        """
        results = []
        # Extrai __NEXT_DATA__ JSON
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            log.warning("magalu_no_next_data")
            return results

        import json
        try:
            data = json.loads(match.group(1))
            # Caminho típico no NEXT_DATA do Magalu
            props = data.get("props", {}).get("pageProps", {})
            search_data = (
                props.get("data", {})
                .get("search", {})
                .get("products", [])
            )
            for item in search_data[:limit]:
                results.append(self._flatten_search_item(item))
        except (json.JSONDecodeError, KeyError) as exc:
            log.error("magalu_parse_error", error=str(exc))

        return results

    def _parse_product_html(self, html: str, sku: str) -> dict:
        """Extrai detalhes do produto do __NEXT_DATA__."""
        import json
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return {"sku": sku}
        try:
            data = json.loads(match.group(1))
            product = (
                data.get("props", {})
                .get("pageProps", {})
                .get("data", {})
                .get("product", {})
            )
            product["sku"] = sku
            return product
        except Exception:
            return {"sku": sku}

    @staticmethod
    def _flatten_search_item(item: dict) -> dict:
        """Converte item do formato Magalu para formato interno."""
        price_info = item.get("price", {})
        return {
            "sku": item.get("sku", item.get("id", "")),
            "title": item.get("title", ""),
            "url": f"https://www.magazineluiza.com.br{item.get('url', '')}",
            "price": price_info.get("bestPrice") or price_info.get("price", 0),
            "original_price": price_info.get("price"),
            "free_shipping": item.get("freeShipping", False),
            "rating": item.get("rating", {}).get("average", 0),
            "review_count": item.get("rating", {}).get("count", 0),
            "images": [item.get("image", "")] if item.get("image") else [],
            "seller_id": item.get("seller", {}).get("id", "magalu"),
            "seller_name": item.get("seller", {}).get("description", "Magazine Luiza"),
            "category_path": item.get("categoryPath", "").split(" > "),
            "installments_max": item.get("installment", {}).get("quantity"),
            "installments_value": item.get("installment", {}).get("amount"),
        }

    def _extract_attributes(self, attrs: dict) -> ListingAttributes:
        return ListingAttributes(
            cor=attrs.get("cor") or attrs.get("Cor"),
            material=attrs.get("material") or attrs.get("Material"),
            largura_cm=self._parse_float(attrs.get("largura") or attrs.get("Largura")),
            profundidade_cm=self._parse_float(attrs.get("profundidade") or attrs.get("Profundidade")),
            altura_cm=self._parse_float(attrs.get("altura") or attrs.get("Altura")),
            peso_kg=self._parse_float(attrs.get("peso") or attrs.get("Peso")),
            extras={k: str(v) for k, v in attrs.items()},
        )

    @staticmethod
    def _parse_float(val: Any) -> Optional[float]:
        return parse_length_to_cm(val)

    def _extract_badges(self, raw: dict) -> Badges:
        return Badges(
            frete_gratis=raw.get("free_shipping", False),
            full=raw.get("fulfillment", False),
            anuncio_patrocinado=raw.get("sponsored", False),
        )

    @staticmethod
    def _extract_media(images: list) -> list[MediaItem]:
        items = []
        for i, url in enumerate(images):
            if url:
                items.append(MediaItem(url=url, tipo=MediaType.PHOTO, is_capa=(i == 0)))
        return items

    @staticmethod
    def _extract_seo_terms(title: str) -> list[str]:
        words = title.lower().split()
        return list(dict.fromkeys(w for w in words if len(w) > 3))

"""
Connector Mercado Livre — usa a API oficial (MeLi API v1).

Autenticação:
  1. Redireciona o usuário para ML_REDIRECT_URI (OAuth2)
  2. ML retorna um ?code=
  3. Troca o code por access_token via /oauth/token
  4. Guarde o token em ML_SELLER_ACCESS_TOKEN

Documentação: https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Any, Optional
import httpx
import structlog

from api.src.config import get_settings
from api.src.connectors.base import BaseConnector
from api.src.utils.measurements import parse_length_to_cm
from api.src.types.listing import (
    Badges, ListingAttributes, ListingNormalized, Marketplace,
    MediaItem, MediaType, Seller, SellerMetrics, SellerReputation,
    SocialProof, TextBlocks,
)

log = structlog.get_logger()
settings = get_settings()

_REPUTATION_MAP = {
    "5_green": SellerReputation.PLATINUM,
    "4_light_green": SellerReputation.GOLD,
    "3_yellow": SellerReputation.SILVER,
    "2_orange": SellerReputation.BRONZE,
    "1_red": SellerReputation.NEW,
}


class MercadoLivreConnector(BaseConnector):
    marketplace_name = "mercado_livre"
    rate_limit_delay = 0.3   # ML permite ~90 req/min

    BASE = "https://api.mercadolibre.com"

    def __init__(self, access_token: str = ""):
        super().__init__(api_key=access_token)
        self._token = access_token or settings.ml_seller_access_token

    def _auth_headers(self) -> dict:
        h = {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    # ── Busca ─────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        category_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        GET /sites/MLB/search?q=...&limit=50
        Retorna até 1000 resultados paginados (50 por vez).
        """
        params: dict[str, Any] = {
            "q": query,
            "limit": min(limit, 50),
            "offset": offset,
        }
        if category_id:
            params["category"] = category_id

        data = await self._get(
            f"{self.BASE}/sites/MLB/search",
            params=params,
            headers=self._auth_headers(),
        )
        return data.get("results", [])

    async def get_listing_details(self, listing_id: str) -> dict[str, Any]:
        """GET /items/{id} + /items/{id}/descriptions"""
        item, desc = await asyncio.gather(
            self._get(f"{self.BASE}/items/{listing_id}", headers=self._auth_headers()),
            self._get(f"{self.BASE}/items/{listing_id}/descriptions", headers=self._auth_headers()),
        )
        item["_descriptions"] = desc if isinstance(desc, list) else []
        return item

    async def get_seller_details(self, seller_id: str) -> dict[str, Any]:
        """GET /users/{seller_id}"""
        return await self._get(f"{self.BASE}/users/{seller_id}", headers=self._auth_headers())

    # ── Normalização ──────────────────────────────────────────

    async def normalize(self, raw: dict[str, Any]) -> ListingNormalized:
        listing_id = raw.get("id", "")
        price = float(raw.get("price") or 0)
        original_price = float(raw.get("original_price") or 0) or None
        shipping = self._extract_shipping(raw)

        seller_raw = raw.get("seller", {})
        seller = await self._build_seller(seller_raw)

        attributes = self._extract_attributes(raw.get("attributes", []))
        badges = self._extract_badges(raw)
        media = self._extract_media(raw.get("pictures", []))
        text_blocks = self._extract_text_blocks(raw)
        seo_terms = self._extract_seo_terms(raw)
        social_proof = self._extract_social_proof(raw)
        category_path = self._extract_category(raw)

        return ListingNormalized(
            marketplace=Marketplace.MERCADO_LIVRE,
            listing_id=listing_id,
            url=raw.get("permalink", f"https://www.mercadolivre.com.br/p/{listing_id}"),
            price=price,
            price_original=original_price,
            shipping_cost=shipping,
            final_price_estimate=price + shipping,
            installments_max=self._installments_max(raw),
            installments_value=self._installments_value(raw),
            category_path=category_path,
            category_id=raw.get("category_id"),
            title=raw.get("title", ""),
            attributes=attributes,
            text_blocks=text_blocks,
            media=media,
            media_count=len(media),
            seller=seller,
            social_proof=social_proof,
            badges=badges,
            seo_terms=seo_terms,
            scraped_at=datetime.utcnow(),
        )

    # ── Helpers privados ──────────────────────────────────────

    def _extract_shipping(self, raw: dict) -> float:
        shipping = raw.get("shipping", {})
        if shipping.get("free_shipping"):
            return 0.0
        # ML não retorna custo exato na listagem; usar 0 como proxy
        return 0.0

    async def _build_seller(self, seller_raw: dict) -> Seller:
        seller_id = str(seller_raw.get("id", ""))
        name = seller_raw.get("nickname", seller_id)
        reputation_level = seller_raw.get("seller_reputation", {}).get("level_id", "")
        reputation = _REPUTATION_MAP.get(reputation_level, SellerReputation.UNKNOWN)

        # Tenta buscar detalhes se tiver ID
        metrics = None
        if seller_id and self._token:
            try:
                detail = await self.get_seller_details(seller_id)
                rep = detail.get("seller_reputation", {})
                trans = rep.get("transactions", {})
                metrics = SellerMetrics(
                    vendas_12m=trans.get("completed"),
                    cancelamentos_pct=rep.get("metrics", {}).get("cancellations", {}).get("rate"),
                    reclamacoes_pct=rep.get("metrics", {}).get("claims", {}).get("rate"),
                    atraso_entrega_pct=rep.get("metrics", {}).get("delayed_handling_time", {}).get("rate"),
                )
            except Exception:
                pass

        return Seller(
            seller_id=seller_id,
            nome=name,
            reputacao=reputation,
            metricas=metrics,
            is_official_store=bool(seller_raw.get("is_official_store", False)),
        )

    def _extract_attributes(self, attrs: list) -> ListingAttributes:
        mapping = {
            "COR": "cor",
            "MATERIAL": "material",
            "WIDTH": "largura_cm",
            "DEPTH": "profundidade_cm",
            "HEIGHT": "altura_cm",
            "WEIGHT": "peso_kg",
            "PRODUCT_TYPE": "tipo_produto",
            "NUMBER_OF_SEATS": "numero_lugares",
            "FILLING_MATERIAL": "densidade",
        }
        data: dict[str, Any] = {}
        extras: dict[str, str] = {}
        for attr in attrs:
            key = attr.get("id", "")
            val = attr.get("value_name")
            if val is None:
                continue
            mapped = mapping.get(key)
            if mapped:
                # conversão de unidade quando necessário
                if mapped in ("largura_cm", "profundidade_cm", "altura_cm"):
                    data[mapped] = self._to_cm(val, attr.get("value_struct", {}))
                elif mapped == "peso_kg":
                    data[mapped] = self._to_kg(val, attr.get("value_struct", {}))
                elif mapped == "numero_lugares":
                    try:
                        data[mapped] = int(val)
                    except ValueError:
                        pass
                else:
                    data[mapped] = val
            else:
                extras[key] = val
        data["extras"] = extras
        return ListingAttributes(**data)

    @staticmethod
    def _to_cm(value_name: str, struct: dict) -> Optional[float]:
        try:
            raw_number = struct.get("number")
            if raw_number is None:
                return parse_length_to_cm(value_name)
            num = float(str(raw_number).replace(",", "."))
            unit = struct.get("unit", "cm").lower()
            if unit == "mm":
                return num / 10
            if unit == "m":
                return num * 100
            return num
        except (ValueError, TypeError):
            return parse_length_to_cm(value_name)

    @staticmethod
    def _to_kg(value_name: str, struct: dict) -> Optional[float]:
        try:
            num = float(struct.get("number", value_name.split()[0]))
            unit = struct.get("unit", "kg").lower()
            if unit == "g":
                return num / 1000
            return num
        except (ValueError, TypeError):
            return None

    def _extract_badges(self, raw: dict) -> Badges:
        shipping = raw.get("shipping", {})
        tags = raw.get("tags", [])
        return Badges(
            frete_gratis=shipping.get("free_shipping", False),
            full=shipping.get("logistic_type") == "fulfillment",
            premium="premium" in tags,
            oficial=bool(raw.get("official_store_id")),
            melhorei_preco="improved_price" in tags,
            anuncio_patrocinado=bool(raw.get("advertising_info")),
        )

    def _extract_media(self, pictures: list) -> list[MediaItem]:
        items = []
        for i, pic in enumerate(pictures):
            url = pic.get("url") or pic.get("secure_url", "")
            if url:
                items.append(MediaItem(
                    url=url,
                    tipo=MediaType.PHOTO,
                    is_capa=(i == 0),
                ))
        return items

    def _extract_text_blocks(self, raw: dict) -> TextBlocks:
        bullets: list[str] = []
        description: Optional[str] = None

        # highlights / short description
        hl = raw.get("highlights", [])
        if hl:
            bullets = [h.get("text", "") for h in hl if h.get("text")]

        # descrição longa (vem do endpoint /descriptions)
        for desc in raw.get("_descriptions", []):
            if desc.get("plain_text"):
                description = desc["plain_text"]
                break

        return TextBlocks(bullets=bullets, descricao=description)

    def _extract_seo_terms(self, raw: dict) -> list[str]:
        title = raw.get("title", "").lower()
        terms = [w for w in title.split() if len(w) > 3]
        return list(dict.fromkeys(terms))  # deduplica mantendo ordem

    def _extract_social_proof(self, raw: dict) -> SocialProof:
        return SocialProof(
            avaliacoes_total=raw.get("reviews", {}).get("total", 0),
            nota_media=float(raw.get("reviews", {}).get("rating_average") or 0),
            vendas_estimadas=raw.get("sold_quantity"),
        )

    def _extract_category(self, raw: dict) -> list[str]:
        # ML não retorna path completo na busca; retornamos o ID como fallback
        cat_id = raw.get("category_id", "")
        return [cat_id] if cat_id else []

    @staticmethod
    def _installments_max(raw: dict) -> Optional[int]:
        inst = raw.get("installments", {})
        return inst.get("quantity")

    @staticmethod
    def _installments_value(raw: dict) -> Optional[float]:
        inst = raw.get("installments", {})
        v = inst.get("amount")
        return float(v) if v else None

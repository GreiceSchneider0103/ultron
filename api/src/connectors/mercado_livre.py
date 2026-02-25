"""
Conector do Mercado Livre
Implementação da interface BaseConnector
"""

import os
import json
import httpx
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from api.src.connectors.base import BaseConnector, MarketplaceConfig
from api.src.types.listing import (
    ListingNormalized, 
    Marketplace, 
    ReputationLevel,
    ListingAttributes,
    MediaItem,
    Seller,
    SellerMetrics,
    SocialProof,
    Badges,
    TextBlocks
)


logger = logging.getLogger(__name__)


class MercadoLivreConnector(BaseConnector):
    """Conector para API do Mercado Livre"""
    
    def __init__(self, access_token: Optional[str] = None):
        # Pegar token das variáveis de ambiente ou parâmetro
        token = access_token or os.getenv("ML_ACCESS_TOKEN")
        config = MarketplaceConfig.get_config("mercado_livre")
        
        super().__init__(api_key=token, config=config)
        
        self.marketplace = Marketplace.MERCADO_LIVRE
        self.base_url = "https://api.mercadolibre.com"
        self.max_title_length = config.get("max_title_length", 60)
        
    async def _get_headers(self) -> Dict[str, str]:
        """Headers para requisições na API do ML"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        condition: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Buscar anúncios no Mercado Livre"""
        
        start_time = time.time()
        # Construir query
        search_url = f"{self.base_url}/sites/MLB/search"
        
        params = {
            "q": query,
            "limit": min(limit, 50),  # ML limita a 50 por requisição
            "offset": offset,
        }
        
        if category:
            params["category"] = category
            
        if price_min is not None:
            params["price_min"] = price_min
            
        if price_max is not None:
            params["price_max"] = price_max
            
        if condition:
            params["condition"] = condition
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    search_url,
                    params=params,
                    headers=await self._get_headers()
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                # Structured logging
                logger.info(json.dumps({
                    "event": "connector_search",
                    "marketplace": "mercado_livre",
                    "query": query,
                    "item_count": len(results),
                    "duration_ms": round((time.time() - start_time) * 1000, 2),
                    "request_id": request_id
                }))
                return results
                
            except httpx.HTTPError as e:
                logger.error(f"Erro na busca do Mercado Livre: {e}")
                return []
    
    async def get_details(self, listing_id: str) -> Dict[str, Any]:
        """Buscar detalhes de um anúncio no ML"""
        
        url = f"{self.base_url}/items/{listing_id}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url,
                    headers=await self._get_headers()
                )
                response.raise_for_status()
                
                item_data = response.json()
                
                # Buscar descrição separadamente
                desc_url = f"{self.base_url}/items/{listing_id}/description"
                try:
                    desc_response = await client.get(desc_url, headers=await self._get_headers())
                    
                    if desc_response.status_code == 200:
                        desc_data = desc_response.json()
                        item_data["description"] = desc_data.get("plain_text", "")
                except Exception as e:
                    logger.warning(f"Não foi possível buscar descrição para {listing_id}: {e}")
                
                return item_data
                
            except httpx.HTTPError as e:
                logger.error(f"Erro ao buscar detalhes do ML: {e}")
                return {}
    
    async def get_seller(self, seller_id: str) -> Dict[str, Any]:
        """Buscar perfil do vendedor no ML"""
        
        url = f"{self.base_url}/users/{seller_id}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    url,
                    headers=await self._get_headers()
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Erro ao buscar vendedor do ML: {e}")
                return {}
    
    async def normalize_listing(self, raw_data: Dict[str, Any]) -> ListingNormalized:
        """Converter dados do ML para ListingNormalized"""
        
        # Extrair seller
        seller_data = raw_data.get("seller", {})
        seller_id = seller_data.get("id", raw_data.get("seller_id", ""))
        
        # Buscar dados do seller se não estiverem incluídos
        if seller_id and not seller_data.get("metrics"):
            try:
                seller_full = await self.get_seller(seller_id)
            except:
                seller_full = {}
        else:
            seller_full = seller_data
        
        # Processar atributos
        attributes = self._process_attributes(raw_data.get("attributes", []))
        
        # Processar imagens
        pictures = raw_data.get("pictures", [])
        if not pictures and "thumbnail" in raw_data:
             # Fallback para thumbnail se não houver pictures (comum em resultados de busca)
             pictures = [{"url": raw_data["thumbnail"]}]

        media = [
            MediaItem(
                url=picture.get("url", ""),
                tipo="foto",
                is_capa=(i == 0)
            )
            for i, picture in enumerate(pictures[:10])  # Limitar a 10 imagens
        ]
        
        # Processar seller
        tags = seller_full.get("tags", [])
        is_official = "eshop" in tags or "brand" in tags

        seller = Seller(
            seller_id=str(seller_id),
            nome=seller_full.get("nickname", raw_data.get("seller_contact", {}).get("email", "Desconhecido")),
            reputacao=self._map_reputation(seller_full.get("seller_reputation", {}).get("level_id", "new")),
            tempo_mercado_meses=self._calculate_months_since(seller_full.get("registration_date")),
            metricas=SellerMetrics(
                vendas_12m=seller_full.get("seller_reputation", {}).get("metrics", {}).get("sales", {}).get("completed", {}).get("value"),
                reputacao=1.0 if seller_full.get("seller_reputation", {}).get("power_seller_status") == "active" else 0.0,
            ) if seller_full else None,
            tiene_tienda_oficial=is_official,
        )
        
        # Processar prova social
        social = raw_data.get("sold_quantity", 0)
        reviews = raw_data.get("reviews", {})
        review_total = 0
        review_rating = 0.0
        
        if isinstance(reviews, dict):
            review_total = reviews.get("total", 0)
            review_rating = reviews.get("rating_average", 0.0)

        social_proof = SocialProof(
            avaliacoes=review_total,
            nota_media=review_rating,
        )
        
        # Processar badges
        shipping = raw_data.get("shipping", {})
        badges = Badges(
            frete_gratis=shipping.get("free_shipping", False),
            full=shipping.get("logistic_type") == "fulfillment",
            premium=raw_data.get("listing_type_id") == "gold_pro",
            oficial=raw_data.get("official_store_id") is not None,
            novo=raw_data.get("condition") == "new",
        )
        
        # Processar texto
        sale_terms = raw_data.get("sale_terms", [])
        bullets = []
        if isinstance(sale_terms, list):
            for term in sale_terms:
                if isinstance(term, dict) and term.get("name") and term.get("value_name"):
                    bullets.append(f"{term['name']}: {term['value_name']}")

        description = raw_data.get("description", "")
        text_blocks = TextBlocks(
            bullets=bullets,
            descricao=description if isinstance(description, str) else description.get("plain_text", ""),
        )
        
        # Extrair termos de SEO do título
        seo_terms = self._extract_seo_terms(raw_data.get("title", ""))
        
        # Calcular preço final
        price = raw_data.get("price", 0.0)
        shipping_cost = shipping.get("cost", 0.0) or 0.0
        
        # Category path
        category_id = raw_data.get("category_id", "")
        category_path = [category_id] if category_id else []
        
        return ListingNormalized(
            marketplace=Marketplace.MERCADO_LIVRE,
            listing_id=raw_data.get("id", ""),
            url=raw_data.get("permalink", ""),
            title=raw_data.get("title", ""),
            price=price,
            currency=raw_data.get("currency_id", "BRL"),
            shipping_cost=shipping_cost,
            final_price_estimate=price + shipping_cost,
            category_path=category_path,
            category_id=category_id,
            attributes=attributes,
            media=media,
            seller=seller,
            social_proof=social_proof,
            badges=badges,
            text_blocks=text_blocks,
            seo_terms=seo_terms,
            original_data=raw_data
        )
    
    def _process_attributes(self, attributes: List[Dict]) -> ListingAttributes:
        """Processar atributos do produto"""
        
        attr_dict = {attr.get("id", ""): attr.get("value_name", "") 
                     for attr in attributes}
        
        # Mapear para campos específicos de móveis
        return ListingAttributes(
            cor=attr_dict.get("COLOR", None),
            material=attr_dict.get("MATERIAL", None),
            tecido=attr_dict.get("FABRIC_DESIGN", None),
            largura=self._extract_number(attr_dict.get("WIDTH")),
            profundidade=self._extract_number(attr_dict.get("DEPTH")),
            altura=self._extract_number(attr_dict.get("HEIGHT")),
            peso=self._extract_number(attr_dict.get("WEIGHT")),
            tipo_sofa=attr_dict.get("SOFA_TYPE"),
            numero_lugares=self._extract_number(attr_dict.get("SEATING_CAPACITY")),
            formato=attr_dict.get("SOFA_FORMAT"),
            capacidade=self._extract_number(attr_dict.get("MAX_LOAD_CAPACITY")),
        )
    
    def _extract_number(self, value: Any) -> Optional[float]:
        """Extrair número de uma string"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            # Tentar extrair número de string
            import re
            numbers = re.findall(r"[\d.]+", str(value))
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None
    
    def _map_reputation(self, level_id: str) -> ReputationLevel:
        """Mapear nível de reputação do ML para nosso enum"""
        level_id = str(level_id).upper()
        
        if level_id in ["5_black", "4_platinum", "3_gold"]:
            return ReputationLevel.GOLD
        elif level_id == "2_silver":
            return ReputationLevel.SILVER
        elif level_id == "1_bronze":
            return ReputationLevel.BRONZE
        else:
            return ReputationLevel.NEW
    
    def _calculate_months_since(self, registration_date: Optional[str]) -> Optional[int]:
        """Calcular meses desde o registro"""
        if not registration_date:
            return None
        
        try:
            reg_date = datetime.fromisoformat(registration_date.replace("Z", "+00:00"))
            now = datetime.now()
            months = (now.year - reg_date.year) * 12 + (now.month - reg_date.month)
            return max(0, months)
        except:
            return None
    
    def _extract_seo_terms(self, title: str) -> List[str]:
        """Extrair termos de SEO do título"""
        # Palavras comuns a ignorar
        stop_words = {
            "de", "do", "da", "dos", "das", "em", "para", "com", "sem",
            "o", "a", "os", "as", "um", "uma", "por", "mais", "ao",
            "e", "ou", "se", "na", "no", "nas", "nos"
        }
        
        # Limpar e tokenizar
        words = title.lower()
        words = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in words)
        words = [w for w in words.split() if w not in stop_words and len(w) > 2]
        
        return list(set(words))

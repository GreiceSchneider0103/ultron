"""
Conector do Magalu - Foco em Inteligência Operacional (Seller Data)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from api.src.connectors.base import BaseConnector
from api.src.types.listing import ListingNormalized, Marketplace, Seller
from api.src.config import settings

logger = logging.getLogger(__name__)

class MagaluConnector(BaseConnector):
    """
    Conector Magalu focado em operações de Seller (Portfólio, Preço, Estoque).
    Usa endpoints de Seller API.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        token = access_token or settings.MAGALU_ACCESS_TOKEN
        super().__init__(api_key=token)
        
        self.channel_id = settings.MAGALU_CHANNEL_ID
        self.base_url = settings.MAGALU_SANDBOX_BASE_URL if settings.MAGALU_USE_SANDBOX else settings.MAGALU_BASE_URL
        self.auth_url = "https://id-sandbox.magalu.com" if settings.MAGALU_USE_SANDBOX else "https://id.magalu.com"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Channel-Id": self.channel_id,
            "Content-Type": "application/json"
        }

    async def authenticate(self) -> str:
        """Obtém token OAuth (Fluxo Client Credentials)"""
        if not settings.MAGALU_CLIENT_ID or not settings.MAGALU_CLIENT_SECRET:
            logger.warning("Magalu Client ID/Secret not provided.")
            return ""
            
        url = f"{self.auth_url}/oauth/token"
        auth = (settings.MAGALU_CLIENT_ID, settings.MAGALU_CLIENT_SECRET)
        data = {"grant_type": "client_credentials", "scope": "orders catalog"}
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, auth=auth, data=data)
                resp.raise_for_status()
                token_data = resp.json()
                self.api_key = token_data.get("access_token")
                # Atualiza headers
                self.headers["Authorization"] = f"Bearer {self.api_key}"
                return self.api_key
        except Exception as e:
            logger.error(f"Magalu Auth Failed: {e}")
            return ""

    async def _get(self, endpoint: str, params: Dict = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_price(self, sku: str) -> Dict[str, Any]:
        """
        GET /seller/v1/portfolios/prices/:sku
        Retorna dados de preço e status do SKU.
        """
        try:
            return await self._get(f"/seller/v1/portfolios/prices/{sku}")
        except Exception as e:
            logger.error(f"Erro ao buscar preço Magalu para {sku}: {e}")
            return {}

    async def get_scores(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        GET /seller/v1/portfolios/products/scores
        Retorna scores de qualidade dos produtos.
        """
        try:
            params = {"limit": limit, "offset": offset}
            # A resposta geralmente vem envelopada ou em lista direta, dependendo da versão.
            # Assumindo lista direta ou chave 'results' conforme padrão REST comum
            data = await self._get("/seller/v1/portfolios/products/scores", params=params)
            return data if isinstance(data, list) else data.get("results", [])
        except Exception as e:
            logger.error(f"Erro ao buscar scores Magalu: {e}")
            return []

    async def get_details(self, sku: str) -> Dict[str, Any]:
        """
        Combina Price e Score para detalhe (Operacional).
        """
        price_data = await self.get_price(sku)
        # Score não tem endpoint por SKU individual documentado aqui, 
        # mas vamos retornar o que temos.
        return {
            "sku": sku,
            "price_data": price_data,
            # Score teria que ser buscado na lista geral, o que é custoso aqui.
            # Deixamos vazio ou implementamos cache depois.
        }

    async def search(self, query: str, category: Optional[str] = None, limit: int = 50, page: int = 1, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        NÃO SUPORTADO: Search concorrente via Seller API.
        """
        logger.warning("Search concorrente não suportado na Magalu Seller API.")
        return []

    async def normalize_listing(self, raw_data: Dict[str, Any]) -> ListingNormalized:
        """
        Normaliza dados operacionais (Price + Score) para ListingNormalized.
        Espera receber um dict combinado ou o retorno de get_price.
        """
        # Extração defensiva
        sku = raw_data.get("sku", raw_data.get("id", "unknown"))
        price_info = raw_data.get("price_data", raw_data) # Se vier direto do get_price
        
        # Mapeamento de campos (ajustar conforme resposta real da API)
        price = float(price_info.get("price", 0.0))
        list_price = float(price_info.get("list_price", 0.0))
        
        # Score (se disponível)
        score_data = raw_data.get("score_data", {})
        
        return ListingNormalized(
            marketplace=Marketplace.MAGALU,
            listing_id=str(sku),
            url=f"https://www.magazineluiza.com.br/produto/{sku}",
            title=f"Produto SKU {sku}", # Seller API de preço as vezes não retorna titulo
            price=price,
            final_price_estimate=price,
            seller=Seller(
                seller_id=self.channel_id,
                nome="Loja Própria"
            ),
            scraped_at=datetime.now(),
            original_data=raw_data
        )
        
        return ListingNormalized(
            marketplace=Marketplace.MAGALU,
            listing_id=str(sku),
            url=f"https://www.magazineluiza.com.br/produto/{sku}",
            title=title,
            price=price,
            final_price_estimate=price,
            seller=Seller(
                seller_id=self.channel_id,
                nome="Loja Própria (Sandbox)"
            ),
            scraped_at=datetime.now(),
            original_data=raw_data
        )
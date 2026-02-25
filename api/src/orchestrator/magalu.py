"""
Conector do Magalu - Foco em Inteligência Operacional (Seller Data)
"""

import logging
import uuid
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
    Usa o Channel ID do Sandbox para testes.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        token = access_token or settings.MAGALU_ACCESS_TOKEN
        super().__init__(api_key=token)
        
        self.channel_id = settings.MAGALU_CHANNEL_ID
        self.base_url = "https://api-sandbox.magalu.com" if settings.MAGALU_SANDBOX else "https://api.magalu.com"
        self.auth_url = "https://id-sandbox.magalu.com" if settings.MAGALU_SANDBOX else "https://id.magalu.com"

    async def authenticate(self) -> str:
        """Obtém token OAuth (Fluxo Client Credentials)"""
        if not settings.MAGALU_CLIENT_ID or not settings.MAGALU_CLIENT_SECRET:
            logger.warning("Magalu Client ID/Secret not provided.")
            return ""
            
        url = f"{self.auth_url}/oauth/token"
        auth = (settings.MAGALU_CLIENT_ID, settings.MAGALU_CLIENT_SECRET)
        data = {"grant_type": "client_credentials", "scope": "orders catalog"} # Scopes comuns
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, auth=auth, data=data)
                resp.raise_for_status()
                token_data = resp.json()
                self.api_key = token_data.get("access_token")
                return self.api_key
        except Exception as e:
            logger.error(f"Magalu Auth Failed: {e}")
            return ""

    async def onboard_seller(self):
        """Realiza o onboarding do seller no Sandbox (Essencial para testes)"""
        if not self.api_key: await self.authenticate()
        
        url = f"{self.base_url}/v1/sellers"
        # Payload básico de onboarding sandbox
        payload = {
            "id": self.channel_id,
            "name": "Ultron Test Seller",
            "trading_name": "Ultron Store"
        }
        # Nota: Em sandbox, muitas vezes o seller já existe ou o endpoint é simulado.
        # Este método serve para garantir que o 'channel_id' está ativo.
        try:
            # Tenta criar ou atualizar
            await self._get(url) # Check se existe (simplificado)
            logger.info(f"Seller {self.channel_id} active on Sandbox")
        except Exception:
            logger.warning("Seller onboarding check failed or seller not found.")

    # --- Operações de Portfólio (Operational Intelligence) ---

    async def get_portfolio(self, page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca SKUs do portfólio (Operational Flow)"""
        url = f"{self.base_url}/v1/products"
        params = {"page": page, "limit": limit}
        # Headers específicos do Magalu
        self.client.headers.update({"X-Channel-Id": self.channel_id})
        if self.api_key:
            self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})
            
        response = await self._get(url, params=params)
        return response.get("products", []) if isinstance(response, dict) else []

    async def get_product_score(self, sku: str) -> Dict[str, Any]:
        """Busca score de qualidade do anúncio (Content Score)"""
        url = f"{self.base_url}/v1/products/{sku}/score"
        return await self._get(url)

    # --- Implementação Obrigatória do BaseConnector ---

    async def search(self, query: str, category: Optional[str] = None, limit: int = 50, page: int = 1, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Magalu não permite busca aberta de concorrentes via API de Seller.
        Retorna produtos do próprio portfólio que correspondem à query (filtro local).
        """
        all_products = await self.get_portfolio(limit=100)
        # Filtro simples em memória para simular busca no portfólio
        return [p for p in all_products if query.lower() in p.get("name", "").lower()][:limit]

    async def get_details(self, listing_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/products/{listing_id}"
        return await self._get(url)

    async def normalize_listing(self, raw_data: Dict[str, Any]) -> ListingNormalized:
        """Normaliza dados do Magalu (Seller Data)"""
        sku = raw_data.get("id", raw_data.get("sku", ""))
        title = raw_data.get("name", raw_data.get("title", "Produto sem título"))
        price = float(raw_data.get("price", 0.0))
        
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
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from typing import Any, Dict
from abc import ABC

# Alias for backward compatibility (required by mercado_livre.py)
MarketplaceConfig = Dict[str, Any]

class BaseConnector(ABC):
    """Classe base para conectores com retry logic e httpx"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = ""
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def _get(self, url: str, params: Dict = None) -> Dict:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self.client.aclose()

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        request_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Buscar anúncios por keyword com suporte a paginação"""
        pass
    
    @abstractmethod
    async def get_details(self, listing_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def normalize_listing(self, raw_data: Dict) -> Any:
        pass
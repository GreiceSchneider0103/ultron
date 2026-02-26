from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class BaseConnector(ABC):
    """Classe base para conectores com retry logic e httpx"""
    
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = ""
        self._client = httpx.AsyncClient(timeout=30.0)
        # Compat alias for legacy modules
        self.client = self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        response = await self._client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        await self._client.aclose()

    @abstractmethod
    async def search(
        self,
        query: str,
        category_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Buscar anúncios por keyword com suporte a paginação"""
        pass
    
    @abstractmethod
    async def get_listing_details(self, listing_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def normalize(self, raw_data: Dict[str, Any]) -> Any:
        pass

    async def search_and_normalize(
        self,
        query: str,
        category_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Any]:
        raw_items = await self.search(
            query=query,
            category_id=category_id,
            limit=limit,
            offset=offset,
        )
        normalized: List[Any] = []
        for item in raw_items:
            try:
                normalized.append(await self.normalize(item))
            except Exception:
                continue
        return normalized

    async def get_details(self, listing_id: str) -> Dict[str, Any]:
        """Compat alias for legacy code."""
        return await self.get_listing_details(listing_id)

    async def normalize_listing(self, raw_data: Dict[str, Any]) -> Any:
        """Compat alias for legacy code."""
        return await self.normalize(raw_data)

    def validate_title(self, title: str, max_length: int = 60) -> Dict[str, Any]:
        """
        Validação base de título (marketplaces podem sobrescrever).
        """
        forbidden_terms = ["gratis", "100%", "melhor do brasil"]
        lower = title.lower()
        found_forbidden = [term for term in forbidden_terms if term in lower]
        is_valid = len(title) <= max_length and not found_forbidden
        return {
            "is_valid": is_valid,
            "max_length": max_length,
            "length": len(title),
            "forbidden_terms_found": found_forbidden,
            "errors": [] if is_valid else ["title_invalid"],
        }

import asyncio
import json
import os
import time
import logging
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from api.src.connectors.base import BaseConnector
from api.src.utils.cache import async_lru_cache
from api.src.types.analytics import MarketSummary, PriceStats
from api.src.types.listing import ListingNormalized

logger = logging.getLogger(__name__)

class MarketAgent:
    """
    Orquestrador com hardening: Timeout, Cache, Retry (via connector) e Persistência.
    """
    def __init__(self, connectors: Dict[str, BaseConnector]):
        self.connectors = connectors
        self.storage_path = "data/reports"
        os.makedirs(self.storage_path, exist_ok=True)

    @async_lru_cache(ttl_seconds=600)
    async def research_market(
        self,
        keyword: str,
        marketplace: str = "mercado_livre",
        limit: int = 50,
        timeout: int = 60,
        request_id: Optional[str] = None
    ) -> Union[MarketSummary, Dict[str, Any]]:
        start_time = time.time()
        try:
            # Global timeout control
            result = await asyncio.wait_for(
                self._execute_research(keyword, marketplace, limit, request_id),
                timeout=timeout
            )
            
            # Structured logging for observability
            logger.info(json.dumps({
                "event": "tool_call",
                "tool": "research_market",
                "marketplace": marketplace,
                "query": keyword,
                "item_count": result.total_listings if isinstance(result, MarketSummary) else 0,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "request_id": request_id
            }))
            return result
            
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "code": "TIMEOUT",
                "message": f"Research timed out after {timeout}s"
            }
        except Exception as e:
            # Structured error handling
            return {
                "status": "error",
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "details": type(e).__name__
            }

    async def _execute_research(self, keyword: str, marketplace: str, limit: int, request_id: Optional[str]) -> MarketSummary:
        connector = self.connectors.get(marketplace)
        if not connector:
            raise ValueError(f"Connector {marketplace} not found")

        listings = []
        page = 1
        
        # Pagination support: fetch until N items
        while len(listings) < limit:
            batch = await connector.search(query=keyword, limit=limit, page=page, request_id=request_id)
            if not batch:
                break
            
            listings.extend(batch)
            page += 1
            
            if len(batch) < 10: # Heuristic: small batch means end of results
                break
                
        # Analytics Logic
        valid_listings = [l for l in listings if l.get("price") is not None]
        prices = sorted([float(l["price"]) for l in valid_listings])
        
        if not prices:
            stats = PriceStats(min=0.0, max=0.0, median=0.0, avg=0.0)
            outliers = []
        else:
            stats = PriceStats(
                min=prices[0],
                max=prices[-1],
                median=statistics.median(prices),
                avg=statistics.mean(prices)
            )
            
            # Outliers (IQR method)
            if len(prices) >= 4:
                q1 = prices[int(len(prices) * 0.25)]
                q3 = prices[int(len(prices) * 0.75)]
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = [l for l in valid_listings if float(l["price"]) < lower_bound or float(l["price"]) > upper_bound]
            else:
                outliers = []

        # Grouping
        seller_dist = {}
        shipping_dist = {}
        
        for l in valid_listings:
            # Seller grouping
            s_type = "regular"
            if l.get("official_store_id"): s_type = "official"
            elif l.get("seller", {}).get("seller_reputation", {}).get("power_seller_status"):
                s_type = l["seller"]["seller_reputation"]["power_seller_status"]
            seller_dist[s_type] = seller_dist.get(s_type, 0) + 1
            
            # Shipping grouping
            sh_type = l.get("shipping", {}).get("logistic_type", "standard")
            if l.get("shipping", {}).get("free_shipping"): sh_type += "_free"
            shipping_dist[sh_type] = shipping_dist.get(sh_type, 0) + 1

        summary = MarketSummary(
            keyword=keyword,
            marketplace=marketplace,
            total_listings=len(listings),
            price_stats=stats,
            seller_distribution=seller_dist,
            shipping_distribution=shipping_dist,
            outliers=outliers,
            timestamp=datetime.now()
        )
        
        # Simple persistence
        safe_key = "".join(c for c in keyword if c.isalnum())
        filename = f"{self.storage_path}/{safe_key}_{marketplace}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))
        
        # DB Persistence (Optional Layer)
        try:
            from api.src.db.database import save_research_run
            save_research_run(summary, listings)
        except Exception as e:
            logger.warning(f"DB Persistence failed (execution continued): {e}")

        return summary

    # --- Operational Intelligence (Magalu Flow) ---
    
    async def analyze_operations(self, marketplace: str = "magalu") -> Dict[str, Any]:
        """
        Fluxo de Inteligência Operacional:
        get_skus -> enrich -> normalize -> score -> save
        """
        connector = self.connectors.get(marketplace)
        if not connector:
            raise ValueError(f"Connector {marketplace} not found")
            
        # 1. Get SKUs (Portfolio)
        raw_products = await connector.search(query="", limit=100) # Empty query = list all
        
        results = []
        for raw in raw_products:
            # 2. Normalize
            normalized: ListingNormalized = await connector.normalize_listing(raw)
            
            # 3. Enrich (Get Score from Magalu)
            if hasattr(connector, 'get_product_score'):
                score_data = await connector.get_product_score(normalized.listing_id)
                normalized.ai_insights = {"magalu_score": score_data}
            
            results.append(normalized)
            
        # TODO: Save to DB (Operational Table)
        return {"total_skus": len(results), "data": results}
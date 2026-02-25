from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class PriceStats(BaseModel):
    min: float
    max: float
    median: float
    avg: float

class MarketSummary(BaseModel):
    keyword: str
    marketplace: str
    total_listings: int
    price_stats: PriceStats
    seller_distribution: Dict[str, int]
    shipping_distribution: Dict[str, int]
    outliers: List[Dict[str, Any]]
    timestamp: datetime
    
    class Config:
        arbitrary_types_allowed = True
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    keyword: str = Field(..., min_length=2)
    marketplace: str = "mercadolivre"
    limit: int = Field(default=30, ge=1, le=100)


class AuditListingRequest(BaseModel):
    listing_id: str
    marketplace: str = "mercadolivre"
    keyword: Optional[str] = None


class OptimizeTitleRequest(BaseModel):
    product_title: str
    marketplace: str = "mercadolivre"
    category: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=10)


class CompetitorPricingRequest(BaseModel):
    product_ids: List[str] = Field(default_factory=list)
    marketplace: str = "mercadolivre"
    include_shipping: bool = True
    include_promotions: bool = True


class AdsCreateRequest(BaseModel):
    marketplace: str = "mercadolivre"
    product_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class AlertsCreateRequest(BaseModel):
    name: str
    condition: Dict[str, Any] = Field(default_factory=dict)
    listing_id: Optional[str] = None
    is_active: bool = True


class AlertsUpdateRequest(BaseModel):
    name: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

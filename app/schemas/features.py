from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from app.models.plans import CurrencyEnum

class FeatureBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    is_base_feature: bool = True
    addon_price: Decimal = Field(default=0.00, ge=0)
    currency: CurrencyEnum = CurrencyEnum.INR
    status: str = "active"

class FeatureCreate(FeatureBase):
    pass

class FeatureOut(FeatureBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

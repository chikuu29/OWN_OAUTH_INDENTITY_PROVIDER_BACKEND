from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime
from app.models.plans import CountryEnum, CurrencyEnum
from app.schemas.features import FeatureCreate, FeatureOut

class AppPricingBase(BaseModel):
    price: Decimal = Field(..., ge=0)
    currency: CurrencyEnum = CurrencyEnum.INR
    country: CountryEnum = CountryEnum.IN
    is_active: bool = True

class AppPricingCreate(AppPricingBase):
    pass

class AppPricingOut(AppPricingBase):
    
    created_at: datetime
    class Config:
        from_attributes = True

class AppBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True

class AppCreate(AppBase):
    pricing: List[AppPricingCreate] = []
    features: List[FeatureCreate] = []

class AppOut(AppBase):
    id: UUID
    pricing: List[AppPricingOut]
    features: List[FeatureOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

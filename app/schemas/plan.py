from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

class CurrencyEnum(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class CountryEnum(str, Enum):
    IN = "IN"
    US = "US"
    EU = "EU"
    UK = "UK"

class BillingCycleEnum(str, Enum):
    monthly = "monthly"
    yearly = "yearly"

class PlanCreate(BaseModel):
    plan_code: str
    plan_name: str
    price: Decimal
    currency: CurrencyEnum
    country: CountryEnum
    billing_cycle: BillingCycleEnum
    max_users: Optional[int] = None
    max_branches: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    is_active: Optional[bool] = True

class PlanVersionOut(BaseModel):
    id: UUID
    version: int
    price: Decimal
    currency: CurrencyEnum
    country: CountryEnum
    billing_cycle: BillingCycleEnum
    max_users: Optional[int]
    max_branches: Optional[int]
    storage_limit_gb: Optional[int]
    effective_from: date
    is_current: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PlanOut(BaseModel):
    id: UUID
    plan_code: str
    name: str 
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    current_version: Optional[PlanVersionOut] = None
    versions: List[PlanVersionOut] = []

    class Config:
        from_attributes = True

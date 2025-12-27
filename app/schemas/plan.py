from pydantic import BaseModel
from typing import Optional
from enum import Enum
from uuid import UUID


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
    price: int
    currency: CurrencyEnum
    country: CountryEnum
    billing_cycle: BillingCycleEnum
    max_users: Optional[int] = None
    max_branches: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    is_active: Optional[bool] = True


class PlanOut(BaseModel):
    uuid: UUID
    id: int
    plan_code: str
    plan_name: str
    price: int
    currency: CurrencyEnum
    country: CountryEnum
    billing_cycle: BillingCycleEnum
    max_users: Optional[int]
    max_branches: Optional[int]
    storage_limit_gb: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True

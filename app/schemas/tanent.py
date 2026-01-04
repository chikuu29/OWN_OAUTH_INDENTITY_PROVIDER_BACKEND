from pydantic import BaseModel, EmailStr, model_validator, field_validator
from typing import Optional
from datetime import datetime, date

class TenantProfileBase(BaseModel):
    legal_name: Optional[str] = None
    industry: Optional[str] = None
    tax_id: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    business_email: Optional[EmailStr] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    owner_name: Optional[str] = None
    total_stores: Optional[int] = 1
    main_branch: Optional[str] = None
    estimated_annual_sales: Optional[str] = None
    business_type: Optional[str] = None
    founding_date: Optional[date] = None # Using date class
    timezone: Optional[str] = "UTC"
    currency: Optional[str] = "INR"

    @field_validator("founding_date", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

class TenantProfileCreate(TenantProfileBase):
    pass

class TenantProfileOut(TenantProfileBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TenantCreate(BaseModel):
    tenant_email: EmailStr
    tenant_name: str

    @model_validator(mode='before')
    def check_name_and_email(cls, values):
        tenant_name = values.get('tenant_name')
        tenant_email = values.get('tenant_email')

        if len(tenant_name) < 2:
            raise ValueError('Tenant name must be at least 2 characters long')

        if tenant_email and tenant_email.endswith("@example.com"):
            raise ValueError("Emails from example.com are not allowed.")

        return values

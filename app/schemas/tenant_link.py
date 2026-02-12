from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class TenantLinkOut(BaseModel):
    tenant_id: UUID
    request_type: str
    is_used: bool
    created_at: Optional[datetime]
    expires_at: Optional[datetime]
    class Config:
        from_attributes = True


class ActivationComplete(BaseModel):
    plan_uuid: Optional[UUID] = None
    admin_email: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    transaction_id: Optional[UUID] = None

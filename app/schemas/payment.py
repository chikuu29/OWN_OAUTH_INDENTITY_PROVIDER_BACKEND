from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from uuid import UUID

class CouponSchema(BaseModel):
    code: str
    percentage: float

class PaymentVerificationRequest(BaseModel):
    tenant_email: EmailStr
    tenant_name: str
    tenant_uuid: UUID
    plan_code: str
    current_version_id: UUID
    apps: List[UUID]
    features: Dict[UUID, List[str]] # appId -> list of feature codes
    coupon: Optional[CouponSchema] = None
    payment_method: str
    grand_total: float
    tax: float
    discount_amount: float
    taxable_amount: float
    subtotal: float
    tax_rate: float
    request_code: Optional[str] = None

class PaymentStatusRequest(BaseModel):
    tenant_id: Optional[UUID] = None
    tenant_uuid: Optional[UUID] = None
    plan_uuid: Optional[UUID] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_signature: Optional[str] = None
    transaction_id: Optional[UUID] = None
    token: Optional[str] = None

class PaymentStatusResponse(BaseModel):
    valid: bool
    status: str # SUCCESS, PENDING, FAILED
    subscription_status: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    transaction_id: Optional[UUID] = None
    amount: float
    currency: str = "INR"
    message: Optional[str] = None

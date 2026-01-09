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

class PaymentVerificationResponse(BaseModel):
    valid: bool
    razorpay_order_id: Optional[str] = None
    transaction_id: Optional[UUID] = None
    amount: float
    currency: str = "INR"
    key_id: Optional[str] = None # Send public key to frontend
    message: Optional[str] = None

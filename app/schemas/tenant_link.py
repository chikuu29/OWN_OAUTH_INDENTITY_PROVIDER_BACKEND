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
        orm_mode = True


class ActivationComplete(BaseModel):
    plan_uuid: Optional[UUID] = None
    admin_email: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None

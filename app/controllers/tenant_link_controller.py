from datetime import datetime, timedelta
from uuid import UUID
import secrets
import hashlib
import os
import jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant_link import TenantLink


JWT_ALGO = os.getenv("LINK_JWT_ALGO", "HS256")
JWT_SECRET = os.getenv("LINK_JWT_SECRET", os.getenv("JWT_SECRET", "change-me"))


async def create_tenant_link(db: AsyncSession, tenant_uuid: str, hours_valid: int = 24, extra_payload: dict = None):
    if isinstance(tenant_uuid, str):
        try:
            tenant_uuid_obj = UUID(tenant_uuid)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {tenant_uuid}")
    else:
        tenant_uuid_obj = tenant_uuid

    # Find tenant_id from tenant_uuid to satisfy DB constraint or payload
    from app.models.tenant import Tenant
    result = await db.execute(select(Tenant.id).filter(Tenant.tenant_uuid == tenant_uuid_obj))
    tenant_id = result.scalar()
    
    if not tenant_id:
        raise ValueError(f"Tenant with UUID {tenant_uuid} not found")

    # Create a signed JWT token containing tenant_id and expiry
    expires_at = TenantLink.default_expires_at(hours=hours_valid)
    payload = {
        "tenant_id": tenant_id,
        "tenant_uuid": tenant_uuid,
        "exp": int(expires_at.timestamp()),
        "type": "activation",
    }
    
    if extra_payload:
        payload.update(extra_payload)
    print(payload)
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

    # store only hash of token
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    link = TenantLink(tenant_id=tenant_uuid_obj, token_hash=token_hash, expires_at=expires_at)
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return link, token


async def get_tenant_link(db: AsyncSession, raw_token: str):
    # Hash incoming token and lookup
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(TenantLink).filter(TenantLink.token_hash == token_hash))
    return result.scalars().first()


async def mark_link_used(db: AsyncSession, link: TenantLink):
    link.is_used = True
    await db.commit()
    await db.refresh(link)
    return link

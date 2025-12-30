from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status,BackgroundTasks
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.auth import User
from app.schemas.tanent import TenantCreate

# from app.crud.client import create_oauth_client
from app.controllers.account_controller import create_tenant, register_user
from app.controllers.tenant_link_controller import create_tenant_link, get_tenant_link, mark_link_used
from app.controllers.plan_controller import get_plan
from app.models.subscriptions import Subscription
from datetime import datetime, timedelta, timezone
from uuid import UUID
import os
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler, APIResponse
from app.models.tenant import Role, Tenant
from app.schemas.auth_schemas import UserRegisterSchema
from app.core.db_helpers import model_to_dict
from sqlalchemy.orm import selectinload
from app.services.email_service import send_tenant_registration_email
from app.schemas.tenant_link import TenantLinkOut
from app.schemas.tenant_link import ActivationComplete
from app.models.subscriptions import Subscription
from app.models.plans import Plan
from app.models.tenant import TenantStatusEnum
# tenant link helpers imported above


router = APIRouter(
    prefix="/account",  # Optional: Define a prefix for all client routes
    tags=["account"],  # Optional: Add a tag for better documentation grouping
)


@router.post("/register/auth_user", response_model=APIResponse)
async def register_authuser(
    user: UserRegisterSchema, db: AsyncSession = Depends(get_db)
):
    print("====CALLING REGISTER AUTH USER===")
    try:
        user_data = await register_user(db, user)

        user_data = model_to_dict(user_data, exclude_fields=["hashed_password"])

        return ResponseHandler.success(
            message="User registration successful", data=[user_data]
        )

    except Exception as e:
        # Handle any unexpected errors
        # print(type(e))
        # print(e)
        # error_dict = {"error": "Validation Error", "message": str(e)}
        return ResponseHandler.error(
            message="User registration failed", error_details=e.args[0]
        )


@router.get("/auth_users")
async def get_oauth_users(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),  # Default page = 1 (>=1)
    limit: int = Query(10, le=100),  # Max limit = 100
):
    # Calculate offset for pagination
    offset = (page - 1) * limit

    # Fetch total records for pagination meta
    total = await db.scalar(select(func.count()).select_from(User))

    # Fetch paginated results
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).offset(offset).limit(limit)
    )
    users = result.scalars().all()

    if not users:
        raise HTTPException(status_code=404, detail="No auth user found")

    return {
        "message": "Auth Users fetched successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),  # Total pages
        "data": [user.to_dict(include_tenat=False) for user in users],
        "success": True,
    }


@router.post("/register/tenant/", response_model=APIResponse)
async def register_tanets(client: TenantCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    print(f"==CALLING register_tanets====")
    print(f"Client", client)
    try:
        db_client = await create_tenant(db=db, client=client)

        # Create activation link valid for 24 hours (returns DB link and raw token)
        link, raw_token = await create_tenant_link(db=db, tenant_id=db_client.id, hours_valid=24)

        # Build activation URL using DOMAIN_NAME env if available (send raw token)
        DOMAIN = os.getenv("DOMAIN_NAME", "http://localhost:8000")
        activation_url = f"{DOMAIN}/account/activate/{raw_token}"

        # Send activation email in background (will await coroutine when run)
        background_tasks.add_task(
            send_tenant_registration_email,
            db_client.tenant_email,
            db_client.tenant_name,
            activation_url,
        )

        return ResponseHandler.success(
            message="Tenant registered successfully", data=[db_client.to_dict()]
        )

    except Exception as e:
        # Handle any unexpected errors
        return ResponseHandler.error(
            message="Tenant registration failed", error_details={"detail": str(e)}
        )


@router.get("/tenants")
async def get_tenant(
    tenant_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),  # Default page = 1 (>=1)
    limit: int = Query(10, le=100),
):  
    # Calculate offset for pagination
    offset = (page - 1) * limit

    if tenant_id:
        # Fetch specific tenant
        result = await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
        tenant = result.scalars().first()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        return {
            "message": "Tenant fetched successfully",
            "total": 1,
            "page": 1,
            "limit": 1,
            "pages": 1,
            "data": [tenant.to_dict()],
            "success": True,
        }

    # Fetch total records for pagination
    total = await db.scalar(select(func.count()).select_from(Tenant))

    # Fetch all tenants with pagination
    result = await db.execute(select(Tenant).offset(offset).limit(limit))
    tenants = result.unique().scalars().all()

    return {
        "message": "Tenants fetched successfully",
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total // limit) + (1 if total % limit != 0 else 0),  # Total pages calculation
        "data": [tenant.to_dict() for tenant in tenants],
        "success": True,
    }


@router.get("/tenants-with-roles")
async def get_tenants_with_roles(db: AsyncSession = Depends(get_db)):
    # Fetch all tenants and their roles
    result = await db.execute(select(Tenant).options(selectinload(Tenant.roles)))
    tenants = result.scalars().all()

    # Transform data to desired structure
    tenants_with_roles = [
        {
            "tenant_id": tenant.tenant_id,
            "name": tenant.tenant_name,
            "roles": [role.role_name for role in tenant.roles],
            "isActive": tenant.tenant_active,
            "created_at": tenant.created_at
        }
        for tenant in tenants
    ]

    return tenants_with_roles


@router.get("/activate/{token}", response_model=APIResponse)
async def validate_activation_link(token: str, db: AsyncSession = Depends(get_db)):
    try:
        link = await get_tenant_link(db, token)
        if not link:
            return ResponseHandler.not_found(message="Activation link not found")

        if link.is_used:
            return ResponseHandler.error(message="Activation link already used", error_details={"token": token})

        if link.expires_at and link.expires_at < datetime.now(timezone.utc):
            return ResponseHandler.error(message="Activation link expired", error_details={"token": token})

        data = [{
            "tenant_id": link.tenant_id,
            "request_type": link.request_type,
            "is_used": link.is_used,
            "created_at": link.created_at.isoformat() if link.created_at else None,
            "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        }]

        return ResponseHandler.success(message="Activation link valid", data=data)

    except Exception as e:
        return ResponseHandler.error(message="Failed to validate link", error_details={"detail": str(e)})


# @router.post("/activate/{token}/complete", response_model=APIResponse)
# async def complete_activation(token: str, payload: ActivationComplete, db: AsyncSession = Depends(get_db)):
#     try:
#         link = await get_tenant_link(db, token)
#         if not link:
#             return ResponseHandler.not_found(message="Activation link not found")

#         if link.is_used:
#             return ResponseHandler.error(message="Activation link already used", error_details={"token": token})

#         if link.expires_at and link.expires_at < datetime.now(timezone.utc):
#             return ResponseHandler.error(message="Activation link expired", error_details={"token": token})

#         # Activate tenant
#         result = await db.execute(select(Tenant).filter(Tenant.id == link.tenant_id))
#         tenant = result.scalars().first()
#         if not tenant:
#             return ResponseHandler.not_found(message="Tenant not found for link", error_details={"tenant_id": link.tenant_id})

#         # If a plan is provided, create subscription
#         subscription_info = None
#         if payload.plan_uuid:
#             plan = await get_plan(db, payload.plan_uuid)
#             if not plan:
#                 return ResponseHandler.not_found(message="Plan not found", error_details={"plan_uuid": str(payload.plan_uuid)})

#             start_date = datetime.now(timezone.utc)
#             if getattr(plan.billing_cycle, "value", str(plan.billing_cycle)) == "monthly":
#                 end_date = start_date + timedelta(days=30)
#             else:
#                 end_date = start_date + timedelta(days=365)

#             subscription = Subscription(
#                 tenant_id=tenant.id,
#                 plan_id=plan.id,
#                 status=SubscriptionStatusEnum.active,
#                 start_date=start_date,
#                 end_date=end_date,
#                 currency=plan.currency,
#                 country=plan.country,
#                 auto_renew=True,
#             )
#             db.add(subscription)
#             await db.commit()
#             await db.refresh(subscription)
#             subscription_info = {
#                 "id": subscription.id,
#                 "plan_id": subscription.plan_id,
#                 "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
#                 "end_date": subscription.end_date.isoformat() if subscription.end_date else None,
#             }

#         # Mark tenant active
#         tenant.is_active = True
#         tenant.status = TenantStatusEnum.active
#         await db.commit()

#         # Mark link used
#         await mark_link_used(db, link)

#         response_data = {"tenant": tenant.to_dict()}
#         if subscription_info:
#             response_data["subscription"] = subscription_info

#         return ResponseHandler.success(message="Activation completed", data=[response_data])

#     except Exception as e:
#         return ResponseHandler.error(message="Failed to complete activation", error_details={"detail": str(e)})






















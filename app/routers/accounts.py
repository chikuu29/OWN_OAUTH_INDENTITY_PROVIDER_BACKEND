from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.auth import User
from app.schemas.tanent import TenantCreate

# from app.crud.client import create_oauth_client
from app.controllers.account_controller import create_tenant, register_user
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ResponseHandler, APIResponse
from app.models.tenant import Tenant
from app.schemas.auth_schemas import UserRegisterSchema
from app.core.db_helpers import model_to_dict
from sqlalchemy.orm import selectinload


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
async def register_tanets(client: TenantCreate, db: AsyncSession = Depends(get_db)):
    print(f"==CALLING register_tanets====")
    print(f"Client", client)
    try:
        db_client = await create_tenant(db=db, client=client)
        # print('db_client',to_dict(db_client))
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
            "id": tenant.tenant_id,
            "name": tenant.tenant_name,
            "roles": [role.role_name for role in tenant.roles],
            "isActive": tenant.tenant_active,
            "created_at": tenant.created_at
        }
        for tenant in tenants
    ]

    return tenants_with_roles
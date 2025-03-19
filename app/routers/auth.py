from datetime import timedelta
import json
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.response import APIResponse, ResponseHandler
from app.core.security.authentications import getRequestIdentity
from app.core.security.oauth_token_service import generate_oauth_tokens, validate_token
from app.db.database import get_db
from app.models.auth import User
from app.models.tenant import Permission, Role, ScopeEnum, Tenant
from app.schemas.auth_schemas import (
    LoginSchema,
    LoginResponse,
    PermissionBulkCreate,
    RoleCreate,
)
from app.controllers.auth_controller import authenticateLoginUser
# from app.core.osecurity import create_jwt_token, verify_token
from app.core.security.oauth_token_service import validate_token
from sqlalchemy.orm import joinedload, selectinload
from uuid import UUID

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter(
    prefix="/auth",  # Optional: Define a prefix for all client routes
    tags=["authentication"],  # Optional: Add a tag for better documentation grouping
)


# Dependency to extract and verify the access token
def get_current_user(access_token: str = Depends(oauth2_scheme)):
    return validate_token(access_token)


# 🚀 Login User & Get Tokens
@router.post("/login", response_model=LoginResponse)
async def login(
    response: Response,
    loginData: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticateLoginUser(db, loginData)

        # {
        #   "sub": "user123",         // Subject (User ID or Username)
        #   "name": "Jiggu",         // Optional User Information
        #   "email": "jiggu@example.com",
        #   "role": "admin",         // User Role
        #   "exp": 1707849600,       // Expiration Timestamp (Unix Time)
        #   "iat": 1707846000,       // Issued At Timestamp
        #   "iss": "your-api.com",   // Issuer
        #   "aud": "your-client-id"  // Audience (Optional)
        # }
        payload = {
            "sub": user.username,
            "email": user.email,
            "username": user.username,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "userFullName": f"{user.first_name} {user.last_name}",
            "tanent_id": user.tenant_id,
            "tenant_name": user.tenant.tenant_name,
        }

        access_token, refresh_token, *_ = generate_oauth_tokens(payload)
        # access_token = create_jwt_token(payload, timedelta(minutes=7))
        # refresh_token = create_jwt_token(payload, timedelta(days=7))

        # 🍪 Set HTTP cookies
        # response.set_cookie(
        #     key="access_token",
        #     value=access_token,
        #     httponly=True,  # Prevent access via JavaScript
        #     secure=True,  # Use HTTPS
        #     samesite="Lax",
        #     max_age=7 * 60  # 7 minutes
        # )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            authProvider="credentials",
            token_type="bearer",
            login_info={
                "email": user.email,
                "username": user.username,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "userFullName": f"{user.first_name} {user.last_name}",
                "phone": user.phone_number,
            },
            success=True,
            message="Login successful",
            error=None,
        )
    except HTTPException as e:
        return LoginResponse(
            access_token=None,
            refresh_token=None,
            authProvider="credentials",
            login_info={},
            success=False,
            message=str(e.detail),
            error={"detail": str(e.detail)},
        )


@router.get("/me")
async def identity(refresh_token: Annotated[str | None, Cookie()] = None):
    print(f"refresh_token", refresh_token)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token found"
        )
    payload = await validate_token(TOKEN=refresh_token)
    # payload = verify_token(refresh_token, "REFRESH_SECRET_KEY")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    print("payload", payload)
    # access_token = create_jwt_token(payload, timedelta(minutes=7))
    access_token, *_ = generate_oauth_tokens(payload, False, False)
    print("access_token", access_token)
    return {
        "access_token": access_token,
        "authProvider": "credentials",
        "token_type": "bearer",
        "login_info": payload,
        "success": True,
        "message": "ReLogin successful",
        "error": None,
    }


@router.post("/logout")
def logout(response: Response, token: str = Depends(oauth2_scheme)):
    """Logout by deleting authentication cookies"""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully", "success": True}


@router.get("/userinfo")
async def userInfo(
    identity: dict = Depends(getRequestIdentity), db: AsyncSession = Depends(get_db)
):
    """
    Fetch user info based on the authenticated user's identity.
    """
    print("Identity:", identity)

    if not identity or "sub" not in identity:
        return {"error": "Invalid identity"}

    result = await db.execute(
        select(User)
        .options(
            joinedload(User.profile), joinedload(User.tenant)
        )  # 👈 Use only joinedload()
        .filter(User.username == identity.get("sub"))
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "tenant": user.tenant.to_dict() if user.tenant else None,
        "profile": {
            "bio": user.profile.bio if user.profile else None,
            "profile_picture": user.profile.profile_picture if user.profile else None,
            "address": user.profile.address if user.profile else None,
            "city": user.profile.city if user.profile else None,
            "country": user.profile.country if user.profile else None,
        },
    }


@router.post("/roles/")
async def create_role(role_data: RoleCreate, db: AsyncSession = Depends(get_db)):
    # Check if role already exists for this tenant
    existing_role = await db.execute(
        select(Role).filter(
            Role.role_name == role_data.role_name, Role.tenant_id == role_data.tenant_id
        )
    )
    if existing_role.scalars().first():
        raise HTTPException(
            status_code=400, detail="Role with this name already exists for the tenant."
        )

    # Create new Role
    new_role = Role(
        role_name=role_data.role_name,
        is_active=role_data.is_active,
        tenant_id=role_data.tenant_id,
        description=role_data.description
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    # Add Permissions
    for perm in role_data.permissions:
        new_permission = Permission(
            permission_name=perm.permission_name,
            scopes=perm.scopes,
            description=perm.description,
            role_id=new_role.id,
        )
        db.add(new_permission)

    await db.commit()
    return {"message": "Role created successfully", "role_id": new_role.id}


@router.get("/roles/{tenant_id}", response_model=APIResponse)
async def get_roles(tenant_id: UUID, db: AsyncSession = Depends(get_db)):
    # Fetch tenant by tenant_id with roles
    result = await db.execute(select(Role).filter(Role.tenant_id == tenant_id))
    roles = result.scalars().unique().all()

    # Check if tenant exists
    if not roles:
        return ResponseHandler.error(message="Roles not found")
        # raise HTTPException(status_code=404, detail="roles not found")

    # Extract roles for the specific tenant
    # roles = [{roles:role.role_name,permissions:role} for role in tenant.roles]
    roles_data = [role.to_dict() for role in roles]
    return APIResponse(success=True, data=roles_data, message="Roles fetched successfully")
    return {"success": True, "data": roles_data}


@router.post("/permissions/")
async def create_permissions(
    permission_data: PermissionBulkCreate, db: AsyncSession = Depends(get_db)
):
    # Check if the role exists
    role = await db.execute(select(Role).filter(Role.id == permission_data.role_id))
    role = role.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")
    print("role", role)
    print("permission_data", permission_data)
    # Get existing permissions for this role
    existing_permissions = await db.execute(
        select(Permission).filter(Permission.role_id == permission_data.role_id)
    )
    existing_permission_names = {
        permission.permission_name
        for permission in existing_permissions.scalars().all()
    }
    print("existing_permission_names", existing_permission_names)
    # Validate and create new permissions
    new_permissions = []
    for perm in permission_data.permissions:
        if perm.permission_name in existing_permission_names:
            continue  # Skip if permission already exists

        # Validate scope
        invalid_scopes = [s for s in perm.scopes if s not in ScopeEnum.__members__]
        if invalid_scopes:
            raise HTTPException(
                status_code=400, detail=f"Invalid scopes: {', '.join(invalid_scopes)}"
            )

        new_permissions.append(
            Permission(
                permission_name=perm.permission_name,
                scopes=perm.scopes,  # Store as JSON
                description=perm.description,
                role_id=permission_data.role_id,
            )
        )

    print("new_permissions", new_permissions)
    # If no valid new permissions, return an error
    if not new_permissions:
        raise HTTPException(
            status_code=400, detail="All permissions already exist for this role."
        )

    db.add_all(new_permissions)
    await db.commit()

    return {
        "message": "Permissions added successfully",
        "added_permissions": [perm.permission_name for perm in new_permissions],
    }

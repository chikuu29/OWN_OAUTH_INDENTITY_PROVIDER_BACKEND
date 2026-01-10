from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from uuid import UUID
from typing import Optional

from app.schemas.tanent import TenantCreate
from app.schemas.auth_schemas import UserRegisterSchema
from app.models.tenant import Tenant
from app.models.auth import User, UserProfile


pwd_context = CryptContext(schemes=["bcrypt"])


class AccountController:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(self, client: TenantCreate):
        """Create a new tenant"""
        result = await self.db.execute(
            select(Tenant).filter(
                or_(
                    Tenant.tenant_name == str(client.tenant_name).lower(),
                    Tenant.tenant_email == client.tenant_email,
                )
            )
        )
        existing_in_db = result.scalars().first()

        if existing_in_db:
            raise ValueError("Tenant with this name or email already exists")

        db_client = Tenant(
            tenant_name=str(client.tenant_name).lower(),
            tenant_email=client.tenant_email
        )

        self.db.add(db_client)
        await self.db.commit()
        await self.db.refresh(db_client)

        return db_client

    async def register_user(self, user_data: UserRegisterSchema, is_active: bool = True, is_root_user: bool = False, is_superuser: bool = False):
        """Register a new user"""
        result = await self.db.execute(
            select(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            raise ValueError(
                {
                    "value": {
                        "username": {"msg": "Username may be already exists"},
                        "email": {"msg": "Email may be already exists"},
                    }
                }
            )

        tenant_result = await self.db.execute(
            select(Tenant).filter(Tenant.tenant_name == user_data.tenant_name)
        )
        tenant = tenant_result.scalars().first()
        if not tenant:
            raise ValueError(
                {"value": {"tenant_name": {"msg": "Invalid tenant name or May not found"}}}
            )

        new_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            email=user_data.email,
            phone_number=user_data.phone_number,
            hashed_password=pwd_context.hash(user_data.password),
            tenant_id=tenant.id,
            is_active=is_active,
            is_root_user=is_root_user,
            is_superuser=is_superuser,
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        if user_data.profile:
            user_profile = UserProfile(
                user_id=new_user.id,
                bio=user_data.profile.bio,
                profile_picture=user_data.profile.profile_picture,
                address=user_data.profile.address,
                city=user_data.profile.city,
                country=user_data.profile.country,
            )
            self.db.add(user_profile)
            await self.db.commit()

        return new_user

    async def create_root_user(self, tenant_id: int, tenant_email: str, tenant_name: str):
        """
        Create a root/admin user for a tenant upon subscription activation.
        Uses tenant email as username and generates a default password.
        """
        # Check if root user already exists
        result = await self.db.execute(
            select(User).filter(
                (User.tenant_id == tenant_id) & (User.email == tenant_email)
            )
        )
        existing_user = result.scalars().first()

        if existing_user:
            # Root user already exists, skip creation
            return existing_user, None

        # Generate a default password (tenant should change this later)
        default_password = f"Welcome@{tenant_name[:8]}123"

        # Build registration schema to reuse validation and profile handling
        root_user_data = UserRegisterSchema(
            first_name="Admin",
            last_name="User",
            username=tenant_email,
            email=tenant_email,
            phone_number=None,
            password=default_password,
            tenant_name=tenant_name,
            profile=None,
        )

        # Use the existing register_user method to create the root user
        root_user = await self.register_user(
            root_user_data, 
            is_active=True, 
            is_root_user=True, 
            is_superuser=False
        )
        return root_user, default_password


# Legacy function wrappers for backward compatibility
async def create_tenant(db: Session, client: TenantCreate):
    controller = AccountController(db)
    return await controller.create_tenant(client)


async def register_user(db: Session, user_data: UserRegisterSchema):
    controller = AccountController(db)
    return await controller.register_user(user_data)

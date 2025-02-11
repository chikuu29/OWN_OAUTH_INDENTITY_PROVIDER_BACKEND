from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.schemas.tanent import TenantCreate
from app.schemas.auth_schemas import UserRegisterSchema
from app.models.tenant import Tenant
from sqlalchemy.future import select

from app.models.auth import User, UserProfile

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])


async def create_tenant(db: Session, client: TenantCreate):
    # Check if the client_id already exists to avoid duplicates

    result = await db.execute(
        select(Tenant).filter(
            or_(
                Tenant.tenant_name == client.tenant_name,
                Tenant.tenant_email
                == client.tenant_email,  # Either name or email should be unique
            )
        )
    )
    existing_in_db = result.scalars().first()

    if existing_in_db:
        raise ValueError("Tenant with this name or email already exists")

    # Create a new OAuth client
    db_client = Tenant(tenant_name=client.tenant_name, tenant_email=client.tenant_email)

    # Add and commit the new client to the database asynchronously
    db.add(db_client)
    await db.commit()

    # Refresh to load the latest state of the client object
    await db.refresh(db_client)

    return db_client


async def register_user(db: Session, user_data: UserRegisterSchema):
    # Check if user exists
    result = await db.execute(
        select(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise ValueError(
            {
                "value": {
                    "username": {"msg": "Username may be  already exists"},
                    "email": {"msg": "Email may be  already exists"},
                }
            }
        )

    # Find Tenant
    tenant_result = await db.execute(
        select(Tenant).filter(Tenant.tenant_name == user_data.tenant_name)
    )
    tenant = tenant_result.scalars().first()
    if not tenant:
        raise ValueError(
            {"value": {"tenant_name": {"msg": "Invalid tenant name or May not found"}}}
        )

    # Create User
    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username,
        email=user_data.email,
        phone_number=user_data.phone_number,
        hashed_password=pwd_context.hash(user_data.password),
        tenant_id=tenant.id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create User Profile (Optional)
    if user_data.profile:
        user_profile = UserProfile(
            user_id=new_user.id,
            bio=user_data.profile.bio,
            profile_picture=user_data.profile.profile_picture,
            address=user_data.profile.address,
            city=user_data.profile.city,
            country=user_data.profile.country,
        )
        db.add(user_profile)
        await db.commit()
    
   
    return new_user

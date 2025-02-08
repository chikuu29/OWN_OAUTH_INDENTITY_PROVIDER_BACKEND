from pydantic import BaseModel, EmailStr
from typing import Optional

class UserProfileSchema(BaseModel):
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class UserRegisterSchema(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    phone_number: str
    password: str  # Raw password before hashing
    tenant_name: str  # Tenant name instead of ID
    profile: Optional[UserProfileSchema] = None



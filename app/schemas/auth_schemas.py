import enum
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
import uuid
from sqlalchemy import UUID

class ScopeEnum(str, enum.Enum):
    read = "read"
    write = "write"
    edit = "edit"
    delete = "delete"

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



class LoginSchema(BaseModel):
    username:str
    password:str



class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    authProvider: str
    login_info: Dict
    success: bool
    message: str
    error: Optional[Dict] = None  # Optional to handle cases with no errors


# Pydantic Schemas
class PermissionCreate(BaseModel):
    permission_name: str
    scopes: list[ScopeEnum]
    description: str | None = None

class RoleCreate(BaseModel):
    role_name: str
    is_active: bool = True
    tenant_id: uuid.UUID
    permissions: Optional[List[PermissionCreate]] = []

class PermissionBulkCreate(BaseModel):
    role_id: int
    # role_name: Optional[str]
    permissions: List[PermissionCreate]
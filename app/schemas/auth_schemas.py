from pydantic import BaseModel, EmailStr
from typing import Dict, Optional

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
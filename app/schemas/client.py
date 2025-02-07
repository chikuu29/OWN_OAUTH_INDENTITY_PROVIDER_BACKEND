from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field,field_validator
from typing import Optional

class OAuthClientCreate(BaseModel):
    name: str
    client_id: str=Field(..., min_length=6, max_length=50)
    client_secret: str=Field(..., min_length=8, max_length=128)
    client_type: str
    authorization_grant_type: str
    redirect_urls: Optional[str] = None
    post_logout_redirect_uris: Optional[str] = None
    allowed_origins: Optional[str] = None
    algorithm: Optional[str] = "HS256"

    model_config = ConfigDict(from_attributes=True)


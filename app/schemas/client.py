from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field,field_validator
from typing import List, Optional

class OAuthClientCreate(BaseModel):
    client_name: str  # Updated field name to match the SQLAlchemy model
    client_id: str = Field(..., min_length=6, max_length=50)
    client_secret: str = Field(..., min_length=8, max_length=128)
    client_type: str
    authorization_grant_types: List[str]  # Changed to List[str] to reflect JSONB in DB
    redirect_urls: List[str]  # Changed to List[str] to reflect JSONB in DB
    post_logout_redirect_urls: Optional[List[str]] = None  # Optional, List of strings
    allowed_origins: Optional[List[str]] = None  # Optional, List of strings
    token_endpoint_auth_method: Optional[str]  # Added to match the new field in the model
    scope: List[str]  # Changed to List[str] to reflect JSONB in DB
    response_types: List[str]  # Added this field to match the new model
    grant_types: List[str]  # Added this field to match the new model
    algorithm: Optional[str] = "HS256"  # Default value as "HS256"

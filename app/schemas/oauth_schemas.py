from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class OauthResponse(BaseModel):
    login_info: Optional[Dict]=None
    success: bool
    data: Optional[Dict] = None
    message: str
    error: Optional[Dict] = None  # Optional to handle cases with no errors


class OauthRequest(BaseModel):
    client_id: str
    redirect_url: str
    response_type: str="code"
    scope: str
    state: Optional[str] = None
    device_id: str


class TokenRequest(BaseModel):
    grant_type: str  # OAuth2 grant type (authorization_code, refresh_token, password)
    code: Optional[str] = None  # For authorization_code flow
    refresh_token: Optional[str] = None  # For refresh_token flow
    username: Optional[str] = None  # For password grant type
    password: Optional[str] = None  # For password grant type
    client_id: str  # Client ID issued by the authorization server
    client_secret: str  # Client Secret issued by the authorization server
    device_id:str





class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    refresh_exp: Optional[datetime] = None  # Changed to datetime for better date handling
    id_token_exp: Optional[datetime] = None
    access_exp: Optional[datetime] = None
    authProvider: Optional[str] = None
    login_info: Optional[Dict] = None
    success: bool
    message: str
    errors: Optional[Dict] = None  # Optional to handle cases with no errors
    # class Config:
    #     json_encoders = {
    #         datetime: lambda v: v.isoformat() # Convert datetime to ISO format with 'Z' for UTC
    #     }
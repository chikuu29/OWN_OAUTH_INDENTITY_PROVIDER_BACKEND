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
from pydantic import BaseModel

class OAuthClientCreate(BaseModel):
    client_id: str
    client_secret: str
    redirect_url: str
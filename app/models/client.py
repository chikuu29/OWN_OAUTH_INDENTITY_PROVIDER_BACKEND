

#app/models/client.py
from sqlalchemy import Column, DateTime, Integer, String
from app.db.database import Base
from datetime import datetime
from sqlalchemy.orm import validates
from passlib.context import CryptContext


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class OAuthClient(Base):
    __tablename__ = 'oauth_clients'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Added name
    client_id = Column(String, unique=True, index=True)
    client_secret = Column(String, nullable=False)
    hash_client_secret = Column(String, nullable=True)  # Added hashed secret
    client_type = Column(String, nullable=False)  # Added client type
    authorization_grant_type = Column(String, nullable=False)  # Added grant type
    redirect_urls = Column(String, nullable=True)  # Added redirect URIs
    post_logout_redirect_uris = Column(String, nullable=True)  # Added logout URIs
    allowed_origins = Column(String, nullable=True)  # Added allowed origins
    algorithm = Column(String, nullable=False, default="HS256")  # Added algorithm
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @validates("client_secret")
    def hash_client_secret(self, key, value):
        """Hash client_secret before storing it."""
        return pwd_context.hash(value)
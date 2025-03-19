from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.db.database import Base
from datetime import datetime
from sqlalchemy.orm import validates
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import JSONB

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)  # Updated from 'name'
    client_id = Column(String, unique=True, index=True)
    client_secret = Column(String, nullable=False)
    hash_client_secret = Column(String, nullable=False)
    client_type = Column(String, nullable=False)
    authorization_grant_types = Column(JSONB, nullable=False)  # Changed to JSONB list
    redirect_urls = Column(JSONB, nullable=False)  # Changed to JSONB
    post_logout_redirect_urls = Column(JSONB, nullable=True)
    skip_authorization = Column(
        Boolean, nullable=True, default=False
    )  # Added this field
    allowed_origins = Column(JSONB, nullable=True)
    token_endpoint_auth_method = Column(String, nullable=False)  # Added this field
    scope = Column(JSONB, nullable=False)  # Changed from 'scopes'
    response_types = Column(JSONB, nullable=False)  # Added this field
    grant_types = Column(JSONB, nullable=False)  # Added explicitly for flexibility
    algorithm = Column(String, nullable=False, default="HS256")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=True)

    @validates("client_secret")
    def validate_and_hash_client_secret(self, key, value):
        """Hash client_secret before storing it."""

        self.hash_client_secret = pwd_context.hash(value)
        return value  # Keep the plain client_secret for temporary use if needed

    def verify_client_secret(self, plain_secret: str) -> bool:
        """Verify provided client_secret against hashed version."""
        return pwd_context.verify(plain_secret, self.hash_client_secret)

    def to_dict(self):
        """Convert model instance to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "client_name": self.client_name,
            "client_id": self.client_id,
            "client_type": self.client_type,
            "authorization_grant_types": self.authorization_grant_types,
            "redirect_urls": self.redirect_urls,
            "post_logout_redirect_urls": self.post_logout_redirect_urls,
            "skip_authorization": self.skip_authorization,
            "allowed_origins": self.allowed_origins,
            "token_endpoint_auth_method": self.token_endpoint_auth_method,
            "scope": self.scope,
            "response_types": self.response_types,
            "grant_types": self.grant_types,
            "algorithm": self.algorithm,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

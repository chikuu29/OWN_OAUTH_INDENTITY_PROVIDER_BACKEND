
from datetime import datetime
from sqlalchemy import UUID, Boolean, Column, DateTime, Integer, String
from app.db.database import Base
import uuid


class Tenant(Base):
    __tablename__ = 'auth_tenants'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)  # Explicitly defined auto-increment ID
    tenant_id = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False)  # UUID for external use
    tenant_name = Column(String(255), unique=True, nullable=False)
    tenant_email = Column(String, unique=True, nullable=False)
    tenant_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "tenant_id": str(self.tenant_id),  # Convert UUID to string
            "tenant_email": self.tenant_email,
            "tenant_name": self.tenant_name,
            "created_at":self.created_at,
            "tenant_active":self.tenant_active
        }
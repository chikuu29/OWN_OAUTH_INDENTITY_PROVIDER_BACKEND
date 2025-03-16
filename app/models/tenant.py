from datetime import datetime
import enum
from sqlalchemy import (
    ARRAY,
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Enum
)
from app.db.database import Base
import uuid
from sqlalchemy.orm import relationship

# Enum for Permission Scope
class ScopeEnum(str, enum.Enum):
    read = "read"
    write = "write"
    edit = "edit"
    delete = "delete"


class Tenant(Base):
    __tablename__ = "auth_tenants"

    id = Column(
        Integer, primary_key=True, autoincrement=True, index=True
    )  # Explicitly defined auto-increment ID
    tenant_id = Column(
        UUID(as_uuid=True), unique=True, default=uuid.uuid4, nullable=False
    )  # UUID for external use
    tenant_name = Column(String(255), unique=True, nullable=False)
    tenant_email = Column(String, unique=True, nullable=False)
    tenant_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    # Relationship with Role
    roles = relationship("Role", back_populates="tenant", cascade="all, delete-orphan",lazy='joined')

    def to_dict(self):
        return {
            "tenant_id": str(self.tenant_id),  # Convert UUID to string
            "tenant_email": self.tenant_email,
            "tenant_name": self.tenant_name,
            "created_at": self.created_at,
            "tenant_active": self.tenant_active,
            "roles": [role.to_dict() for role in self.roles],
        }


class Role(Base):
    __tablename__ = "auth_roles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    role_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Foreign key to Tenant
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("auth_tenants.tenant_id"), nullable=False
    )

    # Relationship back to Tenant
    tenant = relationship("Tenant", back_populates="roles")
    # One-to-Many Relationship with Permission
    permissions = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan",lazy='joined'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "role_name": self.role_name,
            "is_active": self.is_active,
            "permissions": [permission.to_dict() for permission in self.permissions],
        }


class Permission(Base):
    __tablename__ = 'auth_permissions'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    permission_name = Column(String(255), nullable=False)
      # Use ARRAY to store multiple scopes (for PostgreSQL)
    scopes = Column(ARRAY(String), nullable=False)    # Enum for read, write, edit, delete
    description = Column(String(500), nullable=True)

    # Foreign key to Role
    role_id = Column(Integer, ForeignKey('auth_roles.id'), nullable=False)

    # Relationship back to Role
    role = relationship("Role", back_populates="permissions")

    def to_dict(self):
        return {
            "id": self.id,
            "permission_name": self.permission_name,
            "scopes": self.scopes,  # Return enum value
            "description": self.description,
        }

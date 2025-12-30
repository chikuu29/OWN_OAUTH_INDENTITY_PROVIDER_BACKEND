from datetime import datetime, timezone
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
    Enum,
    func,
    UniqueConstraint
)
from app.db.database import Base
import uuid
from sqlalchemy.orm import relationship


class TenantStatusEnum(str, enum.Enum):
    invited = "invited"
    active = "active"
    suspended = "suspended"
    deleted = "deleted"
    pending = "pending"


# Enum for Permission Scope
class ScopeEnum(str, enum.Enum):
    read = "read"
    write = "write"
    edit = "edit"
    delete = "delete"


class DeploymentEnum(str, enum.Enum):
    shared = "shared"
    dedicated = "dedicated"


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    tenant_name = Column(String(255), unique=True, nullable=False)
    tenant_email = Column(String(255), unique=True, nullable=False)

    is_active = Column(Boolean, default=False, nullable=False)

    status = Column(
        Enum(TenantStatusEnum, name="tenant_status_enum"),
        default=TenantStatusEnum.invited,
        nullable=False,
    )

    deployment_type = Column(
        Enum(DeploymentEnum, name="deployment_enum"),
        default=DeploymentEnum.shared,
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    roles = relationship(
        "Role",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscription = relationship(
        "Subscription",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "tenant_uuid": str(self.tenant_uuid),
            "tenant_name": self.tenant_name,
            "tenant_email": self.tenant_email,
            "is_active": self.is_active,
            "status": self.status.value,
            "deployment_type": self.deployment_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Role(Base):
    __tablename__ = "auth_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_name", name="uq_role_per_tenant"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(255), nullable=False)
    description = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant = relationship("Tenant", back_populates="roles")

    permissions = relationship(
        "Permission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "role_name": self.role_name,
            "description": self.description,
            "is_active": self.is_active,
            "permissions": [p.to_dict() for p in self.permissions],
        }


class Permission(Base):
    __tablename__ = "auth_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_name", name="uq_permission_per_role"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    permission_name = Column(String(255), nullable=False)

    scopes = Column(ARRAY(String), nullable=False)
    description = Column(String(500))

    role_id = Column(
        Integer,
        ForeignKey("auth_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = relationship("Role", back_populates="permissions")

    def to_dict(self):
        return {
            "id": self.id,
            "permission_name": self.permission_name,
            "scopes": [scope.value for scope in self.scopes],
            "description": self.description,
        }


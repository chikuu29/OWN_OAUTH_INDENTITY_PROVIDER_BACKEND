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
    Date,
    Numeric,
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
    profile = relationship(
        "TenantProfile",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        data = {
            "id": self.id,
            "tenant_uuid": str(self.tenant_uuid),
            "tenant_name": self.tenant_name,
            "tenant_email": self.tenant_email,
            "is_active": self.is_active,
            "status": self.status.value,
            "deployment_type": self.deployment_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        # Safe check for relationship to avoid greenlet_spawn error in async
        from sqlalchemy import inspect
        state = inspect(self)
        if "profile" not in state.unloaded and "profile" not in state.expired:
            if self.profile:
                data["profile"] = self.profile.to_dict()
                
        return data


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


class TenantProfile(Base):
    __tablename__ = "tenant_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Business Details
    legal_name = Column(String(255))
    industry = Column(String(100))
    tax_id = Column(String(50))
    website = Column(String(255))
    phone = Column(String(20))
    business_email = Column(String(255))

    # Address Information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    pincode = Column(String(20))

    # Additional Business Metrics
    owner_name = Column(String(255))
    total_stores = Column(Integer, default=1)
    main_branch = Column(String(255))
    estimated_annual_sales = Column(String(100)) # Using string for flexibility, or Numeric if preferred
    business_type = Column(String(100)) # Wholesale, Retail, Service, etc.
    founding_date = Column(Date)
    timezone = Column(String(100), default="UTC")
    currency = Column(String(10), default="INR")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant = relationship("Tenant", back_populates="profile")

    def to_dict(self):
        return {
            "legal_name": self.legal_name,
            "industry": self.industry,
            "tax_id": self.tax_id,
            "website": self.website,
            "phone": self.phone,
            "business_email": self.business_email,
            "address": {
                "line1": self.address_line1,
                "line2": self.address_line2,
                "city": self.city,
                "state": self.state,
                "country": self.country,
                "pincode": self.pincode,
            },
            "owner_name": self.owner_name,
            "total_stores": self.total_stores,
            "main_branch": self.main_branch,
            "estimated_annual_sales": self.estimated_annual_sales,
            "business_type": self.business_type,
            "founding_date": self.founding_date.isoformat() if self.founding_date else None,
            "timezone": self.timezone,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


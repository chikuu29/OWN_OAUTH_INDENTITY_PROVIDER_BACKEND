import uuid
import enum
from datetime import date, datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    Table,
    Numeric,
    UUID,
    Integer,
    Date,
    DateTime,
    Enum,
    func,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.database import Base

class CurrencyEnum(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class CountryEnum(str, enum.Enum):
    IN = "IN"
    US = "US"
    EU = "EU"
    UK = "UK"

class BillingCycleEnum(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"

# 4.3 plan_apps - Mapping apps to a specific plan version
plan_apps = Table(
    "saas_plan_apps",
    Base.metadata,
    Column("plan_version_id", UUID(as_uuid=True), ForeignKey("saas_plan_versions.id", ondelete="CASCADE"), primary_key=True),
    Column("app_id", UUID(as_uuid=True), ForeignKey("saas_apps.id", ondelete="CASCADE"), primary_key=True),
)

# 4.4 plan_features - Mapping base features to a specific plan version
plan_features = Table(
    "saas_plan_features",
    Base.metadata,
    Column("plan_version_id", UUID(as_uuid=True), ForeignKey("saas_plan_versions.id", ondelete="CASCADE"), primary_key=True),
    Column("feature_id", UUID(as_uuid=True), ForeignKey("saas_features.id", ondelete="CASCADE"), primary_key=True),
)

# 4.1 plans (Logical Plan Name)
class Plan(Base):
    __tablename__ = "saas_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_code = Column(String(50), unique=True, nullable=False) # e.g., 'free', 'pro'
    name = Column(String(100), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    versions = relationship("PlanVersion", back_populates="plan", cascade="all, delete-orphan")

# 4.2 plan_versions (Immutable Contract)
class PlanVersion(Base):
    __tablename__ = "saas_plan_versions"
    __table_args__ = (
        UniqueConstraint("plan_id", "version", "currency", "country", name="uq_plan_version_region"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("saas_plans.id", ondelete="CASCADE"), nullable=False)
    
    version = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    
    currency = Column(Enum(CurrencyEnum), nullable=False, default=CurrencyEnum.INR)
    country = Column(Enum(CountryEnum), nullable=False, default=CountryEnum.IN)
    billing_cycle = Column(Enum(BillingCycleEnum), nullable=False, default=BillingCycleEnum.monthly)
    
    effective_from = Column(Date, default=date.today)
    is_current = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plan = relationship("Plan", back_populates="versions")
    apps = relationship("App", secondary=plan_apps, backref="plan_versions")
    features = relationship("Feature", secondary=plan_features, back_populates="plan_versions")

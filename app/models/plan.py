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

class CurrencyEnum(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class CountryEnum(str, enum.Enum):
    IN = "IN"   # India
    US = "US"   # United States
    EU = "EU"   # Europe
    UK = "UK"   # United Kingdom



class BillingCycleEnum(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"
    
class Plan(Base):
    __tablename__ = "saas_plans"
    __table_args__ = (
        UniqueConstraint(
            "plan_code",
            "billing_cycle",
            "currency",
            "country",
            name="uq_plan_region_pricing",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    plan_code = Column(String(50), nullable=False)   # BASIC / PRO / ENTERPRISE
    plan_name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    # ⬆️ store in smallest unit
    # INR → paise, USD → cents
    currency = Column(
        Enum(CurrencyEnum, name="currency_enum"),
        nullable=False,
    )
    country = Column(
        Enum(CountryEnum, name="country_enum"),
        nullable=False,
    )
    billing_cycle = Column(
        Enum(BillingCycleEnum, name="billing_cycle_enum"),
        nullable=False,
    )
    max_users = Column(Integer)
    max_branches = Column(Integer)
    storage_limit_gb = Column(Integer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    Numeric,
    UUID,
    DateTime,
    Enum,
    func,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.plans import CountryEnum, CurrencyEnum

class App(Base):
    __tablename__ = "saas_apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    code = Column(String(50), unique=True, nullable=False)  # e.g., 'CRM', 'SFA'
    name = Column(String(100), nullable=False)
    description = Column(Text,nullable=True)
    icon = Column(String(255),nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    pricing = relationship("AppPricing", back_populates="app", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="app", cascade="all, delete-orphan")

class AppPricing(Base):
    __tablename__ = "saas_app_pricing"
    __table_args__ = (
        UniqueConstraint("app_id", "currency", "country", name="uq_app_region_pricing"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("saas_apps.id", ondelete="CASCADE"), nullable=False)

    price = Column(Numeric(10, 2), nullable=False, default=0.00)
    currency = Column(Enum(CurrencyEnum), nullable=False, default=CurrencyEnum.INR)
    country = Column(Enum(CountryEnum), nullable=False, default=CountryEnum.IN)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    app = relationship("App", back_populates="pricing")

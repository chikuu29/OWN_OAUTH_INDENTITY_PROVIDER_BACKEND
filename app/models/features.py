import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    ForeignKey,
    Numeric,
    UUID,
    DateTime,
    Enum,
    func
)
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.plans import CurrencyEnum

class Feature(Base):
    __tablename__ = "saas_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("saas_apps.id", ondelete="CASCADE"), nullable=False)
    
    code = Column(String(100), nullable=False) # e.g., 'gym:sms'
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    is_base_feature = Column(Boolean, default=True)
    addon_price = Column(Numeric(10, 2), default=0.00) # 0 if base
    currency = Column(Enum(CurrencyEnum), nullable=False, default=CurrencyEnum.INR)
    
    status = Column(String(20), default="active") # active, inactive
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    app = relationship("App", back_populates="features")
    plan_versions = relationship("PlanVersion", secondary="saas_plan_features", back_populates="features")

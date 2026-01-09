from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Numeric, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    # Order Details
    total_amount = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    currency = Column(String(3), default="INR")
    
    # JSON breakdown of what is being purchased (plan, apps, features snapshot)
    items = Column(JSON, nullable=True)
    
    # External Reference
    provider_order_id = Column(String(100), nullable=True) # Razorpay Order ID
    
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="orders")
    transactions = relationship("Transaction", back_populates="order")

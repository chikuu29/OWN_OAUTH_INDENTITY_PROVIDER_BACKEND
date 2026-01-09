from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Enum, Numeric, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from app.db.database import Base

class TransactionStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    REFUNDED = "refunded"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="INR")
    
    provider = Column(String(50), default="razorpay")
    provider_payment_id = Column(String(100), nullable=True)
    provider_order_id = Column(String(100), nullable=True)
    provider_signature = Column(String(200), nullable=True)
    
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Metadata for the plan/apps selected at time of purchase
    plan_code = Column(String(50), nullable=True)
    billing_cycle = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", backref="transactions")
    subscription = relationship("Subscription", backref="transactions")
    order = relationship("Order", back_populates="transactions")


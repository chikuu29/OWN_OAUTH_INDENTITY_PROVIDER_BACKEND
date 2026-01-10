from datetime import date, datetime
import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    Table,
    UUID,
    Integer,
    Date,
    DateTime,
    Enum,
    Numeric,
    func
)
from sqlalchemy.orm import relationship, backref
from app.db.database import Base
from app.models.plans import CurrencyEnum
from app.models.apps import App
from app.models.features import Feature

class SubscriptionStatus(str, enum.Enum):
    active = "active"
    grace = "grace"
    expired = "expired"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    paid = "paid"
    pending = "pending"
    failed = "failed"
    refunded = "refunded"

class SubscriptionApp(Base):
    __tablename__ = "tenant_subscription_apps"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), primary_key=True)
    app_id = Column(UUID(as_uuid=True), ForeignKey("saas_apps.id", ondelete="CASCADE"), primary_key=True)
    
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    app = relationship("App")


class SubscriptionFeature(Base):
    __tablename__ = "tenant_subscription_features"
    
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), primary_key=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("saas_features.id", ondelete="CASCADE"), primary_key=True)
    
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="active")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    feature = relationship("Feature")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Locking to tenant (Integer ID from tenants)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    # Locking to the immutable contract version
    plan_version_id = Column(UUID(as_uuid=True), ForeignKey("saas_plan_versions.id"), nullable=False)
    
    plan_code = Column(String(50), nullable=True)
    
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.active, nullable=False)
    
    start_date = Column(Date, nullable=False, default=date.today)
    end_date = Column(Date, nullable=False)
    auto_renew = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="subscription")
    plan_version = relationship("PlanVersion")
    
    # Association Object Relationships
    subscribed_apps = relationship("SubscriptionApp", backref="subscription", cascade="all, delete-orphan")
    subscribed_features = relationship("SubscriptionFeature", backref="subscription", cascade="all, delete-orphan")
    
    billings = relationship("SubscriptionBilling", back_populates="subscription", cascade="all, delete-orphan")

    @property
    def all_active_features(self):
        """
        Consolidates all features available to this subscription:
        1. Features bundled in the Plan Version.
        2. Base features included in the subscribed Apps (if active).
        3. Specific Addon features purchased for this subscription (if active).
        """
        features = set()
        
        # 1. From Plan Version
        if self.plan_version:
            features.update(self.plan_version.features)
            
        # 2. From Subscribed Apps (Base features only)
        # Iterate over association objects
        for sub_app in self.subscribed_apps:
            if sub_app.is_active and sub_app.app:
                features.update([f for f in sub_app.app.features if f.is_base_feature])
            
        # 3. From Direct Addons
        for sub_feature in self.subscribed_features:
            if sub_feature.is_active and sub_feature.feature:
                features.add(sub_feature.feature)
        
        return list(features)


class SubscriptionBilling(Base):
    __tablename__ = "saas_subscription_billings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)

    base_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    tax_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    currency = Column(Enum(CurrencyEnum), nullable=False, default=CurrencyEnum.INR)

    billing_date = Column(Date, nullable=False, default=date.today)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    payment_reference = Column(String(255))  # Stripe / Razorpay ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    subscription = relationship("Subscription", back_populates="billings")


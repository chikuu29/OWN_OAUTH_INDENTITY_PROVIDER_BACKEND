from datetime import datetime, timezone
import enum
from sqlalchemy.orm import relationship
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
from app.models.plan import CountryEnum, CurrencyEnum
import uuid


class SubscriptionStatusEnum(str, enum.Enum):
    trial = "trial"
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"
    expired = "expired"









class Subscription(Base):
    __tablename__ = "saas_subscriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_subscription_per_tenant"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    tenant_id = Column(
        Integer,
        ForeignKey("auth_tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    plan_id = Column(
        Integer,
        ForeignKey("saas_plans.id"),
        nullable=False,
    )

    status = Column(
        Enum(SubscriptionStatusEnum, name="subscription_status_enum"),
        default=SubscriptionStatusEnum.trial,
        nullable=False,
    )

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    currency = Column(
        Enum(CurrencyEnum, name="subscription_currency_enum"),
        nullable=False,
    )

    country = Column(
        Enum(CountryEnum, name="subscription_country_enum"),
        nullable=False,
    )

    auto_renew = Column(Boolean, default=True)

    external_payment_id = Column(String(255))  # Stripe / Razorpay ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant = relationship("Tenant", back_populates="subscription")
    plan = relationship("Plan")

    def is_active(self):
        return (
            self.status == SubscriptionStatusEnum.active
            and self.end_date >= datetime.utcnow()
        )

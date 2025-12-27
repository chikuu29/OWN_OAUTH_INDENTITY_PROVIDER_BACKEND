from datetime import datetime, timedelta
import uuid
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    String,
    UUID as SA_UUID,
    func,
)
from app.db.database import Base
from sqlalchemy.orm import relationship


class TenantLink(Base):
    __tablename__ = "tenant_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
 
    # store only the hash of the activation token (do not store the raw token)
    token_hash = Column(String(128), index=True, nullable=False)
    tenant_id = Column(
        Integer,
        ForeignKey("auth_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    request_type = Column(String(100), default="activation")
    is_used = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    tenant = relationship("Tenant", backref="links")

    @staticmethod
    def default_expires_at(hours: int = 24):
        from datetime import timezone
        return datetime.now(timezone.utc) + timedelta(hours=hours)

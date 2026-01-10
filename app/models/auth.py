from sqlalchemy import Column, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class UserProfile(Base):
    __tablename__ = "auth_user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String, nullable=True)  # Store image URL or path
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Define relationship with User
    user = relationship("User", back_populates="profile")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "bio": self.bio,
            "profile_picture": self.profile_picture,
            "address": self.address,
            "city": self.city,
            "country": self.country,
        }


class User(Base):
    __tablename__ = "auth_users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String(20), nullable=True) # Changed to nullable as root users might not have it
    hashed_password = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    
    is_active = Column(Boolean, default=True)
    is_root_user = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    tenant = relationship("Tenant", backref="users")
    profile = relationship("UserProfile", uselist=False, back_populates="user")  # One-to-One Relationship

    def to_dict(self, include_profile=False, include_tenant=False):
        user_data = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "email": self.email,
            "phone_number": self.phone_number,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active,
            "is_root_user": self.is_root_user,
            "is_superuser": self.is_superuser,
        }
        
        # Optionally include the profile if requested
        if include_profile and self.profile:
            user_data["profile"] = self.profile.to_dict()
        if include_tenant and self.tenant:
            user_data["tenant"] = self.tenant.to_dict()

        return user_data

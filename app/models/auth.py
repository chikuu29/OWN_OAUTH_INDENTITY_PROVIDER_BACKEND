



from sqlalchemy import UUID, Column, ForeignKey, Integer, String, Text
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



class User(Base):
    __tablename__ = "auth_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    hashed_password = Column(String, nullable=False)
    tenant_id = Column(Integer, ForeignKey("auth_tenants.id"), nullable=False)

    tenant = relationship("Tenant", backref="users")
    profile = relationship("UserProfile", uselist=False, back_populates="user")  # One-to-One Relationship
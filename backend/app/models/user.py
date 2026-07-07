"""
User table definition.

Why these fields:
- id: primary key
- full_name, email: basic identity, email is used for login (unique)
- hashed_password: we NEVER store plain passwords, only bcrypt hashes
- role: drives Role-Based Access Control (admin / business_user /
  marketing_team / content_creator)
- is_active: lets us disable an account without deleting it
- created_at / updated_at: standard audit fields
"""

import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func

from app.database.session import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    BUSINESS_USER = "business_user"
    MARKETING_TEAM = "marketing_team"
    CONTENT_CREATOR = "content_creator"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CONTENT_CREATOR, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

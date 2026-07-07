"""
Pydantic schemas: define exactly what data comes IN to an API
and what goes OUT, separate from the database model.

Why separate from the DB model:
- We never want to accidentally send hashed_password back in a response.
- We want strict validation on input (e.g. valid email, min password length)
  before it ever touches the database.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.CONTENT_CREATOR


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # allows returning SQLAlchemy objects directly


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    full_name: str
    username: str
    email: EmailStr
    phone: Optional[str]
    profile_picture: Optional[str]
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True
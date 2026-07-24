from datetime import datetime
from pydantic import BaseModel


class SocialAccountCreate(BaseModel):
    platform: str
    account_name: str
    access_token: str | None = None

class SocialAccountUpdate(BaseModel):
    platform: str
    account_name: str
    access_token: str | None = None
    is_active: bool


class SocialAccountResponse(BaseModel):
    id: int
    user_id: int
    platform: str
    account_name: str
    access_token: str | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
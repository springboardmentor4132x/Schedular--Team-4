from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PostCreate(BaseModel):
    campaign_id: int
    social_account_id: int
    title: str
    content: str
    media_url: Optional[str] = None
    scheduled_time: datetime
    content_type: str = "Text"
    timezone: str = "Asia/Kolkata"
    status: str = "Draft"

class PostUpdate(BaseModel):
    campaign_id: int
    social_account_id: int
    title: str
    content: str
    media_url: Optional[str] = None
    content_type: str
    scheduled_time: datetime
    timezone: str
    status: str

class PostResponse(BaseModel):
    id: int
    campaign_id: int
    social_account_id: int
    title: str
    content: str
    media_url: Optional[str]
    content_type: str
    scheduled_time: datetime
    timezone: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
  


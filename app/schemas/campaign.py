from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    campaign_name: str
    description: Optional[str] = None
    status: str = "Active"

class CampaignUpdate(BaseModel):
    campaign_name: str
    description: str
    status: str


class CampaignUpdate(BaseModel):
    campaign_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    user_id: int
    campaign_name: str
    description: Optional[str]
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
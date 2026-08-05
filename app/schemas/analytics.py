from datetime import datetime
from pydantic import BaseModel


class AnalyticsCreate(BaseModel):
    post_id: int
    platform: str
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    impressions: int = 0
    reach: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0


class AnalyticsResponse(BaseModel):
    id: int
    post_id: int
    platform: str
    likes: int
    comments: int
    shares: int
    saves: int
    impressions: int
    reach: int
    clicks: int
    engagement_rate: float
    last_synced: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
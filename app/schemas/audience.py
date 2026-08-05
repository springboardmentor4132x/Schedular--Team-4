from datetime import datetime
from pydantic import BaseModel


class AudienceCreate(BaseModel):
    platform: str
    followers: int = 0
    new_followers: int = 0
    lost_followers: int = 0
    gender_distribution: str
    age_distribution: str
    country: str
    city: str


class AudienceResponse(BaseModel):
    id: int
    platform: str
    followers: int
    new_followers: int
    lost_followers: int
    gender_distribution: str
    age_distribution: str
    country: str
    city: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
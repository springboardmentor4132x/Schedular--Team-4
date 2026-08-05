from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Audience(Base):
    __tablename__ = "audience_analytics"

    id = Column(Integer, primary_key=True, index=True)

    platform = Column(String(50), nullable=False)

    followers = Column(Integer, default=0)
    new_followers = Column(Integer, default=0)
    lost_followers = Column(Integer, default=0)

    gender_distribution = Column(String(200))
    age_distribution = Column(String(200))

    country = Column(String(100))
    city = Column(String(100))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
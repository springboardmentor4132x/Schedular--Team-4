from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)

    post_id = Column(
        Integer,
        ForeignKey("posts.id"),
        nullable=False
    )

    platform = Column(String(50), nullable=False)

    likes = Column(Integer, default=0)

    comments = Column(Integer, default=0)

    shares = Column(Integer, default=0)

    saves = Column(Integer, default=0)

    impressions = Column(Integer, default=0)

    reach = Column(Integer, default=0)

    clicks = Column(Integer, default=0)

    engagement_rate = Column(Float, default=0)

    last_synced = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    post = relationship(
    "Post",
    back_populates="analytics"
    )
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id"),
        nullable=False
    )

    social_account_id = Column(
        Integer,
        ForeignKey("social_accounts.id"),
        nullable=False
    )

    title = Column(String(200), nullable=False)

    content = Column(String(1000), nullable=False)

    media_url = Column(String(500), nullable=True)

    scheduled_time = Column(
        DateTime(timezone=True),
        nullable=False
    )

    status = Column(
        String(30),
        default="Scheduled"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    campaign = relationship("Campaign")

    social_account = relationship("SocialAccount")
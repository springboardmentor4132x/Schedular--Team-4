from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignService:

    @staticmethod
    def create_campaign(
        db: Session,
        user_id: int,
        campaign: CampaignCreate
    ):
        db_campaign = Campaign(
            user_id=user_id,
            campaign_name=campaign.campaign_name,
            description=campaign.description,
            status=campaign.status
        )

        db.add(db_campaign)
        db.commit()
        db.refresh(db_campaign)

        return db_campaign

    @staticmethod
    def get_campaigns(db: Session, user_id: int):
        return db.query(Campaign).filter(
            Campaign.user_id == user_id
        ).all()
    
    @staticmethod
    def get_campaign_by_id(db: Session, campaign_id: int):
        return db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    
    
    @staticmethod
    def update_campaign(
    db: Session,
    campaign_id: int,
    user_id: int,
    campaign_data: CampaignUpdate):
        campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id).first()
        if campaign is None:
            return None
        campaign.campaign_name = campaign_data.campaign_name
        campaign.description = campaign_data.description
        campaign.status = campaign_data.status
        db.commit()
        db.refresh(campaign)
        return campaign
    
    @staticmethod
    def delete_campaign(
    db: Session,
    campaign_id: int,
    user_id: int
):
        campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id
        ).first()
        if campaign is None:
            return False
        db.delete(campaign)
        db.commit()
        return True
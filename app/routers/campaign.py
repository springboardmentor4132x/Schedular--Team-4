from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate
)

from app.services.campaign_service import CampaignService

router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["Campaigns"]
)


# Create Campaign
@router.post(
    "/",
    response_model=CampaignResponse
)
def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CampaignService.create_campaign(
        db,
        current_user.id,
        campaign
    )


# Get All Campaigns
@router.get(
    "/",
    response_model=list[CampaignResponse]
)
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CampaignService.get_campaigns(
        db,
        current_user.id
    )


# Get Campaign by ID
@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse
)
def get_campaign_by_id(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaign = CampaignService.get_campaign_by_id(
        db,
        campaign_id
    )

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return campaign


# Update Campaign
@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse
)
def update_campaign(
    campaign_id: int,
    campaign: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_campaign = CampaignService.update_campaign(
        db,
        campaign_id,
        current_user.id,
        campaign
    )

    if updated_campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return updated_campaign


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = CampaignService.delete_campaign(
        db,
        campaign_id,
        current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return {
        "message": "Campaign deleted successfully"
    }
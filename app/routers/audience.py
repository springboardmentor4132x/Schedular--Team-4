from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

from app.schemas.audience import (
    AudienceCreate,
    AudienceResponse
)

from app.services.audience_service import AudienceService

router = APIRouter(
    prefix="/api/v1/audience",
    tags=["Audience Analytics"]
)


@router.post("/", response_model=AudienceResponse)
def create_audience(
    audience: AudienceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AudienceService.create_audience(db, audience)


@router.get("/", response_model=list[AudienceResponse])
def get_all_audience(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AudienceService.get_all_audience(db)


@router.get("/{platform}", response_model=list[AudienceResponse])
def get_platform_audience(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AudienceService.get_platform_audience(
        db,
        platform
    )
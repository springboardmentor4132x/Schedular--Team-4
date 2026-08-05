from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

from app.schemas.analytics import (
    AnalyticsCreate,
    AnalyticsResponse
)

from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)


@router.post("/", response_model=AnalyticsResponse)
def create_analytics(
    analytics: AnalyticsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.create_analytics(
        db,
        analytics
    )


@router.get("/", response_model=list[AnalyticsResponse])
def get_all_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_all_analytics(db)


@router.get("/dashboard")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_dashboard_summary(db)


@router.get("/top-posts")
def top_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_top_posts(db)

@router.get("/campaign/{campaign_id}")
def campaign_analytics(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_campaign_analytics(
        db,
        campaign_id
    )


@router.get("/platform")
def platform_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_platform_analytics(db)


@router.get("/performance")
def performance_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_performance_trends(db)


@router.get("/performance/daily")
def daily_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_daily_performance(db)


@router.get("/performance/weekly")
def weekly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_weekly_performance(db)


@router.get("/performance/monthly")
def monthly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_monthly_performance(db)


@router.get("/performance/yearly")
def yearly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_yearly_performance(db)


@router.get("/performance/daily")
def daily_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_performance_trends(db, "Daily")


@router.get("/performance/weekly")
def weekly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_performance_trends(db, "Weekly")


@router.get("/performance/monthly")
def monthly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_performance_trends(db, "Monthly")


@router.get("/performance/yearly")
def yearly_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return AnalyticsService.get_performance_trends(db, "Yearly")
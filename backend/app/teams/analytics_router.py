from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.responses import standard_response
from app.database.models import User, Team, TeamMember


router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"],
)


# ============================================================
# HELPER
# ============================================================

def check_team_access(
    team_id: str,
    db: Session,
    current_user: User,
):
    """
    Check that the workspace exists and the current user
    belongs to the workspace.
    """

    team = db.query(Team).filter(
        Team.id == team_id
    ).first()

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Workspace team not found.",
        )

    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
    ).first()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this workspace.",
        )

    return team


# ============================================================
# OVERVIEW
# ============================================================

@router.get("/overview")
def analytics_overview(
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Overall workspace analytics.
    """

    team = check_team_access(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    # These are starter values.
    #
    # Once we connect your actual Post/SocialAccount models,
    # these values can be calculated directly from your DB.
    # --------------------------------------------------------

    data = {
        "workspace": {
            "id": str(team.id),
            "name": getattr(team, "name", "Workspace"),
        },

        "posts": {
            "total": 1245,
            "published": 842,
            "scheduled": 286,
            "draft": 117,
        },

        "engagement": {
            "likes": 18420,
            "comments": 3280,
            "shares": 2145,
            "engagement_rate": 8.7,
        },

        "followers": {
            "total": 12450,
            "growth": 12.5,
        },

        "performance": {
            "reach": 98450,
            "impressions": 152340,
        },
    }

    return standard_response(
        success=True,
        message="Analytics overview retrieved successfully",
        data=data,
    )


# ============================================================
# ENGAGEMENT ANALYTICS
# ============================================================

@router.get("/engagement")
def engagement_analytics(
    team_id: str = Query(...),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return engagement data for charts.
    """

    check_team_access(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )

    today = datetime.utcnow().date()

    result = []

    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)

        result.append(
            {
                "date": date.isoformat(),
                "likes": 400 + ((days - i) * 17) % 300,
                "comments": 70 + ((days - i) * 9) % 100,
                "shares": 40 + ((days - i) * 5) % 70,
            }
        )

    return standard_response(
        success=True,
        message="Engagement analytics retrieved successfully",
        data={
            "days": days,
            "results": result,
        },
    )


# ============================================================
# FOLLOWERS ANALYTICS
# ============================================================

@router.get("/followers")
def followers_analytics(
    team_id: str = Query(...),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Followers growth analytics.
    """

    check_team_access(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )

    today = datetime.utcnow().date()

    result = []

    starting_followers = 11000

    for i in range(days - 1, -1, -1):

        date = today - timedelta(days=i)

        followers = (
            starting_followers
            + ((days - i) * 48)
        )

        result.append(
            {
                "date": date.isoformat(),
                "followers": followers,
            }
        )

    return standard_response(
        success=True,
        message="Followers analytics retrieved successfully",
        data={
            "results": result,
        },
    )


# ============================================================
# POSTS ANALYTICS
# ============================================================

@router.get("/posts")
def posts_analytics(
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scheduled / published / draft post analytics.
    """

    check_team_access(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )

    data = {
        "published": 842,
        "scheduled": 286,
        "draft": 117,
        "failed": 23,
        "total": 1268,
    }

    return standard_response(
        success=True,
        message="Post analytics retrieved successfully",
        data=data,
    )


# ============================================================
# PLATFORM ANALYTICS
# ============================================================

@router.get("/platforms")
def platform_analytics(
    team_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Social platform-wise analytics.
    """

    check_team_access(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )

    platforms = [
        {
            "platform": "Facebook",
            "posts": 320,
            "followers": 5200,
            "likes": 7200,
            "comments": 1240,
            "shares": 780,
            "engagement_rate": 8.4,
        },
        {
            "platform": "Instagram",
            "posts": 410,
            "followers": 6100,
            "likes": 9200,
            "comments": 1650,
            "shares": 1050,
            "engagement_rate": 11.2,
        },
        {
            "platform": "LinkedIn",
            "posts": 180,
            "followers": 1150,
            "likes": 2020,
            "comments": 390,
            "shares": 215,
            "engagement_rate": 6.8,
        },
    ]

    return standard_response(
        success=True,
        message="Platform analytics retrieved successfully",
        data={
            "platforms": platforms,
        },
    )
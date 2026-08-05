from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.analytics import Analytics
from app.models.post import Post
from sqlalchemy import func
from app.models.analytics import Analytics
from app.models.post import Post

class AnalyticsService:

    @staticmethod
    def create_analytics(db: Session, analytics):
        db_analytics = Analytics(**analytics.dict())
        db.add(db_analytics)
        db.commit()
        db.refresh(db_analytics)
        return db_analytics

    @staticmethod
    def get_all_analytics(db: Session):
        return db.query(Analytics).all()

    @staticmethod
    def get_dashboard_summary(db: Session):

        total_published = db.query(Post).filter(
            Post.status == "Published"
        ).count()

        total_scheduled = db.query(Post).filter(
            Post.status == "Scheduled"
        ).count()

        impressions = db.query(
            func.sum(Analytics.impressions)
        ).scalar() or 0

        reach = db.query(
            func.sum(Analytics.reach)
        ).scalar() or 0

        engagement = db.query(
            func.sum(
                Analytics.likes +
                Analytics.comments +
                Analytics.shares
            )
        ).scalar() or 0

        clicks = db.query(
            func.sum(Analytics.clicks)
        ).scalar() or 0

        return {
            "published_posts": total_published,
            "scheduled_posts": total_scheduled,
            "total_impressions": impressions,
            "total_reach": reach,
            "total_engagement": engagement,
            "total_clicks": clicks
        }

    @staticmethod
    def get_top_posts(db: Session):

        return (
            db.query(Analytics)
            .order_by(
                Analytics.engagement_rate.desc()
            )
            .limit(5)
            .all()
        )

    @staticmethod
    def get_campaign_analytics(
    db: Session,
    campaign_id: int
):
     analytics = (
        db.query(
            func.count(Post.id).label("total_posts"),
            func.sum(Analytics.impressions).label("total_impressions"),
            func.sum(Analytics.reach).label("total_reach"),
            func.sum(
                Analytics.likes +
                Analytics.comments +
                Analytics.shares +
                Analytics.saves
            ).label("total_engagement"),
            func.sum(Analytics.clicks).label("total_clicks"),
            func.avg(
                Analytics.engagement_rate
            ).label("avg_engagement_rate")
        )
        .join(
            Post,
            Analytics.post_id == Post.id
        )
        .filter(
            Post.campaign_id == campaign_id
        )
        .first()
    )

     return {
        "campaign_id": campaign_id,
        "total_posts": analytics.total_posts or 0,
        "total_impressions": analytics.total_impressions or 0,
        "total_reach": analytics.total_reach or 0,
        "total_engagement": analytics.total_engagement or 0,
        "total_clicks": analytics.total_clicks or 0,
        "average_engagement_rate": float(
            analytics.avg_engagement_rate or 0
        )
    }

    @staticmethod
    def get_platform_analytics(db: Session):

     analytics = (
        db.query(
            Analytics.platform,
            func.count(Analytics.id).label("posts"),
            func.sum(Analytics.impressions).label("impressions"),
            func.sum(Analytics.reach).label("reach"),
            func.sum(Analytics.likes).label("likes"),
            func.sum(Analytics.comments).label("comments"),
            func.sum(Analytics.shares).label("shares"),
            func.sum(Analytics.clicks).label("clicks"),
            func.avg(Analytics.engagement_rate).label("engagement_rate")
        )
        .group_by(Analytics.platform)
        .all()
    )

     result = []

     for row in analytics:
        result.append({
            "platform": row.platform,
            "posts": row.posts,
            "impressions": row.impressions or 0,
            "reach": row.reach or 0,
            "likes": row.likes or 0,
            "comments": row.comments or 0,
            "shares": row.shares or 0,
            "clicks": row.clicks or 0,
            "engagement_rate": float(row.engagement_rate or 0)
        })

     return result


    @staticmethod
    def get_performance_trends(db: Session):

     analytics = db.query(Analytics).all()

     result = []

     for row in analytics:
        result.append({
            "date": row.created_at.date(),
            "platform": row.platform,
            "impressions": row.impressions,
            "reach": row.reach,
            "likes": row.likes,
            "comments": row.comments,
            "shares": row.shares,
            "clicks": row.clicks,
            "engagement_rate": row.engagement_rate
        })

     return result



    @staticmethod
    def get_daily_performance(db: Session):
     return db.query(Analytics).all()


    @staticmethod
    def get_weekly_performance(db: Session):
     return db.query(Analytics).all()


    @staticmethod
    def get_monthly_performance(db: Session):
     return db.query(Analytics).all()


    staticmethod
    def get_yearly_performance(db: Session):
     return db.query(Analytics).all()


    @staticmethod
    def get_performance_trends(db: Session, period: str):

     analytics = db.query(Analytics).all()

     result = []

     for row in analytics:
        result.append({
            "date": row.created_at.strftime("%Y-%m-%d"),
            "period": period,
            "platform": row.platform,
            "impressions": row.impressions,
            "reach": row.reach,
            "engagement": (
                row.likes +
                row.comments +
                row.shares +
                row.saves
            ),
            "clicks": row.clicks,
            "engagement_rate": row.engagement_rate
        })

     return result
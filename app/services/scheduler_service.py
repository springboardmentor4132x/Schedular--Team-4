from datetime import datetime
from sqlalchemy.orm import Session

from app.models.post import Post
from app.services.publisher_service import PublisherService


class SchedulerService:

    @staticmethod
    def run_scheduler(db: Session):
        # Get all scheduled posts whose time has arrived
        scheduled_posts = db.query(Post).filter(
            Post.status == "Scheduled",
            Post.scheduled_time <= datetime.now()
        ).all()

        published_count = 0

        for post in scheduled_posts:
            PublisherService.publish_post(db, post)
            published_count += 1

        return {
            "message": "Scheduler executed successfully",
            "published_posts": published_count
        }
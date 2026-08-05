from sqlalchemy.orm import Session

from app.models.post import Post


class PublisherService:

    @staticmethod
    def publish_post(
        db: Session,
        post: Post
    ):
        # Simulate publishing
        post.status = "Published"

        db.commit()
        db.refresh(post)

        return post
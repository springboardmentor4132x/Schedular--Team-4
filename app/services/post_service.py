from sqlalchemy.orm import Session

from app.models.post import Post
from app.schemas.post import (
    PostCreate,
    PostUpdate
)


class PostService:

    @staticmethod
    def create_post(
     db: Session,
     post: PostCreate
):
     db_post = Post(
        campaign_id=post.campaign_id,
        social_account_id=post.social_account_id,
        title=post.title,
        content=post.content,
        media_url=post.media_url,
        content_type=post.content_type,
        scheduled_time=post.scheduled_time,
        timezone=post.timezone,
        status="Scheduled"
    )

     db.add(db_post)
     db.commit()
     db.refresh(db_post)

     return db_post

    @staticmethod
    def get_posts(db: Session):
        return db.query(Post).all()

    

    @staticmethod
    def get_post_queue(db: Session):
     return db.query(Post).filter(
        Post.status == "Scheduled"
    ).all()

    @staticmethod
    def get_post_by_id(
        db: Session,
        post_id: int
    ):
        return db.query(Post).filter(
            Post.id == post_id
        ).first()

    @staticmethod
    def update_post(
        db: Session,
        post_id: int,
        post_data: PostUpdate
        
    ):
        post = db.query(Post).filter(
            Post.id == post_id
        ).first()

        if post is None:
            return None

        post.campaign_id = post_data.campaign_id
        post.social_account_id = post_data.social_account_id
        post.title = post_data.title
        post.content = post_data.content
        post.media_url = post_data.media_url
        post.scheduled_time = post_data.scheduled_time
        post.status = post_data.status
        post.content_type = post_data.content_type
        post.timezone = post_data.timezone

        db.commit()
        db.refresh(post)

        return post

    @staticmethod
    def delete_post(
        db: Session,
        post_id: int
    ):
        post = db.query(Post).filter(
            Post.id == post_id
        ).first()

        if post is None:
            return False

        db.delete(post)
        db.commit()

        return True

 
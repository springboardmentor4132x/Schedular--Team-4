import asyncio
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.models import Post, SocialAccount
from app.database.repositories import PublishingLogRepository, NotificationRepository
from app.database.schemas import PublishingLogCreate, NotificationCreate

async def publish_pending_posts(db: Session = None):
    is_local_session = False
    if db is None:
        db = SessionLocal()
        is_local_session = True
        
    try:
        now = datetime.utcnow()
        pending_posts = db.query(Post).filter(
            Post.status == "scheduled",
            Post.scheduled_at <= now
        ).all()

        if not pending_posts:
            return

        from app.publishing.publisher import RealPublisher
        from app.social.token_manager import TokenManager, TokenRefreshError

        for post in pending_posts:
            try:
                platform_ids = json.loads(post.platform_targets)
            except Exception:
                platform_ids = []

            if not platform_ids:
                post.status = "failed"
                post.updated_at = datetime.utcnow()
                db.add(post)
                continue

            expired_accounts = []
            refresh_failed_accounts = []
            for ch_id in platform_ids:
                acc = db.query(SocialAccount).filter(SocialAccount.id == ch_id).first()
                if not acc:
                    PublishingLogRepository.create_log(db, PublishingLogCreate(
                        post_id=post.id,
                        team_id=post.team_id,
                        platform="unknown",
                        status="failed",
                        error_message=f"Target social account {ch_id} not found."
                    ))
                    continue

                try:
                    TokenManager.get_valid_access_token(db, acc)
                    db.refresh(acc)
                except TokenRefreshError as token_exc:
                    refresh_failed_accounts.append((acc, str(token_exc)))
                    continue

                is_expired = acc.expires_at is not None and acc.expires_at < datetime.utcnow()
                if is_expired:
                    expired_accounts.append(acc)

            if refresh_failed_accounts:
                for acc, error_message in refresh_failed_accounts:
                    PublishingLogRepository.create_log(db, PublishingLogCreate(
                        post_id=post.id,
                        team_id=post.team_id,
                        platform=acc.platform,
                        status="failed",
                        error_message=error_message,
                    ))
                    NotificationRepository.create_notification(db, NotificationCreate(
                        team_id=post.team_id,
                        user_id=post.user_id,
                        title="Publishing Dispatch Failed",
                        message=(
                            f"We were unable to publish your post to "
                            f"{acc.platform.capitalize()} because the connection expired."
                        ),
                        type="error"
                    ))
                post.status = "failed"
                post.updated_at = datetime.utcnow()
                db.add(post)
                continue

            if expired_accounts:
                for acc in expired_accounts:
                    PublishingLogRepository.create_log(db, PublishingLogCreate(
                        post_id=post.id,
                        team_id=post.team_id,
                        platform=acc.platform,
                        status="failed",
                        error_message=(
                            f"Connection expired for channel {acc.account_name}. "
                            "Please re-authenticate."
                        )
                    ))
                    NotificationRepository.create_notification(db, NotificationCreate(
                        team_id=post.team_id,
                        user_id=post.user_id,
                        title="Publishing Dispatch Failed",
                        message=(
                            f"We were unable to publish your post to "
                            f"{acc.platform.capitalize()} because the connection expired."
                        ),
                        type="error"
                    ))
                post.status = "failed"
                post.updated_at = datetime.utcnow()
                db.add(post)
                continue

            post.status = "publishing"
            post.updated_at = datetime.utcnow()
            db.add(post)
            db.commit()
            db.refresh(post)

            try:
                result = RealPublisher.publish_post_to_channels(db, post.id)
                if result.get("status") == "published":
                    NotificationRepository.create_notification(db, NotificationCreate(
                        team_id=post.team_id,
                        user_id=post.user_id,
                        title="Post Published Successfully",
                        message="Your scheduled post was successfully published.",
                        type="success"
                    ))
            except Exception as publish_error:
                PublishingLogRepository.create_log(db, PublishingLogCreate(
                    post_id=post.id,
                    team_id=post.team_id,
                    platform="unknown",
                    status="failed",
                    error_message=str(publish_error)
                ))
                post.status = "failed"
                post.updated_at = datetime.utcnow()
                db.add(post)

        db.commit()
    except Exception as e:
        print(f"Error in background publisher task: {e}")
        db.rollback()
        raise e
    finally:
        if is_local_session:
            db.close()

async def scheduler_loop():
    await asyncio.sleep(5)
    while True:
        try:
            await publish_pending_posts()
        except Exception:
            pass
        await asyncio.sleep(10)

import json
import logging
from datetime import datetime, timedelta, time
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status as fastapi_status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_active_user, get_db
from app.database.models import User, Post, SocialAccount, PublishingLog
from app.database.repositories import TeamRepository, SocialAccountRepository, PostRepository, PublishingLogRepository, NotificationRepository
from app.database.schemas import PostCreate, PostUpdate, PostOut, PublishingLogCreate, NotificationCreate

logger = logging.getLogger("socialpilot.posts.routes")
router = APIRouter(prefix="/posts", tags=["Content Scheduling"])

def calculate_next_queue_slot(db: Session, team_id: str, timezone_str: str) -> datetime:
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone_str)
    except Exception:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("UTC")

    now_tz = datetime.now(tz)
    slot_times = [time(9, 0), time(11, 0), time(14, 0), time(17, 0)]
    current_date = now_tz.date()
    
    for day_offset in range(30):
        check_date = current_date + timedelta(days=day_offset)
        for slot_time in slot_times:
            dt_tz = datetime.combine(check_date, slot_time)
            dt_tz = dt_tz.replace(tzinfo=tz)
            
            if dt_tz <= now_tz:
                continue
                
            dt_utc = dt_tz.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            start_win = dt_utc - timedelta(minutes=10)
            end_win = dt_utc + timedelta(minutes=10)
            
            existing = db.query(Post).filter(
                Post.team_id == team_id,
                Post.status == "scheduled",
                Post.scheduled_at >= start_win,
                Post.scheduled_at <= end_win
            ).first()
            
            if not existing:
                return dt_utc
                
    return datetime.utcnow() + timedelta(hours=1)

@router.get("/next-queue-slot")
def get_next_queue_slot(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    member = TeamRepository.get_member(db, team_id=team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace"
        )
    
    user_tz = getattr(current_user, "timezone", "UTC") or "UTC"
    next_slot = calculate_next_queue_slot(db, team_id=team_id, timezone_str=user_tz)
    
    return {
        "success": True,
        "next_slot": next_slot.isoformat(),
        "timezone": user_tz
    }

@router.post("", response_model=PostOut)
def create_scheduled_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    member = TeamRepository.get_member(db, team_id=payload.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace"
        )
        
    if payload.schedule_type == "scheduled":
        if not payload.scheduled_at:
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail="Scheduled post requires a target publishing timestamp 'scheduled_at'"
            )
        # Allow 1-minute buffer for clock drift
        if payload.scheduled_at < datetime.utcnow() - timedelta(minutes=1):
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail="Publish date cannot be set in the past"
            )

    if not payload.platform_targets:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="Publish targets must contain at least one connected social account ID"
        )
        
    for acc_id in payload.platform_targets:
        acc = SocialAccountRepository.get_by_id(db, account_id=acc_id)
        if not acc or acc.team_id != payload.team_id:
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail=f"Target channel connection ID '{acc_id}' is invalid or from a different workspace"
            )

    post = PostRepository.create_post(db, post_data=payload, user_id=current_user.id)
    
    if payload.schedule_type == "now":
        post.status = "publishing"
        db.commit()
        db.refresh(post)
        
        from app.publishing.publisher import RealPublisher
        try:
            RealPublisher.publish_post_to_channels(db, post.id)
            db.refresh(post)
        except Exception as e:
            logger.error(f"Immediate publishing failed for post {post.id}: {e}")
            post.status = "failed"
            db.commit()
            db.refresh(post)

    return post

@router.get("/{id}", response_model=PostOut)
def get_post_by_id(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace"
        )
    return post

@router.get("", response_model=List[PostOut])
def get_scheduled_posts(
    team_id: str,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Enforce team access
    member = TeamRepository.get_member(db, team_id=team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace"
        )
        
    return PostRepository.get_by_team(
        db, team_id=team_id, status=status, start_date=start_date, end_date=end_date
    )

@router.put("/{id}", response_model=PostOut)
def update_scheduled_post(
    id: str,
    payload: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    # Enforce membership to post's team
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to target post"
        )

    # Time validation if updating schedule times
    if payload.scheduled_at and payload.schedule_type != "draft":
        if payload.scheduled_at < datetime.utcnow():
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail="Publish date cannot be set in the past"
            )

    updated_post = PostRepository.update_post(db, post_id=id, updates=payload)
    return updated_post

@router.delete("/{id}", status_code=fastapi_status.HTTP_200_OK)
def delete_scheduled_post(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    # Check authorization permissions
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to target post"
        )

    PostRepository.delete_post(db, post_id=id)
    return {"detail": "Scheduled post deleted successfully"}

@router.post("/{id}/publish", response_model=PostOut)
def publish_post_now(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Instantly dispatches post publishing simulation. Checks credentials validity."""
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to target post"
        )

    # 1. Parse target platforms list from model string
    try:
        targets = json.loads(post.platform_targets)
    except Exception:
        targets = []

    # 2. Check channel connection health
    for acc_id in targets:
        acc = SocialAccountRepository.get_by_id(db, account_id=acc_id)
        if not acc:
            # Mark post as failed
            PostRepository.update_post(db, post_id=id, updates=PostUpdate(status="failed"))
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail=f"Target channel connection not found in team workspace."
            )
        # Check if the connection has expired (attempt refresh first)
        if acc.expires_at and acc.expires_at < datetime.utcnow():
            from app.social.token_manager import TokenManager, TokenRefreshError
            try:
                TokenManager.get_valid_access_token(db, acc)
                db.refresh(acc)
            except TokenRefreshError as token_exc:
                PostRepository.update_post(db, post_id=id, updates=PostUpdate(status="failed"))
                raise HTTPException(
                    status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                    detail=str(token_exc),
                ) from token_exc

        if acc.expires_at and acc.expires_at < datetime.utcnow():
            PostRepository.update_post(db, post_id=id, updates=PostUpdate(status="failed"))
            raise HTTPException(
                status_code=fastapi_status.HTTP_400_BAD_REQUEST,
                detail=f"Publishing failed: Target connection '{acc.account_name}' has expired. Re-authenticate in Social Channels."
            )

    # 3. Mark post as published
    updated = PostRepository.update_post(db, post_id=id, updates=PostUpdate(status="published"))
    return updated

@router.post("/{id}/retry", response_model=PostOut)
def retry_failed_post(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
        
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace"
        )
        
    if post.status not in ["failed", "partially_published"]:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="Only failed or partially published posts can be retried"
        )

    try:
        platform_ids = json.loads(post.platform_targets) if isinstance(post.platform_targets, str) else post.platform_targets
    except Exception:
        platform_ids = [post.platform_targets] if post.platform_targets else []

    if not platform_ids:
        post.status = "failed"
        db.commit()
        return post

    # Find already successful platforms
    success_logs = db.query(PublishingLog).filter(
        PublishingLog.post_id == post.id,
        PublishingLog.status == "published"
    ).all()
    successful_platforms = {log.platform for log in success_logs}

    targets_to_retry = []
    for ch_id in platform_ids:
        acc = SocialAccountRepository.get_by_id(db, account_id=ch_id)
        if acc and acc.platform not in successful_platforms:
            targets_to_retry.append(ch_id)

    if not targets_to_retry:
        raise HTTPException(
            status_code=fastapi_status.HTTP_400_BAD_REQUEST,
            detail="All platforms have already published successfully."
        )

    post.status = "publishing"
    db.commit()
    db.refresh(post)

    from app.publishing.publisher import RealPublisher
    try:
        RealPublisher.publish_post_to_channels(db, post.id, account_ids=targets_to_retry)
        db.refresh(post)
    except Exception as e:
        logger.error(f"Retry failed for post {post.id}: {e}")
        post.status = "failed"
        db.commit()
        db.refresh(post)

    return post

@router.post("/cancel/{id}")
@router.post("/{id}/cancel")
def cancel_scheduled_post(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel a scheduled post."""
    post = PostRepository.get_by_id(db, post_id=id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    member = TeamRepository.get_member(db, team_id=post.team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    post.status = "cancelled"
    db.commit()
    return {"detail": f"Post {id} cancelled successfully", "status": "cancelled"}

@router.get("/queue")
def get_publishing_queue(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve scheduled/pending publishing queue."""
    member = TeamRepository.get_member(db, team_id=team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    posts = PostRepository.get_by_team(db, team_id=team_id, status="scheduled")
    return {"queue": [PostOut.model_validate(p) for p in posts]}

@router.get("/history")
def get_publishing_history(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve published/failed publishing history."""
    member = TeamRepository.get_member(db, team_id=team_id, user_id=current_user.id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    pub_posts = PostRepository.get_by_team(db, team_id=team_id, status="published")
    fail_posts = PostRepository.get_by_team(db, team_id=team_id, status="failed")
    return {
        "published": [PostOut.model_validate(p) for p in pub_posts],
        "failed": [PostOut.model_validate(p) for p in fail_posts]
    }

@router.post("/upload-media")
def upload_media_file(
    file: UploadFile = File(...),
    platform: str = "facebook",
    current_user: User = Depends(get_current_active_user)
):
    """Upload a media file and validate it against the target social platform specifications."""
    try:
        from app.social.media.media_service import MediaService
        
        file_bytes = file.file.read()
        media_service = MediaService()
        res = media_service.process_and_upload(
            file_bytes=file_bytes,
            filename=file.filename,
            mime_type=file.content_type,
            platform=platform
        )
        return {
            "success": True,
            "media_url": res["media_url"],
            "mime_type": res["mime_type"],
            "filesize": res["filesize"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload media: {str(e)}"
        )


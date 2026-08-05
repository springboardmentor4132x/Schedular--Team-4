from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse
)

from app.services.post_service import PostService
from app.services.scheduler_service import SchedulerService

router = APIRouter(
    prefix="/api/v1/posts",
    tags=["Posts"]
)

@router.post("/run-scheduler")
def run_scheduler(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SchedulerService.run_scheduler(db)

@router.post("/", response_model=PostResponse)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return PostService.create_post(db, post)


@router.get("/", response_model=list[PostResponse])
def get_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return PostService.get_posts(db)

@router.get("/queue", response_model=list[PostResponse])
def get_post_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return PostService.get_post_queue(db)

@router.get("/{post_id}", response_model=PostResponse)
def get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = PostService.get_post_by_id(db, post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return post


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_post = PostService.update_post(
        db,
        post_id,
        post
    )

    if updated_post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return updated_post


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = PostService.delete_post(db, post_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return {
        "message": "Post deleted successfully"
    }
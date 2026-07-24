from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User

from app.schemas.social_account import (
    SocialAccountCreate,
    SocialAccountResponse,
    SocialAccountUpdate
)
from fastapi import APIRouter, Depends, HTTPException

from app.services.social_account_service import SocialAccountService

router = APIRouter(
    prefix="/api/v1/social-accounts",
    tags=["Social Accounts"]
)


# Connect a Social Account
@router.post(
    "/",
    response_model=SocialAccountResponse
)
def create_social_account(
    social_account: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SocialAccountService.create_social_account(
        db,
        current_user.id,
        social_account
    )


# Get All Connected Social Accounts
@router.get(
    "/",
    response_model=list[SocialAccountResponse]
)
def get_social_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SocialAccountService.get_social_accounts(
        db,
        current_user.id
    )


@router.put(
    "/{account_id}",
    response_model=SocialAccountResponse
)
def update_social_account(
    account_id: int,
    social_account: SocialAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_account = SocialAccountService.update_social_account(
        db,
        account_id,
        current_user.id,
        social_account
    )

    if updated_account is None:
        raise HTTPException(
            status_code=404,
            detail="Social account not found"
        )

    return updated_account


@router.delete("/{account_id}")
def delete_social_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = SocialAccountService.delete_social_account(
        db,
        account_id,
        current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Social account not found"
        )

    return {
        "message": "Social account deleted successfully"
    }
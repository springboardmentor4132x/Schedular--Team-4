from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount
from app.schemas.social_account import (
    SocialAccountCreate,
    SocialAccountUpdate
)


class SocialAccountService:

    @staticmethod
    def create_social_account(
        db: Session,
        user_id: int,
        social_account: SocialAccountCreate
    ):
        db_social_account = SocialAccount(
            user_id=user_id,
            platform=social_account.platform,
            account_name=social_account.account_name,
            access_token=social_account.access_token
        )

        db.add(db_social_account)
        db.commit()
        db.refresh(db_social_account)

        return db_social_account

    @staticmethod
    def get_social_accounts(
        db: Session,
        user_id: int
    ):
        return db.query(SocialAccount).filter(
            SocialAccount.user_id == user_id
        ).all()

    @staticmethod
    def update_social_account(
        db: Session,
        account_id: int,
        user_id: int,
        social_account: SocialAccountUpdate
    ):
        account = db.query(SocialAccount).filter(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user_id
        ).first()

        if account is None:
            return None

        account.platform = social_account.platform
        account.account_name = social_account.account_name
        account.access_token = social_account.access_token
        account.is_active = social_account.is_active

        db.commit()
        db.refresh(account)

        return account

    @staticmethod
    def delete_social_account(
        db: Session,
        account_id: int,
        user_id: int
    ):
        account = db.query(SocialAccount).filter(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user_id
        ).first()

        if account is None:
            return False

        db.delete(account)
        db.commit()

        return True
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.users.models import OAuthAccount
from app.database.models import SocialAccount
from app.core.crypto import encrypt_token, decrypt_token
from app.social.providers import get_social_provider

logger = logging.getLogger("socialpilot.social.token_manager")

class TokenRefreshError(Exception):
    """Raised when an OAuth access token cannot be refreshed or validated."""

class TokenManager:
    """Manages Fernet AES-256 encrypted token lifecycle, decryption, and automatic background refresh."""

    LINKEDIN_DEFAULT_EXPIRY_SECONDS = 5184000  # 60 days

    @staticmethod
    def store_oauth_account(
        db: Session,
        user_id: str,
        provider: str,
        provider_user_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        expires_in_seconds: int = 3600,
        account_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> OAuthAccount:
        """Encrypt and store OAuth tokens into user database."""
        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(refresh_token) if refresh_token else None
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        existing = db.query(OAuthAccount).filter(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider
        ).first()

        if existing:
            existing.provider_user_id = provider_user_id
            existing.access_token = enc_access
            if enc_refresh:
                existing.refresh_token = enc_refresh
            existing.scope = scope or existing.scope
            existing.expires_at = expires_at
            if account_name:
                existing.account_name = account_name
            if avatar_url:
                existing.avatar_url = avatar_url
            existing.connected = True
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated OAuth tokens for {provider} account {provider_user_id}.")
            return existing
        else:
            new_acc = OAuthAccount(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                account_name=account_name,
                avatar_url=avatar_url,
                access_token=enc_access,
                refresh_token=enc_refresh,
                scope=scope,
                expires_at=expires_at,
                connected=True
            )
            db.add(new_acc)
            db.commit()
            db.refresh(new_acc)
            logger.info(f"Stored new OAuth tokens for {provider} account {provider_user_id}.")
            return new_acc

    @staticmethod
    def get_valid_access_token(db: Session, account: Any) -> str:
        """Decrypt access token and trigger automatic refresh if token is expired or within 1 hour of expiration."""
        raw_access = decrypt_token(account.access_token)
        raw_refresh = decrypt_token(account.refresh_token) if account.refresh_token else ""
        provider = getattr(account, "provider", None) or getattr(account, "platform", None)

        buffer_time = datetime.utcnow() + timedelta(hours=1)
        is_near_expiry = account.expires_at is not None and account.expires_at <= buffer_time
        is_expired = account.expires_at is not None and account.expires_at <= datetime.utcnow()

        if is_expired and not raw_refresh:
            raise TokenRefreshError(
                f"The {provider or 'social'} connection has expired and no refresh token is available. "
                "Please reconnect the account from Social Accounts."
            )

        if is_near_expiry and raw_refresh and provider:
            logger.info(
                "Token for %s account %s is near expiration. Triggering refresh.",
                provider,
                getattr(account, "id", "unknown"),
            )
            try:
                provider_driver = get_social_provider(provider)
                refreshed = provider_driver.refresh_token(raw_refresh)
                new_access = refreshed.get("access_token")
                new_refresh = refreshed.get("refresh_token", raw_refresh)
                expires_in = int(
                    refreshed.get(
                        "expires_in",
                        TokenManager.LINKEDIN_DEFAULT_EXPIRY_SECONDS if provider == "linkedin" else 3600,
                    )
                )

                if new_access:
                    account.access_token = encrypt_token(new_access)
                    if new_refresh:
                        account.refresh_token = encrypt_token(new_refresh)
                    account.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    db.commit()
                    TokenManager._sync_refreshed_tokens(db, account, new_access, new_refresh, account.expires_at)
                    return new_access
            except Exception as exc:
                logger.error("Failed auto-refresh for %s: %s", provider, exc)
                if is_expired:
                    raise TokenRefreshError(
                        f"Unable to refresh the expired {provider} connection: {exc}. "
                        "Please reconnect the account from Social Accounts."
                    ) from exc

        if is_expired:
            raise TokenRefreshError(
                f"The {provider or 'social'} connection has expired. "
                "Please reconnect the account from Social Accounts."
            )

        return raw_access

    @staticmethod
    def _sync_refreshed_tokens(
        db: Session,
        source_account: Any,
        access_token: str,
        refresh_token: Optional[str],
        expires_at: datetime,
    ) -> None:
        """Keep OAuthAccount and SocialAccount token stores aligned after a refresh."""
        user_id = getattr(source_account, "user_id", None)
        provider = getattr(source_account, "provider", None) or getattr(source_account, "platform", None)
        platform_account_id = getattr(source_account, "platform_account_id", None) or getattr(
            source_account, "provider_user_id", None
        )

        if not user_id or not provider:
            return

        enc_access = encrypt_token(access_token)
        enc_refresh = encrypt_token(refresh_token) if refresh_token else None

        if isinstance(source_account, SocialAccount):
            oauth_match = db.query(OAuthAccount).filter(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
            ).first()
            if oauth_match:
                oauth_match.access_token = enc_access
                if enc_refresh:
                    oauth_match.refresh_token = enc_refresh
                oauth_match.expires_at = expires_at
                db.commit()
            return

        if isinstance(source_account, OAuthAccount) and platform_account_id:
            social_matches = db.query(SocialAccount).filter(
                SocialAccount.user_id == user_id,
                SocialAccount.platform == provider,
                SocialAccount.platform_account_id == platform_account_id,
            ).all()
            for social_acc in social_matches:
                social_acc.access_token = enc_access
                if enc_refresh:
                    social_acc.refresh_token = enc_refresh
                social_acc.expires_at = expires_at
            if social_matches:
                db.commit()

    @staticmethod
    def refresh_all_expiring_tokens(db: Session) -> int:
        """Background job helper scanning all active accounts and refreshing near-expiry tokens."""
        from app.database.models import SocialAccount
        buffer_time = datetime.utcnow() + timedelta(hours=2)
        
        expiring_oauth = db.query(OAuthAccount).filter(
            OAuthAccount.connected == True,
            OAuthAccount.expires_at <= buffer_time
        ).all()

        expiring_social = db.query(SocialAccount).filter(
            SocialAccount.expires_at <= buffer_time
        ).all()

        count = 0
        for acc in expiring_oauth:
            try:
                TokenManager.get_valid_access_token(db, acc)
                count += 1
            except Exception as e:
                logger.error(f"Error during bulk refresh for OAuthAccount {acc.id}: {e}")

        for acc in expiring_social:
            try:
                TokenManager.get_valid_access_token(db, acc)
                count += 1
            except Exception as e:
                logger.error(f"Error during bulk refresh for SocialAccount {acc.id}: {e}")
        return count

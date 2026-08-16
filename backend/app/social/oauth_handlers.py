import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models import User
from app.database.repositories import SocialAccountRepository, TeamRepository
from app.social.oauth_utils import (
    get_oauth_redirect_uri,
    get_provider_credentials_error,
    parse_oauth_state,
)
from app.social.providers import get_social_provider
from app.social.token_manager import TokenManager

logger = logging.getLogger("socialpilot.social.oauth_handlers")


def _resolve_profile_for_connection(
    driver: Any,
    access_token: str,
    platform: str,
    connection_type: Optional[str],
) -> Dict[str, Any]:
    profile = driver.get_profile(access_token)

    if platform != "linkedin":
        return profile

    if connection_type != "company":
        member_id = profile.get("provider_user_id", "")
        profile["author_urn"] = profile.get("author_urn") or f"urn:li:person:{member_id}"
        return profile

    organizations = driver.get_admin_organizations(access_token)
    if not organizations:
        raise ValueError(
            "No LinkedIn Company Page administrator access was found for this account. "
            "Ensure you selected a Company Page connection, your app has the "
            "w_organization_social product enabled, and you are an admin of at least one page."
        )

    selected_org = organizations[0]
    profile["provider_user_id"] = selected_org["id"]
    profile["account_name"] = selected_org.get("name") or profile.get("name", "LinkedIn Company Page")
    profile["author_urn"] = selected_org["urn"]
    profile["connection_type"] = "company"
    return profile


def complete_oauth_callback(
    db: Session,
    platform: str,
    code: str,
    state: Optional[str],
    redirect_uri: Optional[str] = None,
) -> Dict[str, Any]:
    platform_lower = platform.lower()
    parsed_state = parse_oauth_state(state)
    user_id = parsed_state.get("user_id")
    team_id = parsed_state.get("team_id")
    connection_type = parsed_state.get("connection_type")

    if not user_id:
        raise HTTPException(status_code=400, detail="OAuth state is missing or invalid.")

    if not team_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "OAuth state is missing the team workspace identifier. "
                "Restart the connection flow from the Social Accounts page."
            ),
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="OAuth user was not found.")

    if team_id:
        member = TeamRepository.get_member(db, team_id=team_id, user_id=user.id)
        if not member:
            raise HTTPException(
                status_code=403,
                detail="User is not a member of the selected team workspace.",
            )

    driver = get_social_provider(platform_lower)
    if not driver:
        raise HTTPException(status_code=400, detail=f"Provider '{platform}' is not supported.")

    if not driver.client_id or driver.client_id == "demo_client_id":
        raise HTTPException(status_code=400, detail=get_provider_credentials_error(platform_lower))

    target_redirect = redirect_uri or get_oauth_redirect_uri(platform_lower)

    try:
        token_data = driver.callback(code=code, redirect_uri=target_redirect)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"{platform.capitalize()} did not return an access token.")

        if not driver.validate_token(access_token):
            raise ValueError(
                f"{platform.capitalize()} access token validation failed. "
                "The token may be invalid or missing required permissions."
            )

        profile = _resolve_profile_for_connection(
            driver=driver,
            access_token=access_token,
            platform=platform_lower,
            connection_type=connection_type,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("OAuth callback failed for %s: %s", platform_lower, exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"OAuth authorization code exchange failed for {platform.capitalize()}: {exc}",
        ) from exc

    expires_in_seconds = int(token_data.get("expires_in", 5184000 if platform_lower == "linkedin" else 3600))
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    account_name = (
        profile.get("account_name")
        or profile.get("name")
        or f"{user.name} ({platform.capitalize()})"
    )
    platform_account_id = profile.get("provider_user_id") or f"{platform_lower}_user"
    if platform_lower == "linkedin":
        platform_account_id = profile.get("author_urn") or f"urn:li:person:{profile.get('provider_user_id', 'me')}"
    avatar_url = profile.get("avatar_url") or f"https://api.dicebear.com/7.x/initials/svg?seed={platform_lower}"

    resolved_access_token = profile.get("access_token") or access_token

    TokenManager.store_oauth_account(
        db=db,
        user_id=user.id,
        provider=platform_lower,
        provider_user_id=platform_account_id,
        access_token=resolved_access_token,
        refresh_token=token_data.get("refresh_token"),
        scope=token_data.get("scope"),
        expires_in_seconds=expires_in_seconds,
        account_name=account_name,
        avatar_url=avatar_url,
    )

    social_account = SocialAccountRepository.connect_account(
        db=db,
        team_id=team_id,
        user_id=user.id,
        platform=platform_lower,
        platform_account_id=platform_account_id,
        name=account_name,
        avatar=avatar_url,
        token=resolved_access_token,
        refresh=token_data.get("refresh_token"),
        expires_at=expires_at,
    )

    return {
        "platform": platform_lower,
        "connection_type": connection_type,
        "profile": profile,
        "social_account": social_account,
        "expires_at": expires_at,
        "refresh_token_available": bool(token_data.get("refresh_token")),
    }

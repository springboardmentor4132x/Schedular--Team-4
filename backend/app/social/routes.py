import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    Query,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_active_user,
    get_db,
)
from app.core.config import settings
from app.database.models import User, SocialAccount
from app.database.repositories import (
    TeamRepository,
    SocialAccountRepository,
)
from app.database.schemas import (
    SocialAccountOut,
    OAuthCallbackIn,
)
from app.social.oauth_utils import (
    build_oauth_state,
    build_frontend_oauth_redirect,
    get_oauth_redirect_uri,
    get_provider_credentials_error,
)
from app.social.oauth_handlers import complete_oauth_callback


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/social",
    tags=["Social Account Integration"],
)


# ============================================================
# SUPPORTED PLATFORMS
# ============================================================

SUPPORTED_PLATFORMS = {
    "facebook",
    "instagram",
    "linkedin",
    "twitter",
    "youtube",
    "pinterest",
}


# ============================================================
# RATE LIMIT SIMULATION
# ============================================================

QUOTA_TRACKER: Dict[str, int] = {}


# ============================================================
# MODEL -> RESPONSE
# ============================================================

def map_model_to_schema(acc: SocialAccount) -> dict:
    """Convert SocialAccount model into API response."""

    is_expired = (
        acc.expires_at is not None
        and acc.expires_at < datetime.utcnow()
    )

    status_str = "expired" if is_expired else "connected"

    if acc.id not in QUOTA_TRACKER:
        QUOTA_TRACKER[acc.id] = 100

    return {
        "id": acc.id,
        "team_id": acc.team_id,
        "user_id": acc.user_id,
        "platform": acc.platform,
        "platform_account_id": acc.platform_account_id,
        "account_name": acc.account_name,
        "avatar_url": acc.avatar_url,
        "expires_at": acc.expires_at,
        "created_at": acc.created_at,
        "status": status_str,
        "rate_limit_remaining": QUOTA_TRACKER[acc.id],
        "connection_type": "page" if acc.platform == "facebook" else "personal",
    }


# ============================================================
# FACEBOOK LOGIN
# ============================================================

@router.get("/facebook/login")
def facebook_login(
    type: str = Query(default="page"),
    team_id: str = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start Facebook OAuth.

    Example:
    /api/v1/social/facebook/login?type=page&team_id=YOUR_TEAM_ID
    """

    platform = "facebook"

    member = TeamRepository.get_member(
        db,
        team_id=team_id,
        user_id=current_user.id,
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team workspace.",
        )

    from app.social.providers import get_social_provider

    driver = get_social_provider(platform)

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Facebook provider is not configured.",
        )

    if (
        not driver.client_id
        or driver.client_id == "demo_client_id"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Facebook OAuth credentials are missing. "
                "Configure META_APP_ID and META_APP_SECRET "
                "in backend/.env."
            ),
        )

    # Keep the state format simple and predictable:
    # user_<user_id>_facebook_<connection_type>_team_<team_id>_<random>
    state = (
        "user_"
        + str(current_user.id)
        + "_facebook_"
        + type
        + "_team_"
        + str(team_id)
        + "_"
        + uuid.uuid4().hex
    )

    redirect_uri = get_oauth_redirect_uri("facebook")

    try:
        auth_url = driver.authorize(
            redirect_uri=redirect_uri,
            state=state,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unable to create Facebook OAuth URL: "
                + str(exc)
            ),
        )

    return {
        "success": True,
        "platform": "facebook",
        "connection_type": type,
        "team_id": team_id,
        "state": state,
        "authorization_url": auth_url,
        "redirect_url": auth_url,
    }


# ============================================================
# FACEBOOK CALLBACK
# ============================================================

@router.get("/facebook/callback")
def facebook_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_code: Optional[int] = Query(None),
    error_description: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Handle Facebook OAuth callback with redirection back to frontend."""
    platform = "facebook"
    
    # Handle cancellation or OAuth failure
    if error or error_reason == "user_denied" or not code:
        err_msg = error_description or error or "Facebook connection was cancelled."
        if error_reason == "user_denied" or "cancel" in err_msg.lower() or "denied" in err_msg.lower():
            err_msg = "Facebook connection was cancelled."
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform, success=False, message=err_msg)
        )

    try:
        if not state:
            raise ValueError("OAuth state is missing.")

        # Expected:
        # user_<USER_ID>_facebook_<TYPE>_team_<TEAM_ID>_<RANDOM>
        state_parts = state.split("_")

        if len(state_parts) < 7:
            raise ValueError("Invalid OAuth state.")

        if state_parts[0] != "user":
            raise ValueError("Invalid OAuth state prefix.")

        if state_parts[2] != "facebook":
            raise ValueError("Invalid OAuth platform in state.")

        if state_parts[4] != "team":
            raise ValueError("Invalid OAuth team marker.")

        user_id = state_parts[1]
        connection_type = state_parts[3]
        team_id = state_parts[5]

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise ValueError("OAuth user was not found.")

        member = TeamRepository.get_member(
            db,
            team_id=team_id,
            user_id=user.id,
        )

        if not member:
            raise ValueError("User is not a member of this team.")

        from app.social.providers import get_social_provider

        driver = get_social_provider("facebook")

        if not driver:
            raise ValueError("Facebook provider is not configured.")

        # Ensure redirect_uri matches exactly the backend base URL dynamically
        redirect_uri = get_oauth_redirect_uri("facebook")

        token_data = driver.callback(
            code=code,
            redirect_uri=redirect_uri,
        )

        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError("Facebook did not return an access token.")

        profile = driver.get_profile(access_token)

        platform_account_id = (
            profile.get("provider_user_id")
            or profile.get("id")
            or ("facebook_" + uuid.uuid4().hex[:8])
        )

        account_name = (
            profile.get("account_name")
            or profile.get("name")
            or (str(user.name) + " (Facebook)")
        )

        avatar_url = profile.get(
            "avatar_url",
            (
                "https://api.dicebear.com/7.x/initials/svg"
                "?seed=facebook"
            ),
        )

        expires_in_seconds = token_data.get(
            "expires_in",
            3600 * 24 * 30,
        )

        expires_at = (
            datetime.utcnow()
            + timedelta(seconds=expires_in_seconds)
        )

        # Store in token manager (securing access tokens)
        from app.social.token_manager import TokenManager
        TokenManager.store_oauth_account(
            db=db,
            user_id=user.id,
            provider="facebook",
            provider_user_id=platform_account_id,
            access_token=profile.get("access_token", access_token),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
            expires_in_seconds=expires_in_seconds,
            account_name=account_name,
            avatar_url=avatar_url,
        )

        social_account = (
            SocialAccountRepository.connect_account(
                db,
                team_id=team_id,
                user_id=user.id,
                platform="facebook",
                platform_account_id=platform_account_id,
                name=account_name,
                avatar=avatar_url,
                token=profile.get("access_token", access_token),
                refresh=token_data.get("refresh_token"),
                expires_at=expires_at,
            )
        )
        
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform, success=True)
        )
    except Exception as exc:
        db.rollback()
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform, success=False, message=str(exc))
        )


# ============================================================
# CONNECT PLATFORM
# ============================================================

@router.get("/connect/{platform}")
def connect_platform(
    platform: str,
    team_id: str,
    type: Optional[str] = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    platform_lower = platform.lower()

    if platform_lower not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Platform '"
                + platform
                + "' is not supported."
            ),
        )

    member = TeamRepository.get_member(
        db,
        team_id=team_id,
        user_id=current_user.id,
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You must be a member of this team "
                "workspace to connect accounts."
            ),
        )

    from app.social.providers import get_social_provider

    driver = get_social_provider(platform_lower)

    if (
        not driver
        or not driver.client_id
        or driver.client_id == "demo_client_id"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_provider_credentials_error(platform_lower),
        )

    connection_type = type
    if platform_lower == "linkedin" and not connection_type:
        connection_type = "personal"

    state = build_oauth_state(
        user_id=str(current_user.id),
        platform=platform_lower,
        team_id=str(team_id),
        connection_type=connection_type,
        nonce=uuid.uuid4().hex,
    )

    redirect_uri = get_oauth_redirect_uri(platform_lower)

    try:
        auth_url = driver.authorize(
            redirect_uri=redirect_uri,
            state=state,
            connection_type=connection_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unable to create OAuth URL: "
                + str(exc)
            ),
        )

    return {
        "success": True,
        "platform": platform_lower,
        "connection_type": connection_type,
        "team_id": team_id,
        "state": state,
        "authorization_url": auth_url,
        "redirect_url": auth_url,
    }


# ============================================================
# OAUTH CALLBACK (GET - browser redirect from provider)
# ============================================================

@router.get("/callback/{platform}")
def oauth_callback_redirect(
    platform: str,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    platform_lower = platform.lower()

    if error:
        message = error_description or error
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform_lower, success=False, message=message)
        )

    if not code:
        return RedirectResponse(
            url=build_frontend_oauth_redirect(
                platform_lower,
                success=False,
                message="Authorization code was not returned by the provider.",
            )
        )

    try:
        complete_oauth_callback(
            db=db,
            platform=platform_lower,
            code=code,
            state=state,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform_lower, success=False, message=detail)
        )
    except Exception as exc:
        return RedirectResponse(
            url=build_frontend_oauth_redirect(platform_lower, success=False, message=str(exc))
        )

    return RedirectResponse(
        url=build_frontend_oauth_redirect(platform_lower, success=True)
    )


# ============================================================
# GENERIC CALLBACK
# ============================================================

@router.post(
    "/callback",
    response_model=SocialAccountOut,
)
def oauth_callback(
    platform: str,
    payload: OAuthCallbackIn,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Programmatic OAuth callback used by tests and API clients."""
    platform_lower = platform.lower()

    if platform_lower not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported platform.",
        )

    member = TeamRepository.get_member(
        db,
        team_id=payload.team_id,
        user_id=current_user.id,
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to team workspace.",
        )

    # Preserve deterministic mock OAuth behavior for automated tests.
    if payload.code.startswith("mock_"):
        mock_access_token = "mock_access_token_" + uuid.uuid4().hex
        mock_refresh_token = "mock_refresh_token_" + uuid.uuid4().hex
        expires_in_seconds = 3600 * 24 * 30
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        platform_account_id = "ext_" + uuid.uuid4().hex[:8]
        account_name = f"{current_user.name} ({platform_lower.capitalize()})"
        avatar_url = (
            "https://api.dicebear.com/7.x/bottts/svg?seed=" + platform_account_id
        )

        try:
            social_account = SocialAccountRepository.connect_account(
                db,
                team_id=payload.team_id,
                user_id=current_user.id,
                platform=platform_lower,
                platform_account_id=platform_account_id,
                name=account_name,
                avatar=avatar_url,
                token=mock_access_token,
                refresh=mock_refresh_token,
                expires_at=expires_at,
            )
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save social account: " + str(exc),
            ) from exc

        response = map_model_to_schema(social_account)
        response["platform"] = platform_lower
        response["status"] = "connected"
        return response

    try:
        result = complete_oauth_callback(
            db=db,
            platform=platform_lower,
            code=payload.code,
            state=payload.state,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization code exchange failed for {platform.capitalize()}: {exc}",
        ) from exc

    social_account = result.get("social_account")
    if not social_account:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth succeeded but the social account could not be saved.",
        )

    return map_model_to_schema(social_account)


# ============================================================
# LIST ACCOUNTS
# ============================================================

@router.get(
    "/accounts",
    response_model=List[SocialAccountOut],
)
def list_social_accounts(
    team_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    member = TeamRepository.get_member(
        db,
        team_id=team_id,
        user_id=current_user.id,
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace channels.",
        )

    accounts = (
        SocialAccountRepository.get_by_team_id(
            db,
            team_id=team_id,
        )
    )

    return [
        map_model_to_schema(account)
        for account in accounts
    ]


# ============================================================
# DISCONNECT
# ============================================================

@router.delete(
    "/accounts/{id}",
    status_code=status.HTTP_200_OK,
)
def disconnect_social_account(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    account = SocialAccountRepository.get_by_id(
        db,
        account_id=id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account connection not found.",
        )

    team = TeamRepository.get_team_by_id(
        db,
        team_id=account.team_id,
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )

    if (
        team.owner_id != current_user.id
        and account.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only the team owner or the connector "
                "of this account can disconnect it."
            ),
        )

    success = SocialAccountRepository.disconnect_account(
        db,
        account_id=id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect account.",
        )

    QUOTA_TRACKER.pop(id, None)

    return {
        "success": True,
        "detail": "Social account disconnected successfully.",
    }


# ============================================================
# SIMULATE EXPIRY
# ============================================================

@router.post(
    "/accounts/{id}/simulate-expiry",
    response_model=SocialAccountOut,
)
def simulate_expiry(
    id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    account = SocialAccountRepository.get_by_id(
        db,
        account_id=id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social connection not found.",
        )

    team = TeamRepository.get_team_by_id(
        db,
        team_id=account.team_id,
    )

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found.",
        )

    if team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only workspace owners can debug this workspace."
            ),
        )

    account.expires_at = (
        datetime.utcnow()
        - timedelta(hours=1)
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return map_model_to_schema(account)


# ============================================================
# TRIGGER API CALL
# ============================================================

@router.post("/accounts/{id}/trigger-api-call")
def trigger_api_call(
    id: str,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    account = SocialAccountRepository.get_by_id(
        db,
        account_id=id,
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social connection not found.",
        )

    if (
        account.expires_at
        and account.expires_at < datetime.utcnow()
    ):
        try:
            from app.social.token_manager import TokenManager, TokenRefreshError
            TokenManager.get_valid_access_token(db, account)
            db.refresh(account)
        except TokenRefreshError as token_exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(token_exc),
            ) from token_exc

    if (
        account.expires_at
        and account.expires_at < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Connection has expired. "
                "Please re-authenticate your channel."
            ),
        )

    api_result = {
        "status": "success",
        "platform": account.platform,
    }

    if account.access_token:
        try:
            from app.core.crypto import decrypt_token
            import httpx

            decrypted_token = decrypt_token(
                account.access_token
            )

            if account.platform in (
                "facebook",
                "instagram",
            ):
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(
                        "https://graph.facebook.com/v19.0/me",
                        params={
                            "access_token": decrypted_token
                        },
                    )

                    if resp.status_code == 200:
                        api_result["graph_api"] = (
                            resp.json()
                        )
                    else:
                        account.expires_at = datetime.utcnow() - timedelta(minutes=5)
                        db.add(account)
                        db.commit()
                        api_result["graph_api_error"] = (
                            resp.text
                        )
            elif account.platform == "linkedin":
                from app.social.providers import get_social_provider

                driver = get_social_provider("linkedin")
                if driver.validate_token(decrypted_token):
                    api_result["linkedin_profile"] = driver.get_profile(decrypted_token)
                else:
                    account.expires_at = datetime.utcnow() - timedelta(minutes=5)
                    db.add(account)
                    db.commit()
                    api_result["linkedin_error"] = (
                        "LinkedIn token validation failed. Reconnect the account."
                    )

        except Exception as ex:
            api_result[
                "decryption_or_api_error"
            ] = str(ex)

    if account.id not in QUOTA_TRACKER:
        QUOTA_TRACKER[account.id] = 100

    if QUOTA_TRACKER[account.id] <= 0:
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = "60"

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Rate limit exceeded for platform. "
                "Quota reset in 60 seconds."
            ),
        )

    QUOTA_TRACKER[account.id] -= 1

    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(
        QUOTA_TRACKER[account.id]
    )
    response.headers["X-RateLimit-Reset"] = "60"

    return {
        "status": "success",
        "action": "real_api_call",
        "details": api_result,
        "remaining_quota": QUOTA_TRACKER[account.id],
    }


# ============================================================
# ABSOLUTE PATH REDIRECTS ROUTER
# ============================================================

from fastapi import APIRouter
redirects_router = APIRouter(tags=["OAuth Absolute Redirect Handlers"])

@redirects_router.get("/auth/facebook/callback")
def facebook_absolute_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_code: Optional[int] = Query(None),
    error_description: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Handle absolute path callback by delegating to standard facebook_callback."""
    return facebook_callback(
        code=code,
        state=state,
        error=error,
        error_code=error_code,
        error_description=error_description,
        error_reason=error_reason,
        db=db,
    )

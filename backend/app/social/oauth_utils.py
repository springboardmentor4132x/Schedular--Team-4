import logging
from typing import Dict, Optional
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger("socialpilot.social.oauth_utils")

SUPPORTED_OAUTH_PLATFORMS = {
    "facebook",
    "instagram",
    "linkedin",
    "twitter",
    "youtube",
    "pinterest",
}


def get_backend_base_url() -> str:
    return settings.BACKEND_BASE_URL.rstrip("/")


def get_frontend_base_url() -> str:
    return settings.FRONTEND_BASE_URL.rstrip("/")


def get_oauth_redirect_uri(platform: str) -> str:
    platform_lower = platform.lower().strip()
    if platform_lower == "facebook" and settings.FACEBOOK_REDIRECT_URI:
        return settings.FACEBOOK_REDIRECT_URI
    if platform_lower == "instagram" and settings.INSTAGRAM_REDIRECT_URI:
        return settings.INSTAGRAM_REDIRECT_URI
    return f"{get_backend_base_url()}{settings.API_V1_STR}/social/callback/{platform_lower}"


def build_oauth_state(
    user_id: str,
    platform: str,
    team_id: Optional[str] = None,
    connection_type: Optional[str] = None,
    nonce: Optional[str] = None,
) -> str:
    state = f"user_{user_id}_{platform.lower()}"
    if connection_type:
        state += f"_{connection_type}"
    if team_id:
        state += f"_team_{team_id}"
    if nonce:
        state += f"_{nonce}"
    return state


def parse_oauth_state(state: Optional[str]) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {
        "user_id": None,
        "platform": None,
        "team_id": None,
        "connection_type": None,
    }
    if not state or not state.startswith("user_"):
        return result

    parts = state.split("_")
    if len(parts) < 3:
        return result

    result["user_id"] = parts[1]
    result["platform"] = parts[2]

    if "_team_" in state:
        team_segment = state.split("_team_", 1)[1]
        result["team_id"] = team_segment.split("_")[0]

    # Format: user_<id>_<platform>_<connection_type>_team_<team_id>_<nonce>
    if len(parts) >= 6 and parts[4] == "team":
        result["connection_type"] = parts[3]

    return result


def get_provider_credentials_error(platform: str) -> str:
    platform_lower = platform.lower()
    if platform_lower == "linkedin":
        return (
            "LinkedIn OAuth credentials are missing. Configure LINKEDIN_CLIENT_ID and "
            "LINKEDIN_CLIENT_SECRET in backend/.env."
        )
    if platform_lower in ("facebook", "instagram"):
        return (
            "Meta OAuth credentials are missing. Configure META_APP_ID and META_APP_SECRET "
            "(or platform-specific client ID/secret) in backend/.env."
        )
    if platform_lower in ("twitter", "x"):
        return (
            "X/Twitter OAuth credentials are missing. Configure X_CLIENT_ID and "
            "X_CLIENT_SECRET in backend/.env."
        )
    if platform_lower in ("youtube", "google"):
        return (
            "Google OAuth credentials are missing. Configure GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET in backend/.env."
        )
    return (
        f"OAuth credentials are missing for {platform.capitalize()}. "
        "Configure the required client ID and secret in backend/.env."
    )


def build_frontend_oauth_redirect(
    platform: str,
    success: bool,
    message: Optional[str] = None,
) -> str:
    base = f"{get_frontend_base_url()}/social-accounts"
    if success:
        return f"{base}?connected={quote(platform.lower())}"

    error_message = message or "LinkedIn authorization was cancelled or failed."
    return f"{base}?error={quote(error_message)}&platform={quote(platform.lower())}"

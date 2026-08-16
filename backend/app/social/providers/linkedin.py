import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.social.providers.base import BaseSocialProvider

logger = logging.getLogger("socialpilot.social.linkedin")


class LinkedInProvider(BaseSocialProvider):
    """LinkedIn OAuth 2.0 + Posts API driver for personal profiles and company pages."""

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
    POSTS_URL = "https://api.linkedin.com/rest/posts"
    ORG_ACLS_URL = "https://api.linkedin.com/rest/organizationAcls"

    PERSONAL_SCOPES = "openid profile email w_member_social"
    # r_organization_admin is required to list administered company pages via organizationAcls
    COMPANY_SCOPES = (
        "openid profile email w_member_social w_organization_social r_organization_admin"
    )

    def _api_headers(self, access_token_val: str, include_version: bool = True) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {access_token_val}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        if include_version:
            headers["LinkedIn-Version"] = settings.LINKEDIN_API_VERSION
        return headers

    def _scopes_for_connection(self, connection_type: Optional[str] = None) -> str:
        if connection_type == "company":
            return self.COMPANY_SCOPES
        return self.PERSONAL_SCOPES

    def authorize(
        self,
        redirect_uri: str,
        state: str,
        connection_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": self._scopes_for_connection(connection_type or kwargs.get("connection_type")),
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    def callback(self, code: str, redirect_uri: str, **kwargs) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(self.TOKEN_URL, data=data, headers=headers)
            if resp.status_code != 200:
                logger.error("LinkedIn OAuth token exchange failed: %s", resp.text)
                self._raise_token_error(resp)

            payload = resp.json()
            access_token = payload.get("access_token")
            if not access_token:
                raise ValueError("LinkedIn token response did not include an access_token.")

            expires_in = int(payload.get("expires_in", 5184000))
            refresh_token = payload.get("refresh_token")
            if not refresh_token:
                logger.warning(
                    "LinkedIn did not return a refresh token. "
                    "Most apps must re-authorize every ~60 days unless LinkedIn grants refresh-token access."
                )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "scope": payload.get("scope"),
                "token_type": payload.get("token_type", "bearer"),
            }

    def refresh_token(self, refresh_token_val: str) -> Dict[str, Any]:
        if not refresh_token_val:
            raise ValueError("LinkedIn refresh token is missing.")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token_val,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(self.TOKEN_URL, data=data, headers=headers)
            if resp.status_code != 200:
                logger.error("LinkedIn token refresh failed: %s", resp.text)
                self._raise_token_error(resp)

            payload = resp.json()
            access_token = payload.get("access_token")
            if not access_token:
                raise ValueError("LinkedIn refresh response did not include an access_token.")

            return {
                "access_token": access_token,
                "refresh_token": payload.get("refresh_token", refresh_token_val),
                "expires_in": payload.get("expires_in", 5184000),
                "scope": payload.get("scope"),
            }

    def validate_token(self, access_token_val: str) -> bool:
        headers = {"Authorization": f"Bearer {access_token_val}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(self.USERINFO_URL, headers=headers)
            return resp.status_code == 200

    def get_profile(self, access_token_val: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {access_token_val}"}
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(self.USERINFO_URL, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch LinkedIn profile: {resp.text}")

            data = resp.json()
            member_id = self._normalize_member_id(data.get("sub", ""))
            return {
                "provider_user_id": member_id,
                "username": data.get("name", "LinkedIn Member"),
                "name": data.get("name", "LinkedIn Member"),
                "account_name": data.get("name", "LinkedIn Member"),
                "avatar_url": data.get("picture", ""),
                "author_urn": f"urn:li:person:{member_id}",
            }

    def get_admin_organizations(self, access_token_val: str) -> List[Dict[str, str]]:
        params = {
            "q": "roleAssignee",
            "role": "ADMINISTRATOR",
            "state": "APPROVED",
        }
        headers = self._api_headers(access_token_val)

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(self.ORG_ACLS_URL, params=params, headers=headers)
            if resp.status_code != 200:
                logger.error("LinkedIn organization lookup failed: %s", resp.text)
                raise ValueError(
                    "Unable to load LinkedIn Company Pages for this account. "
                    "Ensure your LinkedIn app has Community Management API access with "
                    "w_organization_social and r_organization_admin scopes enabled, and that "
                    "you are an administrator of at least one company page."
                )

            elements = resp.json().get("elements", [])
            organizations: List[Dict[str, str]] = []
            for element in elements:
                org_id = self._extract_organization_id(element)
                if not org_id:
                    continue
                org_name = self._extract_organization_name(element, org_id)
                organizations.append(
                    {
                        "id": str(org_id),
                        "name": org_name,
                        "urn": f"urn:li:organization:{org_id}",
                    }
                )
            return organizations

    def upload_media(self, access_token_val: str, media_url: str, media_type: str = "image") -> str:
        return media_url

    def publish_post(
        self,
        access_token_val: str,
        content: str,
        media_urls: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        author_urn = kwargs.get("author_urn") or kwargs.get("target_id") or ""
        if author_urn and not str(author_urn).startswith("urn:li:"):
            author_urn = f"urn:li:person:{author_urn}"

        if not author_urn:
            profile = self.get_profile(access_token_val)
            author_urn = profile["author_urn"]

        if media_urls:
            logger.warning(
                "LinkedIn media publishing is not yet implemented in this integration; publishing text-only content."
            )

        payload = {
            "author": author_urn,
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        headers = self._api_headers(access_token_val)

        logger.info(
            "Sending post request to LinkedIn. Author URN: %s, Posts URL: %s, Commentary Length: %d",
            author_urn,
            self.POSTS_URL,
            len(content)
        )

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.POSTS_URL, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                logger.error(
                    "LinkedIn publishing failed (Status: %d, Response: %s)",
                    resp.status_code,
                    resp.text
                )
                raise ValueError(self._format_publish_error(resp))

            post_id = resp.headers.get("x-restli-id") or ""
            if not post_id and resp.text:
                try:
                    post_id = resp.json().get("id", "")
                except Exception:
                    post_id = ""

            logger.info("Successfully published to LinkedIn. Post ID: %s", post_id)

            return {
                "id": post_id,
                "platform": "linkedin",
                "status": "published",
                "raw_response": {"status_code": resp.status_code, "body": resp.text},
            }

    def disconnect(self, access_token_val: str) -> bool:
        return True

    @staticmethod
    def _extract_organization_id(element: Dict[str, Any]) -> Optional[str]:
        organization = element.get("organization~") or {}
        org_id = organization.get("id")
        if org_id:
            return str(org_id)

        organization_urn = element.get("organization") or ""
        if isinstance(organization_urn, str) and organization_urn.startswith("urn:li:organization:"):
            return organization_urn.split(":")[-1]
        return None

    @staticmethod
    def _extract_organization_name(element: Dict[str, Any], org_id: str) -> str:
        organization = element.get("organization~") or {}
        localized = organization.get("localizedName")
        if isinstance(localized, dict):
            preferred = localized.get("localized") or localized.get("en_US")
            if preferred:
                return str(preferred)
        if localized:
            return str(localized)
        return f"Organization {org_id}"

    @staticmethod
    def _normalize_member_id(raw_sub: str) -> str:
        if not raw_sub:
            return "me"
        if raw_sub.startswith("urn:li:person:"):
            return raw_sub.split(":")[-1]
        return raw_sub

    @staticmethod
    def _raise_token_error(resp: httpx.Response) -> None:
        try:
            payload = resp.json()
            error = payload.get("error_description") or payload.get("error") or resp.text
        except Exception:
            error = resp.text
        raise ValueError(f"LinkedIn OAuth error: {error}")

    @staticmethod
    def _format_publish_error(resp: httpx.Response) -> str:
        try:
            payload = resp.json()
            message = payload.get("message") or payload.get("error") or payload.get("status")
            details = payload.get("serviceErrorCode") or payload.get("code")
            if details:
                return f"LinkedIn publishing error ({resp.status_code}): {message} [{details}]"
            return f"LinkedIn publishing error ({resp.status_code}): {message}"
        except Exception:
            cleaned = re.sub(r"\s+", " ", resp.text).strip()
            return f"LinkedIn publishing error ({resp.status_code}): {cleaned or 'Unknown error'}"

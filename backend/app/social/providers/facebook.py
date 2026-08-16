import logging
import urllib.parse
import httpx
from typing import Dict, Any, List, Optional
from app.social.providers.base import BaseSocialProvider

logger = logging.getLogger("socialpilot.social.facebook")

class FacebookProvider(BaseSocialProvider):
    """Official Facebook Graph API v19.0 OAuth 2.0 and Publishing Driver."""

    GRAPH_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, client_id: str, client_secret: str, config_id: Optional[str] = None):
        super().__init__(client_id, client_secret)
        self.config_id = config_id

    def authorize(self, redirect_uri: str, state: str, **kwargs) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
        }
        config_id = kwargs.get("config_id") or self.config_id
        if config_id:
            params["config_id"] = config_id
        else:
            params["scope"] = "pages_show_list,pages_read_engagement,pages_manage_posts,public_profile"
        return f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"

    def callback(self, code: str, redirect_uri: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.GRAPH_URL}/oauth/access_token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.error(f"Facebook OAuth token exchange failed: {resp.text}")
                raise ValueError(f"Facebook token exchange error: {resp.text}")
            data = resp.json()

        # Exchange short-lived token for long-lived 60-day token
        long_lived = self.refresh_token(data["access_token"])
        return {
            "access_token": long_lived.get("access_token", data["access_token"]),
            "refresh_token": long_lived.get("refresh_token", ""),
            "expires_in": long_lived.get("expires_in", 5184000),
            "token_type": "bearer"
        }

    def refresh_token(self, refresh_token_val: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived page token."""
        url = f"{self.GRAPH_URL}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "fb_exchange_token": refresh_token_val
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Facebook token exchange fallback: {resp.text}")
                return {"access_token": refresh_token_val, "expires_in": 5184000}
            return resp.json()

    def validate_token(self, access_token_val: str) -> bool:
        url = f"{self.GRAPH_URL}/me"
        params = {"access_token": access_token_val}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            return resp.status_code == 200

    def _handle_error(self, status_code: int, response_text: str):
        import json
        err_msg = ""
        err_code = None
        err_type = None
        err_subcode = None
        try:
            err_data = json.loads(response_text).get("error", {})
            err_msg = err_data.get("message", "")
            err_code = err_data.get("code")
            err_type = err_data.get("type")
            err_subcode = err_data.get("error_subcode")
        except Exception:
            err_msg = response_text

        # Sanitize error detail to prevent access tokens leak
        clean_msg = err_msg
        if clean_msg:
            import re
            clean_msg = re.sub(r"access_token=[a-zA-Z0-9_\-\.]+", "access_token=********", clean_msg)
            clean_msg = re.sub(r"EAAB[a-zA-Z0-9]+", "********", clean_msg)

        detail_parts = []
        if clean_msg:
            detail_parts.append(clean_msg)
        if err_type:
            detail_parts.append(f"Type: {err_type}")
        if err_code is not None:
            detail_parts.append(f"Code: {err_code}")
        if err_subcode is not None:
            detail_parts.append(f"Subcode: {err_subcode}")

        detail_str = ", ".join(detail_parts)

        if status_code == 401 or err_code in (190, 102):
            raise ValueError(f"Facebook authorization expired. Please reconnect your Facebook Page. ({detail_str})")
        elif status_code == 403 or err_code in (10, 200, 283):
            raise ValueError(f"Facebook permissions are insufficient. Please reconnect or review the required permissions. ({detail_str})")
        elif status_code == 429 or err_code in (4, 17, 32, 613):
            raise ValueError(f"Facebook API rate limit reached. Please try again later. ({detail_str})")
        else:
            raise ValueError(f"Facebook rejected the publishing request: {detail_str or 'Unknown Facebook error'}")

    def get_profile(self, access_token_val: str) -> Dict[str, Any]:
        url = f"{self.GRAPH_URL}/me/accounts"
        params = {
            "fields": "id,name,picture.width(200).height(200),access_token",
            "access_token": access_token_val
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code != 200:
                self._handle_error(resp.status_code, resp.text)
            data = resp.json()
            accounts = data.get("data", [])
            if not accounts:
                raise ValueError("No Facebook Pages were found for this account.")
            
            # Select first page as default page to connect
            page = accounts[0]
            picture_url = page.get("picture", {}).get("data", {}).get("url", "")
            return {
                "provider_user_id": page["id"],
                "username": page.get("name", "Facebook Page"),
                "name": page.get("name", "Facebook Page"),
                "avatar_url": picture_url,
                "access_token": page.get("access_token", access_token_val)
            }

    def upload_media(self, access_token_val: str, media_url: str, media_type: str = "image") -> str:
        # Facebook allows direct URL parameter attachment in feed post or photo endpoint
        return media_url

    def publish_post(
        self,
        access_token_val: str,
        content: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        import os
        import mimetypes
        target_id = kwargs.get("target_id", "me")
        
        media_url = media_urls[0] if media_urls else None
        is_video = False
        is_image = False
        if media_url:
            lower_url = media_url.lower()
            if any(ext in lower_url for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp"]):
                is_video = True
            elif any(ext in lower_url for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]):
                is_image = True

        # Check if the file exists locally in static/uploads
        filename = os.path.basename(media_url) if media_url else None
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        local_path = os.path.join(backend_dir, "static", "uploads", filename) if filename else None
        has_local_file = local_path and os.path.exists(local_path)

        payload = {}
        files = None

        if is_video:
            url = f"{self.GRAPH_URL}/{target_id}/videos"
            if has_local_file:
                payload = {
                    "description": content,
                    "access_token": access_token_val
                }
                files = {
                    "source": (filename, open(local_path, "rb"), "video/mp4")
                }
            else:
                payload = {
                    "description": content,
                    "file_url": media_url,
                    "access_token": access_token_val
                }
        elif is_image:
            url = f"{self.GRAPH_URL}/{target_id}/photos"
            if has_local_file:
                mime_type, _ = mimetypes.guess_type(local_path)
                if not mime_type:
                    mime_type = "image/jpeg"
                payload = {
                    "caption": content,
                    "access_token": access_token_val
                }
                files = {
                    "source": (filename, open(local_path, "rb"), mime_type)
                }
            else:
                payload = {
                    "caption": content,
                    "url": media_url,
                    "access_token": access_token_val
                }
        else:
            url = f"{self.GRAPH_URL}/{target_id}/feed"
            payload = {
                "message": content,
                "access_token": access_token_val
            }
            if media_urls and len(media_urls) > 0:
                payload["link"] = media_urls[0]

        # Determine content type
        content_type = "text"
        if is_video:
            content_type = "video"
        elif is_image:
            content_type = "image"

        # Determine endpoint path
        if is_video:
            endpoint = "/*******/videos"
        elif is_image:
            endpoint = "/*******/photos"
        else:
            endpoint = "/*******/feed"

        account_name = kwargs.get("account_name", "Unknown Page")

        print("========== FACEBOOK PUBLISH DEBUG ==========\n")
        print("Platform: facebook")
        print(f"Account: {account_name}")
        print("Page ID: ********")
        print(f"Content Type: {content_type}")
        print("Graph API Version: v19.0")
        print(f"Endpoint: {endpoint}")
        print(f"Has Page Token: {'true' if access_token_val else 'false'}")
        print(f"Token Valid: {'true' if access_token_val else 'false'}")
        print(f"Message Present: {'true' if content else 'false'}")
        print(f"Media Present: {'true' if media_urls else 'false'}\n")

        resp_status = "N/A"
        fb_err_code = "N/A"
        fb_err_type = "N/A"
        fb_err_msg = "N/A"

        opened_files = []
        try:
            httpx_files = {}
            if files:
                for k, v in files.items():
                    opened_files.append(v[1])
                    httpx_files[k] = (v[0], v[1], v[2])

            with httpx.Client(timeout=30.0) as client:
                if httpx_files:
                    resp = client.post(url, data=payload, files=httpx_files)
                else:
                    resp = client.post(url, data=payload)

                resp_status = str(resp.status_code)
                if resp.status_code not in (200, 201):
                    logger.error(f"Facebook publish failed: {resp.text}")
                    try:
                        import json
                        err_data = json.loads(resp.text).get("error", {})
                        fb_err_msg = err_data.get("message", "N/A")
                        fb_err_code = str(err_data.get("code", "N/A"))
                        fb_err_type = err_data.get("type", "N/A")
                    except Exception:
                        fb_err_msg = resp.text
                    self._handle_error(resp.status_code, resp.text)
                res_data = resp.json()
                return {
                    "id": res_data.get("id", ""),
                    "platform": "facebook",
                    "status": "published",
                    "raw_response": res_data
                }
        except Exception as exc:
            if fb_err_msg == "N/A":
                fb_err_msg = str(exc)
            raise exc
        finally:
            for f_obj in opened_files:
                try:
                    f_obj.close()
                except Exception:
                    pass
            print(f"Facebook Response Status: {resp_status}")
            print(f"Facebook Error Code: {fb_err_code}")
            print(f"Facebook Error Type: {fb_err_type}")
            print(f"Facebook Error Message: {fb_err_msg}")
            print("\n=============================================")

    def disconnect(self, access_token_val: str) -> bool:
        url = f"{self.GRAPH_URL}/me/permissions"
        params = {"access_token": access_token_val}
        with httpx.Client(timeout=10.0) as client:
            resp = client.delete(url, params=params)
            return resp.status_code == 200

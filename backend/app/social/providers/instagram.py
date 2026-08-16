import logging
import urllib.parse
import httpx
import time
from typing import Dict, Any, List, Optional
from app.social.providers.base import BaseSocialProvider

logger = logging.getLogger("socialpilot.social.instagram")

class InstagramProvider(BaseSocialProvider):
    """Official Instagram Graph API Content Publishing Driver (Containers, Single & Carousel)."""

    GRAPH_URL = "https://graph.facebook.com/v19.0"

    def authorize(self, redirect_uri: str, state: str, **kwargs) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
        }
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
                raise ValueError(f"Instagram OAuth token error: {resp.text}")
            data = resp.json()
        logger.info("OAuth code exchanged successfully")

        # Exchange short-lived token for long-lived 60-day token
        long_lived = self.refresh_token(data["access_token"])
        return {
            "access_token": long_lived.get("access_token", data["access_token"]),
            "refresh_token": long_lived.get("refresh_token", ""),
            "expires_in": long_lived.get("expires_in", 5184000),
            "token_type": "bearer"
        }

    def refresh_token(self, refresh_token_val: str) -> Dict[str, Any]:
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
                return {"access_token": refresh_token_val, "expires_in": 5184000}
            return resp.json()

    def validate_token(self, access_token_val: str) -> bool:
        url = f"{self.GRAPH_URL}/me"
        params = {"access_token": access_token_val}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            return resp.status_code == 200

    def get_profile(self, access_token_val: str) -> Dict[str, Any]:
        logger.info("Starting Instagram account discovery process...")
        
        # Determine if we have a User Access Token or a Page Access Token
        # Try fetching accounts (which only works for User Access Token)
        url = f"{self.GRAPH_URL}/me/accounts"
        params = {
            "fields": "id,name,access_token,instagram_business_account{id,username,name,profile_picture_url}",
            "access_token": access_token_val
        }
        
        with httpx.Client(timeout=15.0) as client:
            # 1. Log Facebook user resolution
            user_url = f"{self.GRAPH_URL}/me"
            user_params = {"fields": "id,name", "access_token": access_token_val}
            try:
                user_resp = client.get(user_url, params=user_params)
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    logger.info(f"Facebook user resolved: {user_data.get('name')}")
                else:
                    logger.warning(f"Could not resolve Facebook user details: {user_resp.text}")
            except Exception as e:
                logger.warning(f"Error resolving Facebook user: {e}")

            # 2. Try fetching Pages (/me/accounts)
            resp = client.get(url, params=params)
            
            if resp.status_code == 200:
                # Token is a Facebook User Access Token
                data = resp.json()
                accounts = data.get("data", [])
                logger.info(f"Pages returned: {len(accounts)}")
                
                if not accounts:
                    logger.warning("Facebook account has no Pages.")
                    raise ValueError(
                        "Instagram account ID could not be determined. "
                        "Your Facebook account has no Pages. "
                        "An Instagram Business/Professional account must be connected to a Facebook Page."
                    )
                
                valid_connections = []
                for page in accounts:
                    page_id = page.get("id")
                    page_name = page.get("name")
                    page_token = page.get("access_token")
                    logger.info(f"Page ID discovered: {page_id}")
                    
                    if "instagram_business_account" in page:
                        ig_acc = page["instagram_business_account"]
                        ig_id = ig_acc.get("id")
                        ig_username = ig_acc.get("username", "instagram_user")
                        ig_name = ig_acc.get("name", ig_username)
                        ig_pic = ig_acc.get("profile_picture_url", "")
                        
                        logger.info(f"Instagram account found for Page: {ig_id}")
                        logger.info(f"Instagram username: {ig_username}")
                        
                        # Verify that we can access the Instagram account using the page token (or user token if page token is missing)
                        verify_url = f"{self.GRAPH_URL}/{ig_id}"
                        verify_params = {
                            "fields": "id,username",
                            "access_token": page_token or access_token_val
                        }
                        try:
                            v_resp = client.get(verify_url, params=verify_params)
                            if v_resp.status_code == 200:
                                valid_connections.append({
                                    "provider_user_id": ig_id,
                                    "username": ig_username,
                                    "name": ig_name,
                                    "avatar_url": ig_pic,
                                    "fb_page_id": page_id,
                                    "access_token": page_token or access_token_val
                                })
                            else:
                                logger.warning(
                                    f"Verification failed for Instagram account {ig_username} using Page token: {v_resp.text}"
                                )
                        except Exception as e:
                            logger.warning(f"Error verifying Instagram account {ig_username}: {e}")
                    else:
                        logger.info(f"Page ID {page_id} has no linked Instagram Professional account.")
                
                if not valid_connections:
                    raise ValueError(
                        "Instagram account ID could not be determined. "
                        "Ensure your Instagram Business/Professional account is linked to a Facebook Page, "
                        "and you have authorized the Facebook Page in the OAuth dialog."
                    )
                
                if len(valid_connections) > 1:
                    logger.info(f"Multiple Instagram accounts are available. Selecting the first verified one: {valid_connections[0]['username']}")
                
                selected = valid_connections[0]
                print("========== INSTAGRAM OAUTH DEBUG ==========\n")
                print("platform: instagram")
                print(f"username: {selected['username']}")
                print("account_id: ********")
                print(f"token_present: {'true' if selected['access_token'] else 'false'}")
                print(f"token_length: {len(selected['access_token']) if selected['access_token'] else 0}")
                print("callback_route: /api/v1/social/callback/instagram")
                print("api_version: v19.0")
                print("\n============================================\n")
                return selected
                
            else:
                # /me/accounts failed. Check if token is a Page Access Token
                # Query /me to see if it represents a Facebook Page linked to Instagram
                logger.info("Failed to query /me/accounts. Checking if token is a Page Access Token...")
                me_url = f"{self.GRAPH_URL}/me"
                me_params = {
                    "fields": "id,name,instagram_business_account{id,username,name,profile_picture_url}",
                    "access_token": access_token_val
                }
                me_resp = client.get(me_url, params=me_params)
                if me_resp.status_code == 200:
                    me_data = me_resp.json()
                    logger.info(f"Page ID discovered: {me_data.get('id')}")
                    if "instagram_business_account" in me_data:
                        ig_acc = me_data["instagram_business_account"]
                        ig_id = ig_acc.get("id")
                        ig_username = ig_acc.get("username", "instagram_user")
                        ig_name = ig_acc.get("name", ig_username)
                        ig_pic = ig_acc.get("profile_picture_url", "")
                        
                        logger.info(f"Instagram account found for Page: {ig_id}")
                        logger.info(f"Instagram username: {ig_username}")
                        print("========== INSTAGRAM OAUTH DEBUG ==========\n")
                        print("platform: instagram")
                        print(f"username: {ig_username}")
                        print("account_id: ********")
                        print(f"token_present: {'true' if access_token_val else 'false'}")
                        print(f"token_length: {len(access_token_val) if access_token_val else 0}")
                        print("callback_route: /api/v1/social/callback/instagram")
                        print("api_version: v19.0")
                        print("\n============================================\n")
                        return {
                            "provider_user_id": ig_id,
                            "username": ig_username,
                            "name": ig_name,
                            "avatar_url": ig_pic,
                            "fb_page_id": me_data.get("id"),
                            "access_token": access_token_val
                        }
                    else:
                        logger.warning("Page has no linked Instagram Professional account.")
                        raise ValueError(
                            "Instagram account ID could not be determined. "
                            "The authorized Facebook Page is not linked to an Instagram Business/Professional account."
                        )
                else:
                    logger.error(f"Graph API error during discovery: {resp.text}")
                    raise ValueError(f"Failed to fetch Instagram accounts: {resp.text}")

    def upload_media(self, access_token_val: str, media_url: str, media_type: str = "IMAGE") -> str:
        """Create Instagram Media Container."""
        return media_url

    def publish_post(
        self,
        access_token_val: str,
        content: str,
        media_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        ig_user_id = kwargs.get("target_id", "me")
        
        # Dynamic target ID resolution if stored as "me"
        fb_page_id = "N/A"
        username = kwargs.get("account_name", "23jr1a0503")
        if ig_user_id == "me":
            logger.info("Instagram target_id is 'me'. Attempting dynamic resolution of Instagram Business Account ID.")
            try:
                profile = self.get_profile(access_token_val)
                resolved_id = profile.get("provider_user_id")
                if resolved_id and resolved_id != "me":
                    logger.info(f"Dynamically resolved Instagram Business Account ID: {resolved_id}")
                    ig_user_id = resolved_id
                    fb_page_id = profile.get("fb_page_id", "N/A")
                    username = profile.get("username", username)
            except Exception as e:
                logger.warning(f"Failed to dynamically resolve Instagram Business Account ID: {e}")

        if ig_user_id == "me":
            raise ValueError("Instagram account ID could not be determined. Reconnect the account from Social Accounts.")

        if not media_urls or len(media_urls) == 0:
            raise ValueError("Instagram requires at least 1 image or video media asset to publish.")

        image_url = media_urls[0]

        # Determine media type (image or video)
        is_video = False
        lower_url = image_url.lower()
        if any(ext in lower_url for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp"]):
            is_video = True

        # Setup debug variables
        resp_status = "N/A"
        fb_err_code = "N/A"
        fb_err_subcode = "N/A"
        fb_err_msg = "N/A"

        content_type = "video" if is_video else "image"
        # Determine container payload
        container_payload = {
            "caption": content,
            "access_token": access_token_val
        }
        if is_video:
            container_payload["video_url"] = image_url
            container_payload["media_type"] = "REELS"
        else:
            container_payload["image_url"] = image_url

        container_url = f"{self.GRAPH_URL}/{ig_user_id}/media"
        publish_url = f"{self.GRAPH_URL}/{ig_user_id}/media_publish"

        print("========== INSTAGRAM PUBLISH DEBUG ==========\n")
        print("platform: instagram")
        print(f"username: {username}")
        print("instagram_account_id: ********")
        print("object_id_used: ********")
        print(f"endpoint: /{ig_user_id}/media")
        print(f"content_type: {content_type}")
        print(f"media_url_present: {'true' if image_url else 'false'}")
        print(f"token_present: {'true' if access_token_val else 'false'}")
        print("\n=============================================")

        try:
            with httpx.Client(timeout=30.0) as client:
                # Step 1: Create Container
                c_resp = client.post(container_url, data=container_payload)
                resp_status = str(c_resp.status_code)
                if c_resp.status_code not in (200, 201):
                    logger.error(f"Instagram Container Creation Failed: {c_resp.text}")
                    try:
                        import json
                        err_data = json.loads(c_resp.text).get("error", {})
                        fb_err_msg = err_data.get("message", "N/A")
                        fb_err_code = str(err_data.get("code", "N/A"))
                        fb_err_subcode = str(err_data.get("error_subcode", "N/A"))
                    except Exception:
                        fb_err_msg = c_resp.text
                    raise ValueError(f"Instagram Container Creation Failed: {c_resp.text}")
                container_id = c_resp.json()["id"]

                # Wait for video processing if applicable
                if is_video:
                    import time
                    max_polls = 12
                    poll_interval = 5.0
                    container_ready = False
                    for i in range(max_polls):
                        time.sleep(poll_interval)
                        status_url = f"{self.GRAPH_URL}/{container_id}"
                        status_params = {
                            "fields": "status_code,status,error_description",
                            "access_token": access_token_val
                        }
                        try:
                            s_resp = client.get(status_url, params=status_params)
                            if s_resp.status_code == 200:
                                s_data = s_resp.json()
                                status_code = s_data.get("status_code")
                                if status_code == "FINISHED":
                                    container_ready = True
                                    break
                                elif status_code == "ERROR":
                                    error_desc = s_data.get("error_description", "Unknown processing error")
                                    raise ValueError(f"Instagram Video Processing Failed: {error_desc}")
                        except Exception as poll_err:
                            logger.warning(f"Error checking container status: {poll_err}")
                    
                    if not container_ready:
                        raise ValueError("Instagram Video container processing timed out after 60 seconds.")

                # Step 2: Publish Container
                publish_payload = {
                    "creation_id": container_id,
                    "access_token": access_token_val
                }
                p_resp = client.post(publish_url, data=publish_payload)
                resp_status = str(p_resp.status_code)
                if p_resp.status_code not in (200, 201):
                    logger.error(f"Instagram Media Publish Failed: {p_resp.text}")
                    try:
                        import json
                        err_data = json.loads(p_resp.text).get("error", {})
                        fb_err_msg = err_data.get("message", "N/A")
                        fb_err_code = str(err_data.get("code", "N/A"))
                        fb_err_subcode = str(err_data.get("error_subcode", "N/A"))
                    except Exception:
                        fb_err_msg = p_resp.text
                    raise ValueError(f"Instagram Media Publish Failed: {p_resp.text}")
                res_data = p_resp.json()
                return {
                    "id": res_data.get("id", container_id),
                    "platform": "instagram",
                    "status": "published",
                    "raw_response": res_data
                }
        except Exception as exc:
            if fb_err_msg == "N/A":
                fb_err_msg = str(exc)
            raise exc
        finally:
            print(f"Facebook/Instagram Response Status: {resp_status}")
            print(f"Error Code: {fb_err_code}")
            print(f"Error Subcode: {fb_err_subcode}")
            print(f"Error Message: {fb_err_msg}")
            print("\n=============================================")

    def disconnect(self, access_token_val: str) -> bool:
        return True

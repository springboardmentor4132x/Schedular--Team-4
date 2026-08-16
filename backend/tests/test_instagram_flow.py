import pytest
import httpx
from unittest.mock import patch, MagicMock
from app.social.providers.instagram import InstagramProvider

def test_instagram_oauth_callback():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: Initial short-lived token callback response
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = {
            "access_token": "short_user_token_123",
            "expires_in": 3600
        }
        
        # Mock 2: Long-lived refresh/exchange token response
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = {
            "access_token": "long_user_token_456",
            "expires_in": 5184000
        }

        mock_get.side_effect = [mock_resp1, mock_resp2]

        callback_res = provider.callback("mock_code", "http://redirect.uri")

        assert callback_res["access_token"] == "long_user_token_456"
        assert callback_res["expires_in"] == 5184000
        assert mock_get.call_count == 2

def test_instagram_get_profile_success():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: GET /me (Facebook user resolution)
        resp_me = MagicMock()
        resp_me.status_code = 200
        resp_me.json.return_value = {"id": "fb_user_123", "name": "John Doe"}

        # Mock 2: GET /me/accounts (Fetch authorized pages list)
        resp_accounts = MagicMock()
        resp_accounts.status_code = 200
        resp_accounts.json.return_value = {
            "data": [
                {
                    "id": "page_id_789",
                    "name": "My Business Page",
                    "access_token": "page_token_abc",
                    "instagram_business_account": {
                        "id": "ig_account_999",
                        "username": "john_doe_ig",
                        "name": "John Doe Instagram",
                        "profile_picture_url": "https://avatar.url/pic.jpg"
                    }
                }
            ]
        }

        # Mock 3: GET /ig_account_999 (Verification check)
        resp_verify = MagicMock()
        resp_verify.status_code = 200
        resp_verify.json.return_value = {"id": "ig_account_999", "username": "john_doe_ig"}

        mock_get.side_effect = [resp_me, resp_accounts, resp_verify]

        profile = provider.get_profile("user_token_123")

        assert profile["provider_user_id"] == "ig_account_999"
        assert profile["username"] == "john_doe_ig"
        assert profile["name"] == "John Doe Instagram"
        assert profile["avatar_url"] == "https://avatar.url/pic.jpg"
        assert profile["fb_page_id"] == "page_id_789"
        assert profile["access_token"] == "page_token_abc"
        assert mock_get.call_count == 3

def test_instagram_get_profile_page_token():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: GET /me (Facebook user resolution for Page Token)
        resp_me1 = MagicMock()
        resp_me1.status_code = 200
        resp_me1.json.return_value = {"id": "page_id_789", "name": "My Business Page"}

        # Mock 2: GET /me/accounts fails (Page token doesn't have /me/accounts)
        resp_accounts = MagicMock()
        resp_accounts.status_code = 400
        resp_accounts.text = "Endpoint not supported for Page tokens"

        # Mock 3: GET /me with instagram fields succeeds (Page details direct fetch)
        resp_me2 = MagicMock()
        resp_me2.status_code = 200
        resp_me2.json.return_value = {
            "id": "page_id_789",
            "name": "My Business Page",
            "instagram_business_account": {
                "id": "ig_account_999",
                "username": "john_doe_ig",
                "name": "John Doe Instagram",
                "profile_picture_url": "https://avatar.url/pic.jpg"
            }
        }

        mock_get.side_effect = [resp_me1, resp_accounts, resp_me2]

        profile = provider.get_profile("page_token_abc")

        assert profile["provider_user_id"] == "ig_account_999"
        assert profile["username"] == "john_doe_ig"
        assert profile["avatar_url"] == "https://avatar.url/pic.jpg"
        assert profile["fb_page_id"] == "page_id_789"
        assert profile["access_token"] == "page_token_abc"

def test_instagram_get_profile_no_pages():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: GET /me
        resp_me = MagicMock()
        resp_me.status_code = 200
        resp_me.json.return_value = {"id": "fb_user_123", "name": "John Doe"}

        # Mock 2: GET /me/accounts returns empty list of Pages
        resp_accounts = MagicMock()
        resp_accounts.status_code = 200
        resp_accounts.json.return_value = {"data": []}

        mock_get.side_effect = [resp_me, resp_accounts]

        with pytest.raises(ValueError) as exc:
            provider.get_profile("user_token_123")
        assert "Your Facebook account has no Pages" in str(exc.value)

def test_instagram_get_profile_no_instagram_account():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: GET /me
        resp_me = MagicMock()
        resp_me.status_code = 200
        resp_me.json.return_value = {"id": "fb_user_123", "name": "John Doe"}

        # Mock 2: GET /me/accounts returns pages but none have linked instagram accounts
        resp_accounts = MagicMock()
        resp_accounts.status_code = 200
        resp_accounts.json.return_value = {
            "data": [
                {
                    "id": "page_id_789",
                    "name": "My Personal Page"
                    # No instagram_business_account
                }
            ]
        }

        mock_get.side_effect = [resp_me, resp_accounts]

        with pytest.raises(ValueError) as exc:
            provider.get_profile("user_token_123")
        assert "Instagram account ID could not be determined" in str(exc.value)

def test_instagram_get_profile_multiple_pages():
    provider = InstagramProvider("mock_client_id", "mock_client_secret")

    with patch("httpx.Client.get") as mock_get:
        # Mock 1: GET /me
        resp_me = MagicMock()
        resp_me.status_code = 200
        resp_me.json.return_value = {"id": "fb_user_123", "name": "John Doe"}

        # Mock 2: GET /me/accounts returns two pages
        resp_accounts = MagicMock()
        resp_accounts.status_code = 200
        resp_accounts.json.return_value = {
            "data": [
                {
                    "id": "page_id_111",
                    "name": "First Page",
                    "access_token": "page_token_111",
                    "instagram_business_account": {
                        "id": "ig_account_111",
                        "username": "ig_user_111",
                        "name": "First IG",
                        "profile_picture_url": "https://avatar.url/111.jpg"
                    }
                },
                {
                    "id": "page_id_222",
                    "name": "Second Page",
                    "access_token": "page_token_222",
                    "instagram_business_account": {
                        "id": "ig_account_222",
                        "username": "ig_user_222",
                        "name": "Second IG",
                        "profile_picture_url": "https://avatar.url/222.jpg"
                    }
                }
            ]
        }

        # Mock 3: Verification fails for the first page
        resp_verify1 = MagicMock()
        resp_verify1.status_code = 403
        resp_verify1.text = "Permission error"

        # Mock 4: Verification succeeds for the second page
        resp_verify2 = MagicMock()
        resp_verify2.status_code = 200
        resp_verify2.json.return_value = {"id": "ig_account_222", "username": "ig_user_222"}

        mock_get.side_effect = [resp_me, resp_accounts, resp_verify1, resp_verify2]

        profile = provider.get_profile("user_token_123")

        # Second page's Instagram account should be returned since the first failed verification
        assert profile["provider_user_id"] == "ig_account_222"
        assert profile["username"] == "ig_user_222"
        assert profile["fb_page_id"] == "page_id_222"
        assert profile["access_token"] == "page_token_222"
        assert mock_get.call_count == 4

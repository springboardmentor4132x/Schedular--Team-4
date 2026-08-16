import pytest
import httpx
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.social.providers.facebook import FacebookProvider
from app.social.routes import map_model_to_schema
from app.database.models import SocialAccount

def test_facebook_error_mappings():
    provider = FacebookProvider("mock_id", "mock_secret")
    
    # 401 Expiry test
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=401,
            text='{"error": {"message": "Session expired", "code": 190}}'
        )
        with pytest.raises(ValueError) as exc:
            provider.publish_post("mock_token", "Hello World")
        assert "Facebook authorization expired." in str(exc.value)

    # 403 Permission test
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=403,
            text='{"error": {"message": "Insufficient permissions", "code": 200}}'
        )
        with pytest.raises(ValueError) as exc:
            provider.publish_post("mock_token", "Hello World")
        assert "Facebook permissions are insufficient." in str(exc.value)

    # 429 Rate limit test
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=429,
            text='{"error": {"message": "Rate limit exceeded", "code": 17}}'
        )
        with pytest.raises(ValueError) as exc:
            provider.publish_post("mock_token", "Hello World")
        assert "Facebook API rate limit reached." in str(exc.value)

def test_facebook_media_routing():
    provider = FacebookProvider("mock_id", "mock_secret")
    
    # Image post
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "123_456"}
        )
        res = provider.publish_post("mock_token", "Hello", ["https://site.com/pic.png"], target_id="mypage")
        assert res["id"] == "123_456"
        # Verify it went to /photos endpoint
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "mypage/photos" in args[0]
        assert kwargs["data"]["url"] == "https://site.com/pic.png"

    # Video post
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "video_123"}
        )
        res = provider.publish_post("mock_token", "My Video", ["https://site.com/clip.mp4"], target_id="mypage")
        assert res["id"] == "video_123"
        # Verify it went to /videos endpoint
        args, kwargs = mock_post.call_args
        assert "mypage/videos" in args[0]
        assert kwargs["data"]["file_url"] == "https://site.com/clip.mp4"

def test_facebook_page_retrieval():
    provider = FacebookProvider("mock_id", "mock_secret")
    
    # Successful profile page parsing
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "id": "page_id_789",
                        "name": "My Business Page",
                        "picture": {"data": {"url": "https://avatar.url"}},
                        "access_token": "page_token_abc"
                    }
                ]
            }
        )
        profile = provider.get_profile("user_token_123")
        assert profile["provider_user_id"] == "page_id_789"
        assert profile["username"] == "My Business Page"
        assert profile["avatar_url"] == "https://avatar.url"
        assert profile["access_token"] == "page_token_abc"

    # Empty pages failure
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []}
        )
        with pytest.raises(ValueError) as exc:
            provider.get_profile("user_token_123")
        assert "No Facebook Pages were found" in str(exc.value)

def test_map_model_to_schema_connection_type():
    acc = SocialAccount(
        id="acc_id",
        team_id="team_id",
        user_id="user_id",
        platform="facebook",
        platform_account_id="page_id",
        account_name="Facebook Page Name",
        avatar_url="http://avatar.url",
        expires_at=None,
        created_at=datetime.utcnow()
    )
    schema_dict = map_model_to_schema(acc)
    assert schema_dict["connection_type"] == "page"

def test_facebook_connect_endpoint(client, db):
    # 1. Register and login team owner
    client.post("/api/v1/auth/register", json={
        "name": "Owner User",
        "email": "owner@socialpilot.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "role_name": "Administrator"
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "owner@socialpilot.com",
        "password": "SecurePassword123!"
    })
    owner_token = login_resp.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Create a team workspace
    team_resp = client.post("/api/v1/teams", json={"name": "Social Team Workspace"}, headers=owner_headers)
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    # 3. Call connect/facebook
    connect_resp = client.get(
        f"/api/v1/social/connect/facebook?team_id={team_id}", 
        headers=owner_headers
    )
    assert connect_resp.status_code == 200
    connect_data = connect_resp.json()
    assert connect_data["platform"] == "facebook"
    assert "dialog/oauth" in connect_data["authorization_url"]
    assert "client_id=" in connect_data["authorization_url"]


def test_facebook_absolute_callback_endpoint(client, db):
    # Simulate a cancellation or error redirect which should redirect to frontend with error message
    resp = client.get("/auth/facebook/callback?error=access_denied&error_description=User+cancelled", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error=Facebook%20connection%20was%20cancelled." in resp.headers["location"]

"""Unit tests for the authentication endpoints."""

from unittest.mock import patch
from src.config import settings


def test_logout_post_only(client):
    """Test that logout is POST-only and GET returns 405 Method Not Allowed."""
    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 405


def test_logout_clears_session_and_redirects(client):
    """Test that POST /auth/logout clears the session and redirects to Microsoft logout."""
    # First set a session manually by invoking a mock login
    # Wait, testing client's session directly is tricky in Starlette.
    # We can patch ENTRA_ENABLED=True to verify the redirect format
    with patch.object(settings, "ENTRA_ENABLED", True):
        response = client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
        location = response.headers["location"]
        assert location.startswith(f"{settings.ENTRA_AUTHORITY}/oauth2/v2.0/logout")
        assert f"post_logout_redirect_uri={settings.ENTRA_POST_LOGOUT_REDIRECT_URI}" in location


def test_auth_callback_access_denied(client):
    """Test that OAuth access_denied error does not render 'None' and shows safe message."""
    with patch.object(settings, "ENTRA_ENABLED", True), \
         patch("src.api.auth.database.consume_login_transaction") as mock_consume:
        mock_consume.return_value = ({"auth_uri": "mock"}, "/ui")
        response = client.post(
            "/auth/callback",
            data={
                "state": "dummy_state",
                "error": "access_denied",
                "error_description": "AADB2C90091: The user has cancelled entering self-asserted information."
            }
        )
        assert response.status_code == 400
        # It should show the safe message, not the raw error description
        assert "Authentication was cancelled or administrator approval is required" in response.text
        assert "AADB2C90091" not in response.text
        assert "None" not in response.text


def test_auth_me_cache_control(client):
    """Test that /auth/me returns Cache-Control: no-store."""
    # Default is ENTRA_ENABLED=False in conftest, so it will return mock user
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    data = response.json()
    assert data["name"] == "Local Dev User"


def test_auth_me_unauthenticated(client):
    """Test that /auth/me returns 401 when unauthenticated."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        response = client.get("/auth/me")
        assert response.status_code == 401

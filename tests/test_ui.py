"""Unit tests for the admin UI template endpoint."""

from unittest.mock import patch
from src.config import settings


def test_admin_ui_unauthenticated(client):
    """Test GET /ui redirects to login when not authenticated and Entra is enabled."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        # With ENTRA_ENABLED=True, get_optional_user requires session
        response = client.get("/ui", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/login?return_to=/ui"


def test_login_page_unauthenticated(client):
    """Test GET /login when not authenticated."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        response = client.get("/login")
        assert response.status_code == 200
        html_text = response.text
        assert "Sign in with Microsoft" in html_text
        assert "Use your work or school account" in html_text
        assert "type=\"password\"" not in html_text
        assert response.headers["Cache-Control"] == "no-store"


def test_login_page_authenticated(client):
    """Test GET /login redirects to /ui if already authenticated."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        # In testing environment with ENTRA_ENABLED=True, we must mock get_optional_user
        async def mock_get_user(request):
            return {"name": "Test User"}
            
        with patch("src.api.ui.get_optional_user", side_effect=mock_get_user):
            response = client.get("/login", follow_redirects=False)
            assert response.status_code == 303
            assert response.headers["location"] == "/ui"


def test_login_page_messages(client):
    """Test GET /login displays appropriate messages based on query parameters."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        # 1. logged_out=1
        response = client.get("/login?logged_out=1")
        assert "You have been signed out successfully." in response.text
        
        # 2. error=access_denied
        response = client.get("/login?error=access_denied")
        assert "Authentication was cancelled or administrator approval is required" in response.text
        
        # 3. error=session_expired
        response = client.get("/login?error=session_expired")
        assert "Your login session expired" in response.text
        
        # 4. Unknown error
        response = client.get("/login?error=unknown_weird_error")
        assert "An error occurred during authentication" in response.text
        assert "unknown_weird_error" not in response.text  # Raw error never echoed


def test_login_page_return_to_preserved(client):
    """Test return_to is correctly propagated to Microsoft sign-in button."""
    with patch.object(settings, "ENTRA_ENABLED", True):
        response = client.get("/login?return_to=/ui/some/path")
        # URL encoding should turn / into %2F
        assert "/auth/login?return_to=%2Fui%2Fsome%2Fpath" in response.text


def test_admin_ui_configured(client):
    """Test GET /ui when HERMES_WEBUI_URL is configured."""
    test_url = "https://hermes.example.com/"
    with patch.object(settings, "HERMES_WEBUI_URL", test_url):
        response = client.get("/ui")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert response.headers["Cache-Control"] == "no-store"
        
        # Verify that the configured URL is correctly injected in JavaScript
        html_text = response.text
        expected_js_line = f'const hermesWebuiUrl = "{test_url}";'
        assert expected_js_line in html_text
        
        # Verify that the placeholder in the template has been replaced
        assert "{hermes_webui_url_json}" not in html_text

        # In testing environment (ENTRA_ENABLED=False), dummy user is returned
        assert "Local Dev User" in html_text
        assert "dev@local" in html_text
        
        # Verify tid/oid not rendered
        assert "00000000-0000-0000-0000-000000000000" not in html_text


def test_admin_ui_user_rendering(client):
    """Test UI rendering of user identity with escaping and fallbacks."""
    # We patch get_optional_user to return specific users to test UI
    test_cases = [
        # 1. Full user
        ({
            "tid": "tenant-123", "oid": "user-123",
            "name": "John Doe", "preferred_username": "john.doe@example.com"
        }, ["JD", "John Doe", "john.doe@example.com"]),
        
        # 2. No name, fallback to preferred_username
        ({
            "tid": "tenant-123", "oid": "user-123",
            "name": "", "preferred_username": "jane.doe@example.com"
        }, ["JA", "jane.doe@example.com"]),
        
        # 3. HTML Escaping
        ({
            "tid": "tenant-123", "oid": "user-123",
            "name": "<script>alert(1)</script>", "preferred_username": 'admin"onclick="evil()'
        }, ["&lt;S", "&lt;script&gt;alert(1)&lt;/script&gt;", "admin&quot;onclick=&quot;evil()"]),
    ]
    
    for mock_user, expected_strings in test_cases:
        async def mock_get_user(request):
            return mock_user
            
        with patch("src.api.ui.get_optional_user", side_effect=mock_get_user):
            response = client.get("/ui")
            assert response.status_code == 200
            html_text = response.text
            
            # Check expected strings are present
            for expected in expected_strings:
                assert expected in html_text
                
            # Ensure tid and oid are NEVER in the UI
            assert mock_user["tid"] not in html_text
            assert mock_user["oid"] not in html_text
            
            # Ensure the truncation class exists
            assert "class=\"user-name\"" in html_text

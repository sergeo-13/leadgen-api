"""Unit tests for the public homepage and info endpoints."""

from unittest.mock import patch, PropertyMock
from src.config import settings


def test_homepage_unauthenticated(client):
    """Test GET / when unauthenticated shows the correct CTA and headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert response.headers.get("Cache-Control") == "private, no-store"
    
    html_text = response.text
    # Branding
    assert "Leadgen Assistant" in html_text
    assert "Turn company knowledge into an AI-powered workspace" in html_text
    assert "How it works" in html_text
    
    # CTA for unauthenticated
    assert "Sign in with Microsoft" in html_text
    assert "/login?return_to=/ui" in html_text
    assert "Open Console" not in html_text
    
    # Animation elements exist and are accessible
    assert 'aria-hidden="true"' in html_text
    assert "Policy" in html_text
    assert "Product Guide" in html_text
    assert "Research" in html_text
    assert "Company Knowledge" in html_text
    assert "Grounded Answer" in html_text
    
    # Ensures reduced motion CSS is present
    assert "@media (prefers-reduced-motion: reduce)" in html_text
    
    # Ensure no internal data is present
    assert "document-table" not in html_text
    assert "Upload Document" not in html_text
    assert "tenant-id" not in html_text


def test_homepage_authenticated(client):
    """Test GET / when authenticated changes the CTA to Open Console."""
    # Mock the session property on Request
    with patch("starlette.requests.Request.session", new_callable=PropertyMock) as mock_session:
        mock_session.return_value = {"user": {"name": "Test User"}}
        
        response = client.get("/")
        assert response.status_code == 200
        html_text = response.text
        
        # CTA for authenticated
        assert "Open Console" in html_text
        assert 'href="/ui"' in html_text
        assert "Sign in with Microsoft" not in html_text
        
        # Ensure no internal data is exposed even when authenticated
        assert "Test User" not in html_text


def test_info_endpoint(client):
    """Test GET /api/v1/info returns public metadata correctly."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == settings.APP_NAME
    assert data["version"] == settings.APP_VERSION
    assert "docs" not in data
    assert "postgres" not in data

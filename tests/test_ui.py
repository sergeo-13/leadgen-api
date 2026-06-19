"""Unit tests for the admin UI template endpoint."""

from unittest.mock import patch
from src.config import settings


def test_admin_ui_configured(client):
    """Test GET /ui when HERMES_WEBUI_URL is configured."""
    test_url = "https://hermes.example.com/"
    with patch.object(settings, "HERMES_WEBUI_URL", test_url):
        response = client.get("/ui")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify that the configured URL is correctly injected in JavaScript
        html_text = response.text
        expected_js_line = f'const hermesWebuiUrl = "{test_url}";'
        assert expected_js_line in html_text
        
        # Verify that the placeholder in the template has been replaced
        assert "{hermes_webui_url_json}" not in html_text


def test_admin_ui_unconfigured(client):
    """Test GET /ui when HERMES_WEBUI_URL is empty."""
    with patch.object(settings, "HERMES_WEBUI_URL", ""):
        response = client.get("/ui")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify that an empty string is injected in JavaScript
        html_text = response.text
        expected_js_line = 'const hermesWebuiUrl = "";'
        assert expected_js_line in html_text
        assert "{hermes_webui_url_json}" not in html_text

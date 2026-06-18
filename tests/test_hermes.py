"""Tests for Hermes API integration spike."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from src.config import settings
from src.services.hermes_client import HermesClient, HermesConfigurationError, HermesAPIError


@pytest.fixture
def mock_async_client():
    """Fixture to mock httpx.AsyncClient context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("src.services.hermes_client.httpx.AsyncClient", return_value=mock_client):
        yield mock_client


# ─── Client Service Unit Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_client_send_message_success(mock_async_client):
    """Test successful message sending and parsing."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_error = False
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello! I am Hermes."
                }
            }
        ]
    }
    mock_async_client.post = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        client = HermesClient()
        result = await client.send_message(
            session_key="test-session",
            message="Hi"
        )
        assert result["response"] == "Hello! I am Hermes."
        assert result["raw"]["choices"][0]["message"]["content"] == "Hello! I am Hermes."


@pytest.mark.asyncio
async def test_client_send_message_missing_key():
    """Test HermesConfigurationError raised when key is empty."""
    with patch.object(settings, "HERMES_API_KEY", ""):
        client = HermesClient()
        with pytest.raises(HermesConfigurationError) as exc:
            await client.send_message(session_key="test-session", message="Hi")
        assert "API key" in str(exc.value)


@pytest.mark.asyncio
async def test_client_send_message_timeout(mock_async_client):
    """Test TimeoutError raised on request timeout."""
    mock_async_client.post.side_effect = httpx.TimeoutException("Timeout")

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        client = HermesClient()
        with pytest.raises(TimeoutError) as exc:
            await client.send_message(session_key="test-session", message="Hi")
        assert "request timed out" in str(exc.value)


@pytest.mark.asyncio
async def test_client_send_message_connection_error(mock_async_client):
    """Test ConnectionError raised when remote connection fails."""
    mock_async_client.post.side_effect = httpx.RequestError("Connection refused")

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        client = HermesClient()
        with pytest.raises(ConnectionError) as exc:
            await client.send_message(session_key="test-session", message="Hi")
        assert "Could not connect" in str(exc.value)


@pytest.mark.asyncio
async def test_client_send_message_non_2xx_status(mock_async_client):
    """Test HermesAPIError raised on non-2xx status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.is_error = True
    mock_response.text = "Internal Server Error details"
    mock_async_client.post = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        client = HermesClient()
        with pytest.raises(HermesAPIError) as exc:
            await client.send_message(session_key="test-session", message="Hi")
        assert exc.value.status_code == 500
        assert "returned status code 500" in str(exc.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed_json", [
    {},  # Empty response
    {"other": []},  # Missing choices
    {"choices": []},  # Empty choices list
    {"choices": [{}]},  # Choice missing message
    {"choices": [{"message": {}}]},  # Message missing content
    {"choices": [{"message": {"content": None}}]},  # Null content
])
async def test_client_send_message_malformed_response(mock_async_client, malformed_json):
    """Test ValueError raised on various malformed JSON structures."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_error = False
    mock_response.json.return_value = malformed_json
    mock_async_client.post = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        client = HermesClient()
        with pytest.raises(ValueError) as exc:
            await client.send_message(session_key="test-session", message="Hi")
        assert "Malformed response" in str(exc.value) or "missing choices[0].message.content" in str(exc.value)


# ─── API Router Integration Tests ────────────────────────────────────────────

def test_api_test_message_success(client, mock_async_client):
    """Test API POST /api/v1/hermes/test-message success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_error = False
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello!"
                }
            }
        ]
    }
    mock_async_client.post = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        payload = {
            "session_key": "leadgen-test-1",
            "message": "Hello. Reply with one short sentence."
        }
        response = client.post("/api/v1/hermes/test-message", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["session_key"] == "leadgen-test-1"
        assert data["model"] == "hermes-agent"
        assert data["response"] == "Hello!"
        assert "raw" in data


def test_api_test_message_validation_error(client):
    """Test API rejects empty parameters with 422."""
    payloads = [
        {"session_key": "", "message": "Hi"},
        {"session_key": "session", "message": ""},
        {"session_key": "   ", "message": "Hi"},
    ]
    for payload in payloads:
        response = client.post("/api/v1/hermes/test-message", json=payload)
        # Empty values should fail validation
        assert response.status_code in (400, 422)


def test_api_test_message_missing_key(client):
    """Test API returns 400 Bad Request when API key is missing."""
    with patch.object(settings, "HERMES_API_KEY", ""):
        payload = {
            "session_key": "leadgen-test-1",
            "message": "Hello"
        }
        response = client.post("/api/v1/hermes/test-message", json=payload)
        assert response.status_code == 400
        assert "key" in response.json()["detail"]


def test_api_test_message_gateway_error(client, mock_async_client):
    """Test API returns 502 Bad Gateway when Hermes returns error status code."""
    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_response.is_error = True
    mock_response.text = "Gateway Timeout"
    mock_async_client.post = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        payload = {
            "session_key": "leadgen-test-1",
            "message": "Hello"
        }
        response = client.post("/api/v1/hermes/test-message", json=payload)
        assert response.status_code == 502
        assert "returned status code" in response.json()["detail"]


def test_api_health_ok(client, mock_async_client):
    """Test API GET /api/v1/hermes/health returns ok when reachable."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_async_client.get = AsyncMock(return_value=mock_response)

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        response = client.get("/api/v1/hermes/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_api_health_unreachable(client, mock_async_client):
    """Test API GET /api/v1/hermes/health returns unreachable when connection fails."""
    mock_async_client.get.side_effect = httpx.RequestError("Connection failed")

    with patch.object(settings, "HERMES_API_KEY", "test-key"):
        response = client.get("/api/v1/hermes/health")
        assert response.status_code == 200
        assert response.json() == {"status": "unreachable"}

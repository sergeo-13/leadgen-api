"""Hermes service client for programmatic LLM interaction."""

import logging
from typing import Any, Dict
import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class HermesConfigurationError(Exception):
    """Raised when Hermes settings (like API key) are missing or invalid."""
    pass


class HermesAPIError(Exception):
    """Raised when the Hermes API returns a non-2xx status code."""
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class HermesClient:
    """Async client wrapper for Hermes OpenAI-compatible API."""

    def __init__(self) -> None:
        self.base_url = settings.HERMES_API_BASE_URL.rstrip("/")
        self.api_key = settings.HERMES_API_KEY
        self.default_model = settings.HERMES_DEFAULT_MODEL
        self.timeout = float(settings.HERMES_TIMEOUT_SECONDS)

    def _get_headers(self, session_key: str = "") -> Dict[str, str]:
        """Generate headers for Hermes API requests."""
        if not self.api_key:
            raise HermesConfigurationError("Hermes API key (HERMES_API_KEY) is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if session_key:
            headers["X-Hermes-Session-Key"] = session_key
        return headers

    async def send_message(self, session_key: str, message: str) -> Dict[str, Any]:
        """
        Send a non-streaming user message to Hermes chat completions endpoint.

        Args:
            session_key: Reusable session identifier.
            message: The user's input prompt.

        Returns:
            Dict containing the assistant response and raw response body.
        """
        # Validate input parameters
        if not session_key or not session_key.strip():
            raise ValueError("session_key is required and cannot be empty.")
        if not message or not message.strip():
            raise ValueError("message is required and cannot be empty.")

        url = f"{self.base_url}/v1/chat/completions"
        headers = self._get_headers(session_key)
        payload = {
            "model": self.default_model,
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                # Check for HTTP errors (non-2xx)
                if response.is_error:
                    body_snippet = response.text[:200]
                    logger.error(
                        f"Hermes API returned non-2xx status code {response.status_code}. Response snippet: {body_snippet}"
                    )
                    raise HermesAPIError(
                        status_code=response.status_code,
                        message=f"Hermes API returned status code {response.status_code}. Response: {body_snippet}"
                    )

                # Parse JSON response
                try:
                    data = response.json()
                except ValueError as e:
                    logger.error("Failed to parse JSON response from Hermes API.")
                    raise ValueError("Malformed response from Hermes API: response is not valid JSON.") from e

                # Validate response structure
                if not isinstance(data, dict) or "choices" not in data:
                    raise ValueError("Malformed response from Hermes API: missing 'choices' array.")
                
                choices = data["choices"]
                if not isinstance(choices, list) or len(choices) == 0:
                    raise ValueError("Malformed response from Hermes API: 'choices' array is empty.")
                
                choice = choices[0]
                if not isinstance(choice, dict) or "message" not in choice:
                    raise ValueError("Malformed response from Hermes API: choice is missing 'message'.")
                
                msg = choice["message"]
                if not isinstance(msg, dict) or "content" not in msg:
                    raise ValueError("Malformed response from Hermes API: message is missing 'content'.")
                
                content = msg["content"]
                if content is None:
                    raise ValueError("Hermes API response is missing choices[0].message.content.")

                return {
                    "response": content,
                    "raw": data
                }

        except httpx.TimeoutException as e:
            logger.error("Hermes API request timed out.")
            raise TimeoutError("Hermes API request timed out.") from e
        except httpx.RequestError as e:
            logger.error(f"Could not connect to Hermes API: {e}")
            raise ConnectionError("Could not connect to Hermes API.") from e

    async def check_health(self) -> bool:
        """
        Verify Hermes service status by listing available models.

        Returns:
            True if healthy and reachable, False otherwise.
        """
        url = f"{self.base_url}/v1/models"
        try:
            # Generate headers (or verify configuration)
            headers = self._get_headers()
        except HermesConfigurationError:
            # We treat missing config as unhealthy (or unreachable) in health context
            logger.warning("Hermes health check failed: HERMES_API_KEY is not configured.")
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return True
                logger.warning(f"Hermes health check returned status code: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Hermes health check endpoint unreachable: {e}")
            return False

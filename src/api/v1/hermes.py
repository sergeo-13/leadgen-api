"""API Router for Hermes programmatic testing."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.services.hermes_client import (
    HermesAPIError,
    HermesClient,
    HermesConfigurationError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hermes")


class HermesMessageRequest(BaseModel):
    """Schema for test message requests to Hermes API."""
    session_key: str = Field(
        ...,
        min_length=1,
        examples=["leadgen-test-1"],
        description="Non-empty session key for identifying user chat context."
    )
    message: str = Field(
        ...,
        min_length=1,
        examples=["Hello. Reply with one short sentence."],
        description="The prompt message to send to Hermes."
    )


class HermesMessageResponse(BaseModel):
    """Schema for responses returned to clients."""
    session_key: str
    model: str
    response: str
    raw: Dict[str, Any]


class HermesHealthResponse(BaseModel):
    """Schema for Hermes integration health status."""
    status: str


@router.post(
    "/test-message",
    response_model=HermesMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a test message to Hermes",
    description="Programmatically logs and forwards a message to the internal Hermes gateway."
)
async def test_message(payload: HermesMessageRequest) -> Dict[str, Any]:
    """Test message endpoint for sending prompts to Hermes."""
    client = HermesClient()
    
    try:
        result = await client.send_message(
            session_key=payload.session_key.strip(),
            message=payload.message.strip()
        )
        return {
            "session_key": payload.session_key,
            "model": client.default_model,
            "response": result["response"],
            "raw": result["raw"]
        }
    except HermesConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HermesAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e)
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error in Hermes test-message route.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HermesHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Hermes gateway reachability",
    description="Verifies the connection to the internal Hermes gateway by retrieving available models."
)
async def check_hermes_health() -> Dict[str, str]:
    """Check Hermes integration health status."""
    client = HermesClient()
    is_healthy = await client.check_health()
    if is_healthy:
        return {"status": "ok"}
    return {"status": "unreachable"}

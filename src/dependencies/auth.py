"""Authentication dependencies."""

from typing import Dict, Any, Optional

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

from src.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get the current user from the session if it exists.
    If Entra is disabled, return a mock user.
    """
    if not settings.ENTRA_ENABLED:
        return {
            "tid": "00000000-0000-0000-0000-000000000000",
            "oid": "00000000-0000-0000-0000-000000000000",
            "name": "Local Dev User",
            "preferred_username": "dev@local",
        }

    user = request.session.get("user")
    return user


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Require an authenticated user.
    Raises 401 Unauthorized if no user is found in the session.
    """
    user = await get_optional_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def verify_ingestion_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> None:
    """
    Verify the internal ingestion API key.
    """
    if settings.ENVIRONMENT == "testing":
        return

    if not settings.INGESTION_API_KEY:
        # If no key is configured, reject all to be safe.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ingestion API key not configured.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not credentials or credentials.scheme != "Bearer" or credentials.credentials != settings.INGESTION_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ingestion API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

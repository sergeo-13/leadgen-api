"""CSRF protection dependencies."""

import logging
from urllib.parse import urlparse

from fastapi import Request, HTTPException, status

from src.config import settings

logger = logging.getLogger(__name__)


async def verify_csrf(request: Request):
    """
    Same-origin CSRF validation.
    Applies only to unsafe browser methods (POST, PUT, PATCH, DELETE).
    Safe missing-Origin policy falls back to Referer.
    """
    if not settings.ENTRA_ENABLED:
        return
        
    if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
        return

    # POST /auth/callback is explicitly exempt (cross-site POST from Microsoft)
    if request.url.path == "/auth/callback" and request.method == "POST":
        return

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    source_origin = origin
    if not source_origin and referer:
        try:
            parsed = urlparse(referer)
            source_origin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass

    if not source_origin:
        logger.warning("CSRF validation failed: Missing Origin and Referer headers.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing Origin and Referer headers for CSRF validation."
        )

    allowed_origins = [
        o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()
    ]
    
    if source_origin not in allowed_origins:
        logger.warning(f"CSRF validation failed: Source origin '{source_origin}' not in allowed origins.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin request rejected by CSRF policy."
        )

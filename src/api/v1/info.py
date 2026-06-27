"""Public API information endpoint."""

from fastapi import APIRouter
from src.config import settings

router = APIRouter()


@router.get("/info")
async def get_info():
    """Returns basic API metadata without sensitive data or docs links."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

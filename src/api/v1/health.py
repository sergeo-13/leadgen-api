"""Health check endpoints."""

import asyncio
import logging
from typing import Dict

from fastapi import APIRouter

from src.config import settings
from src.services.database import check_postgres
from src.services.minio_service import check_minio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dictionary with health status of all services.
    """
    postgres_ok = False
    minio_ok = False

    # Check PostgreSQL
    try:
        postgres_ok = await check_postgres()
        logger.info("PostgreSQL health check: OK")
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        postgres_ok = False

    # Check MinIO
    try:
        minio_ok = await asyncio.to_thread(check_minio)
        logger.info("MinIO health check: OK")
    except Exception as e:
        logger.error(f"MinIO health check failed: {e}")
        minio_ok = False

    status = "ok" if postgres_ok and minio_ok else "degraded"

    return {
        "status": status,
        "postgres": "ok" if postgres_ok else "error",
        "minio": "ok" if minio_ok else "error",
        "version": settings.APP_VERSION,
    }

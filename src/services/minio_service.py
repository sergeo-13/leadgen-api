"""MinIO storage service."""

import logging

from minio import Minio

from src.config import settings
from src.core.exceptions import MinIOConnectionError

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    """
    Get MinIO client instance.

    Returns:
        Minio client.
    """
    endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def check_minio() -> bool:
    """
    Check MinIO connection and bucket existence.

    Returns:
        True if MinIO is accessible and bucket exists.

    Raises:
        MinIOConnectionError: If connection fails.
    """
    try:
        client = get_minio_client()
        exists = client.bucket_exists(settings.MINIO_BUCKET)
        if not exists:
            logger.warning(f"MinIO bucket '{settings.MINIO_BUCKET}' does not exist")
            return False
        logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' exists")
        return True
    except Exception as e:
        logger.error(f"MinIO connection error: {e}")
        raise MinIOConnectionError(f"Failed to connect to MinIO: {e}")


def check_object_exists(object_key: str) -> bool:
    """
    Check if object exists in the configured MinIO bucket.

    Args:
        object_key: MinIO object key.

    Returns:
        True if the object exists, False otherwise.
    """
    try:
        client = get_minio_client()
        client.stat_object(settings.MINIO_BUCKET, object_key)
        return True
    except Exception as e:
        logger.warning(f"Object '{object_key}' check failed in bucket '{settings.MINIO_BUCKET}': {e}")
        return False


def download_object(bucket_name: str, object_key: str) -> bytes:
    """
    Download an object from the specified MinIO bucket.

    Args:
        bucket_name: Name of the bucket.
        object_key: Key of the object.

    Returns:
        bytes: Object content.

    Raises:
        Exception: If download fails.
    """
    try:
        client = get_minio_client()
        response = client.get_object(bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as e:
        logger.error(f"Failed to download object '{object_key}' from bucket '{bucket_name}': {e}")
        raise

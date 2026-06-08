"""Database connection and operations."""

import logging

import asyncpg

from src.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.models.schemas import DocumentMetadata

logger = logging.getLogger(__name__)


async def check_postgres() -> bool:
    """
    Check PostgreSQL connection.

    Returns:
        True if connection is successful, False otherwise.

    Raises:
        DatabaseConnectionError: If connection fails.
    """
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            timeout=5,
        )
        try:
            result = await conn.fetchval("SELECT 1")
            return result == 1
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"PostgreSQL connection error: {e}")
        raise DatabaseConnectionError(f"Failed to connect to PostgreSQL: {e}")


async def create_ingestion_job(
    title: str,
    object_key: str,
    metadata: DocumentMetadata
) -> tuple[str, str, str]:
    """
    Insert a document and corresponding ingestion job inside a transaction.

    Args:
        title: Document title.
        object_key: MinIO object key.
        metadata: DocumentMetadata Pydantic object.

    Returns:
        tuple: (document_id, job_id, status)
    """
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        timeout=5,
    )
    try:
        async with conn.transaction():
            # Insert document
            doc_id = await conn.fetchval(
                """
                INSERT INTO documents (
                    title, type, client_name, industry, geography,
                    use_case, capabilities, authors, source_bucket,
                    source_object_key, status, confidentiality_level,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                RETURNING id
                """,
                title,
                metadata.type,
                metadata.client_name,
                metadata.industry,
                metadata.geography,
                metadata.use_case,
                metadata.capabilities,
                metadata.authors,
                settings.MINIO_BUCKET,
                object_key,
                "active",
                "internal"
            )

            # Insert ingestion job
            job_id = await conn.fetchval(
                """
                INSERT INTO ingestion_jobs (
                    document_id, source_bucket, source_object_key,
                    status, error, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                RETURNING id
                """,
                doc_id,
                settings.MINIO_BUCKET,
                object_key,
                "pending",
                None
            )

            return str(doc_id), str(job_id), "pending"
    finally:
        await conn.close()

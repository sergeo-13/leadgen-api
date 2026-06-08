"""Database connection and operations."""

import logging
from typing import Optional, Tuple, List

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
) -> Tuple[str, str, str]:
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


async def get_and_claim_next_pending_job() -> Optional[dict]:
    """
    Fetch and atomically claim the next pending ingestion job.
    Uses SELECT FOR UPDATE SKIP LOCKED inside a transaction.

    Returns:
        dict | None: The claimed job details or None if no pending jobs.
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
            job = await conn.fetchrow(
                """
                SELECT id, document_id, source_bucket, source_object_key, status
                FROM ingestion_jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            if not job:
                return None

            # Claim job by updating status to processing
            await conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'processing', updated_at = NOW()
                WHERE id = $1
                """,
                job["id"]
            )

            return {
                "job_id": str(job["id"]),
                "document_id": str(job["document_id"]),
                "source_bucket": job["source_bucket"],
                "source_object_key": job["source_object_key"],
                "status": "processing"
            }
    finally:
        await conn.close()


async def update_job_status(job_id: str, status: str, error: str = None) -> None:
    """
    Update the status and optional error message of an ingestion job.

    Args:
        job_id: The job ID.
        status: The new status.
        error: Optional error message.
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
        await conn.execute(
            """
            UPDATE ingestion_jobs
            SET status = $1, error = $2, updated_at = NOW()
            WHERE id = $3::uuid
            """,
            status,
            error,
            job_id
        )
    finally:
        await conn.close()


async def insert_document_chunks(document_id: str, chunks: List[Tuple[int, str, List[float]]]) -> None:
    """
    Delete existing chunks for a document, and insert new chunks.
    All done within a transaction.

    Args:
        document_id: The document ID.
        chunks: List of tuples (chunk_index, content, embedding_list).
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
            # 1. Delete existing chunks
            await conn.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = $1::uuid
                """,
                document_id
            )

            # 2. Insert new chunks
            for index, content, embedding in chunks:
                vector_str = f"[{','.join(map(str, embedding))}]"
                await conn.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_index, content, embedding
                    ) VALUES ($1::uuid, $2, $3, $4::vector)
                    """,
                    document_id,
                    index,
                    content,
                    vector_str
                )
    finally:
        await conn.close()

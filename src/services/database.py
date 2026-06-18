import json
import logging
from typing import Optional, Tuple, List, Any

import asyncpg

from src.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.models.schemas import DocumentMetadata, DocumentSearchFilters

logger = logging.getLogger(__name__)


def _normalize_jsonb(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSONB metadata string, returning empty dict")
            return {}
    return {}


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
                    use_case, tags, authors, source_bucket,
                    source_object_key, status, confidentiality_level,
                    description, source_type, source_url, file_name,
                    mime_type, file_size, metadata,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19::jsonb, NOW(), NOW())
                RETURNING id
                """,
                title,
                metadata.type,
                metadata.client_name,
                metadata.industry,
                metadata.geography,
                metadata.use_case,
                metadata.tags,
                metadata.authors,
                settings.MINIO_BUCKET,
                object_key,
                "uploaded",  # Initial status for new documents is uploaded
                "internal",
                metadata.description,
                metadata.source_type,
                metadata.source_url,
                metadata.file_name,
                metadata.mime_type,
                metadata.file_size,
                json.dumps(metadata.metadata) if metadata.metadata is not None else '{}'
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

            logger.info(f"Ingestion job created: job_id={job_id}, document_id={doc_id}")
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


async def get_job_by_id(job_id: str) -> Optional[dict]:
    """
    Fetch a single ingestion job row by its UUID.

    Args:
        job_id: UUID of the ingestion job.

    Returns:
        dict | None: Job details, or None if not found.
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
        row = await conn.fetchrow(
            """
            SELECT id, document_id, source_bucket, source_object_key, status
            FROM ingestion_jobs
            WHERE id = $1::uuid
            """,
            job_id,
        )
        if not row:
            return None
        return {
            "job_id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "source_bucket": row["source_bucket"],
            "source_object_key": row["source_object_key"],
            "status": row["status"],
        }
    finally:
        await conn.close()


async def claim_job(job_id: str) -> None:
    """
    Set an ingestion job's status to 'processing'.

    Args:
        job_id: UUID of the ingestion job.
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
            SET status = 'processing', updated_at = NOW()
            WHERE id = $1::uuid
            """,
            job_id,
        )
        logger.info(f"Job {job_id} status changed to processing")
    finally:
        await conn.close()


async def update_job_status(job_id: str, status: str, error: Optional[str] = None) -> None:
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
        logger.info(f"Job {job_id} status changed to {status}")
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


async def search_document_chunks(
    query_embedding: List[float],
    limit: int,
    filters: Optional[DocumentSearchFilters] = None,
    query_text: Optional[str] = None
) -> List[dict]:
    """
    Search document chunks by vector similarity using pgvector cosine distance,
    optionally filtering by document metadata.

    Args:
        query_embedding: OpenAI embedding float list.
        limit: Max number of chunks to return.
        filters: DocumentSearchFilters object.
        query_text: Optional search query text for debugging.

    Returns:
        List[dict]: Matched document chunks with similarity score and doc metadata.
    """
    logger.info("Starting search_document_chunks execution.")
    logger.debug(f"Search Query Text: {query_text}")
    logger.debug(f"Limit: {limit}")
    logger.debug(f"Filters: {filters}")
    logger.debug(f"Query Embedding Dimensions: {len(query_embedding)}")

    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        timeout=5,
    )

    vector_str = f"[{','.join(map(str, query_embedding))}]"

    query = """
        SELECT
            d.id AS document_id,
            d.title,
            d.type,
            d.client_name,
            d.industry,
            d.geography,
            d.use_case,
            d.tags,
            d.authors,
            d.source_bucket,
            d.source_object_key,
            d.description,
            d.source_type,
            d.source_url,
            d.file_name,
            d.mime_type,
            d.file_size,
            d.metadata,
            c.id AS chunk_id,
            c.chunk_index,
            c.content,
            1 - (c.embedding <=> $1::vector) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
    """

    params: List[Any] = [vector_str]
    where_clauses = ["c.embedding IS NOT NULL", "d.status = 'processed'"]
    param_idx = 2

    if filters:
        if filters.type and filters.type.strip():
            where_clauses.append(f"d.type = ${param_idx}")
            params.append(filters.type)
            param_idx += 1
        if filters.client_name and filters.client_name.strip():
            where_clauses.append(f"d.client_name = ${param_idx}")
            params.append(filters.client_name)
            param_idx += 1
        if filters.industry and filters.industry.strip():
            where_clauses.append(f"d.industry = ${param_idx}")
            params.append(filters.industry)
            param_idx += 1
        if filters.geography and filters.geography.strip():
            where_clauses.append(f"d.geography = ${param_idx}")
            params.append(filters.geography)
            param_idx += 1
        if filters.use_case and filters.use_case.strip():
            where_clauses.append(f"d.use_case = ${param_idx}")
            params.append(filters.use_case)
            param_idx += 1
        if filters.tags:
            non_empty_tags = [t.strip() for t in filters.tags if t and t.strip()]
            if non_empty_tags:
                where_clauses.append(f"d.tags && ${param_idx}::text[]")
                params.append(non_empty_tags)
                param_idx += 1

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += f" ORDER BY c.embedding <=> $1::vector ASC LIMIT ${param_idx}"
    params.append(limit)

    logger.debug(f"Final SQL Query: {query}")
    logger.debug(f"Query parameters: {params}")

    try:
        rows = await conn.fetch(query, *params)
        logger.info(f"Database returned {len(rows)} matching chunks.")
        results = []
        for row in rows:
            res = dict(row)
            res["document_id"] = str(res["document_id"])
            res["chunk_id"] = str(res["chunk_id"])
            res["tags"] = list(res["tags"]) if res.get("tags") is not None else []
            res["authors"] = list(res["authors"]) if res.get("authors") is not None else []
            res["metadata"] = _normalize_jsonb(res.get("metadata"))
            results.append(res)
        return results
    finally:
        await conn.close()


async def list_documents() -> List[dict]:
    """
    List all documents from the database.
    Includes count of chunks associated with each document.
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
        rows = await conn.fetch(
            """
            SELECT d.id, d.title, d.type, d.client_name, d.industry, d.geography, d.use_case,
                   d.tags, d.authors, d.source_bucket, d.source_object_key, d.status,
                   d.confidentiality_level, d.description, d.source_type, d.source_url,
                   d.file_name, d.mime_type, d.file_size, d.metadata, d.created_at, d.updated_at,
                   (SELECT COUNT(*) FROM document_chunks WHERE document_id = d.id) AS chunks_count
            FROM documents d
            ORDER BY d.created_at DESC
            """
        )
        results = []
        for row in rows:
            res = dict(row)
            res["id"] = str(res["id"])
            res["tags"] = list(res["tags"]) if res.get("tags") is not None else []
            res["authors"] = list(res["authors"]) if res.get("authors") is not None else []
            res["metadata"] = _normalize_jsonb(res.get("metadata"))
            results.append(res)
        return results
    finally:
        await conn.close()


async def get_document_by_id(document_id: str) -> Optional[dict]:
    """
    Get detailed view of a specific document including chunks_count.
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
        row = await conn.fetchrow(
            """
            SELECT d.id, d.title, d.type, d.client_name, d.industry, d.geography, d.use_case,
                   d.tags, d.authors, d.source_bucket, d.source_object_key, d.status,
                   d.confidentiality_level, d.description, d.source_type, d.source_url,
                   d.file_name, d.mime_type, d.file_size, d.metadata, d.created_at, d.updated_at,
                   (SELECT COUNT(*) FROM document_chunks WHERE document_id = d.id) AS chunks_count
            FROM documents d
            WHERE d.id = $1::uuid
            """,
            document_id
        )
        if not row:
            return None
        res = dict(row)
        res["id"] = str(res["id"])
        res["tags"] = list(res["tags"]) if res.get("tags") is not None else []
        res["authors"] = list(res["authors"]) if res.get("authors") is not None else []
        res["metadata"] = _normalize_jsonb(res.get("metadata"))
        return res
    finally:
        await conn.close()


async def update_document_metadata(document_id: str, title: str, metadata: DocumentMetadata) -> bool:
    """
    Update document metadata fields.
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
        result = await conn.execute(
            """
            UPDATE documents
            SET title = $1, type = $2, client_name = $3, industry = $4, geography = $5,
                use_case = $6, tags = $7, authors = $8, description = $9, source_type = $10,
                source_url = $11, metadata = $12::jsonb, updated_at = NOW()
            WHERE id = $13::uuid
            """,
            title,
            metadata.type,
            metadata.client_name,
            metadata.industry,
            metadata.geography,
            metadata.use_case,
            metadata.tags,
            metadata.authors,
            metadata.description,
            metadata.source_type,
            metadata.source_url,
            json.dumps(metadata.metadata) if metadata.metadata is not None else '{}',
            document_id
        )
        success = result == "UPDATE 1"
        if success:
            logger.info(f"Document {document_id} metadata updated successfully.")
        return success
    finally:
        await conn.close()


async def update_document_source(document_id: str, source_object_key: str, file_name: str, mime_type: str, file_size: int) -> bool:
    """
    Update document source file reference fields (e.g. during file replacement).
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
        result = await conn.execute(
            """
            UPDATE documents
            SET source_object_key = $1, file_name = $2, mime_type = $3, file_size = $4, updated_at = NOW()
            WHERE id = $5::uuid
            """,
            source_object_key,
            file_name,
            mime_type,
            file_size,
            document_id
        )
        success = result == "UPDATE 1"
        if success:
            logger.info(f"Document {document_id} source file reference updated successfully.")
        return success
    finally:
        await conn.close()


async def list_ingestion_jobs(
    status: Optional[str] = None,
    document_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """
    List ingestion jobs with optional filters and pagination.
    """
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        timeout=5,
    )
    query = """
        SELECT id, document_id, source_bucket, source_object_key, status, error, created_at, updated_at
        FROM ingestion_jobs
    """
    where_clauses = []
    params: List[Any] = []
    param_idx = 1

    if status:
        where_clauses.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1
    if document_id:
        where_clauses.append(f"document_id = ${param_idx}::uuid")
        params.append(document_id)
        param_idx += 1

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    try:
        rows = await conn.fetch(query, *params)
        results = []
        for row in rows:
            res = dict(row)
            res["job_id"] = str(res["id"])
            res["document_id"] = str(res["document_id"])
            results.append(res)
        return results
    finally:
        await conn.close()


async def get_jobs_by_document_id(document_id: str) -> List[dict]:
    """
    Get all ingestion jobs for a specific document.
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
        rows = await conn.fetch(
            """
            SELECT id, document_id, source_bucket, source_object_key, status, error, created_at, updated_at
            FROM ingestion_jobs
            WHERE document_id = $1::uuid
            ORDER BY created_at DESC
            """,
            document_id
        )
        results = []
        for row in rows:
            res = dict(row)
            res["job_id"] = str(res["id"])
            res["document_id"] = str(res["document_id"])
            results.append(res)
        return results
    finally:
        await conn.close()


async def get_job_details_by_id(job_id: str) -> Optional[dict]:
    """
    Get specific ingestion job details.
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
        row = await conn.fetchrow(
            """
            SELECT id, document_id, source_bucket, source_object_key, status, error, created_at, updated_at
            FROM ingestion_jobs
            WHERE id = $1::uuid
            """,
            job_id
        )
        if not row:
            return None
        res = dict(row)
        res["job_id"] = str(res["id"])
        res["document_id"] = str(res["document_id"])
        return res
    finally:
        await conn.close()


async def archive_document(document_id: str) -> bool:
    """
    Soft-delete a document by setting its status to 'archived'.
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
        result = await conn.execute(
            """
            UPDATE documents
            SET status = 'archived', updated_at = NOW()
            WHERE id = $1::uuid
            """,
            document_id
        )
        success = result == "UPDATE 1"
        if success:
            logger.info(f"Document {document_id} status changed to archived")
        return success
    finally:
        await conn.close()


async def restore_document(document_id: str) -> bool:
    """
    Restore a document from 'archived' status.
    If it has chunks with embeddings, set to 'processed'; otherwise set to 'uploaded'.
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
        # Check for chunks with non-null embeddings
        chunks_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM document_chunks
            WHERE document_id = $1::uuid AND embedding IS NOT NULL
            """,
            document_id
        )
        new_status = "processed" if chunks_count > 0 else "uploaded"
        result = await conn.execute(
            """
            UPDATE documents
            SET status = $1, updated_at = NOW()
            WHERE id = $2::uuid
            """,
            new_status,
            document_id
        )
        success = result == "UPDATE 1"
        if success:
            logger.info(f"Document {document_id} status changed to {new_status}")
        return success
    finally:
        await conn.close()


async def update_document_status(document_id: str, status: str) -> bool:
    """
    Update a document's status.
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
        result = await conn.execute(
            """
            UPDATE documents
            SET status = $1, updated_at = NOW()
            WHERE id = $2::uuid
            """,
            status,
            document_id
        )
        success = result == "UPDATE 1"
        if success:
            logger.info(f"Document {document_id} status changed to {status}")
        return success
    finally:
        await conn.close()


async def retry_ingestion_job(job_id: str) -> bool:
    """
    Retry a failed ingestion job. Resets status to pending, error to NULL,
    and resets related document status to uploaded.
    Only allowed for failed jobs.
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
                "SELECT status, document_id FROM ingestion_jobs WHERE id = $1::uuid",
                job_id
            )
            if not job:
                raise ValueError(f"Ingestion job '{job_id}' not found.")
            if job["status"] != "failed":
                raise ValueError(f"Only failed jobs can be retried. Current status is '{job['status']}'.")

            # Update job status
            await conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'pending', error = NULL, updated_at = NOW()
                WHERE id = $1::uuid
                """,
                job_id
            )
            logger.info(f"Job {job_id} status changed to pending")

            # Update related document status to uploaded
            doc_id = str(job["document_id"])
            await conn.execute(
                """
                UPDATE documents
                SET status = 'uploaded', updated_at = NOW()
                WHERE id = $1::uuid
                """,
                doc_id
            )
            logger.info(f"Document {doc_id} status changed to uploaded")

            return True
    finally:
        await conn.close()

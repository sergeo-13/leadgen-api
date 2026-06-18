"""Ingestion processing service."""

import logging

from src.services.chunker import split_text
from src.services.database import (
    claim_job,
    get_and_claim_next_pending_job,
    get_job_by_id,
    insert_document_chunks,
    update_job_status,
    update_document_status,
)
from src.services.document_parser import extract_text
from src.services.embedding_service import generate_embeddings
from src.services.minio_service import download_object

logger = logging.getLogger(__name__)


async def process_job(job_id: str) -> dict:
    """
    Core ingestion pipeline for a specific job.

    Loads the ingestion job by ID, downloads the source file from MinIO,
    parses it, splits into chunks, generates embeddings, and stores them.

    Args:
        job_id: UUID of the ingestion job to process.

    Returns:
        dict: Result containing status, job_id, document_id, and chunks_created.

    Raises:
        ValueError: If the job is not found or the file type is unsupported.
        Exception: On any pipeline failure — the job is marked 'failed' before re-raising.
    """
    # 1. Load job from DB
    job = await get_job_by_id(job_id)
    if not job:
        raise ValueError(f"Ingestion job '{job_id}' not found.")

    document_id = job["document_id"]

    # 2. Return early if already completed (idempotent)
    if job["status"] == "completed":
        return {
            "status": "already_completed",
            "job_id": job_id,
            "document_id": document_id,
        }

    # 3. Claim job (mark as processing)
    await claim_job(job_id)
    await update_document_status(document_id, "processing")

    source_bucket = job["source_bucket"]
    source_object_key = job["source_object_key"]

    logger.info(f"Processing job {job_id} for document {document_id}")

    try:
        # 4. Check supported file formats
        import os
        supported_extensions = {".pdf", ".txt", ".md", ".markdown", ".csv", ".docx", ".xlsx"}
        _, ext = os.path.splitext(source_object_key.lower())
        if ext not in supported_extensions:
            raise ValueError("Unsupported file type. Supported formats: PDF, TXT, Markdown, CSV, DOCX, XLSX.")

        # 5. Download file from MinIO
        logger.info(f"Downloading '{source_object_key}' from bucket '{source_bucket}'")
        file_bytes = download_object(source_bucket, source_object_key)

        # 6. Extract text
        logger.info(f"Extracting text from file {source_object_key}")
        text = extract_text(file_bytes, source_object_key)
        if not text or not text.strip():
            raise ValueError(
                "No text could be extracted from the file — "
                "the file may be empty or invalid."
            )

        # 7. Split into chunks
        logger.info("Splitting text into chunks")
        chunks = split_text(text)
        if not chunks:
            raise ValueError("Text was extracted but no chunks were generated.")

        # 8. Generate embeddings (batched OpenAI calls)
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = generate_embeddings(chunks)

        # 9. Build (index, content, embedding) tuples
        chunks_payload = [
            (idx, content, embedding)
            for idx, (content, embedding) in enumerate(zip(chunks, embeddings))
        ]

        # 10. Replace existing chunks and insert new ones
        logger.info("Inserting chunks into database")
        await insert_document_chunks(document_id, chunks_payload)

        # 11. Mark job completed
        await update_job_status(job_id, "completed")
        await update_document_status(document_id, "processed")
        logger.info(f"Job {job_id} completed — {len(chunks)} chunks created")

        return {
            "status": "completed",
            "job_id": job_id,
            "document_id": document_id,
            "chunks_created": len(chunks),
        }

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        try:
            await update_job_status(job_id, "failed", str(e))
            await update_document_status(document_id, "failed")
        except Exception as db_err:
            logger.error(f"Could not persist failed status for job {job_id}: {db_err}")
        raise


async def process_next_job() -> dict:
    """
    Fetch, atomically claim, and process the next pending ingestion job.

    Returns:
        dict: Processing result, or {"status": "no_pending_jobs"} when queue is empty.

    Raises:
        Exception: Propagated from process_job on pipeline failure.
    """
    job = await get_and_claim_next_pending_job()
    if not job:
        return {"status": "no_pending_jobs"}

    # Delegate to the core processing function
    return await process_job(job["job_id"])

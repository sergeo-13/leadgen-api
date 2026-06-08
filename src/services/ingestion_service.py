"""Ingestion processing service."""

import logging

from src.services.chunker import split_text
from src.services.database import (
    get_and_claim_next_pending_job,
    insert_document_chunks,
    update_job_status,
)
from src.services.document_parser import extract_text_from_pdf
from src.services.embedding_service import generate_embeddings
from src.services.minio_service import download_object

logger = logging.getLogger(__name__)


async def process_next_job() -> dict:
    """
    Fetch, claim, and process the next pending ingestion job.

    Returns:
        dict: The result status dictionary.

    Raises:
        Exception: If processing fails.
    """
    # 1. Fetch and claim next pending job
    job = await get_and_claim_next_pending_job()
    if not job:
        return {"status": "no_pending_jobs"}

    job_id = job["job_id"]
    document_id = job["document_id"]
    source_bucket = job["source_bucket"]
    source_object_key = job["source_object_key"]

    logger.info(f"Processing job {job_id} for document {document_id}")

    try:
        # 2. File type check (Only PDF)
        if not source_object_key.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are supported in this MVP version.")

        # 3. Download the file from MinIO
        logger.info(f"Downloading {source_object_key} from {source_bucket}")
        pdf_bytes = download_object(source_bucket, source_object_key)

        # 4. Extract text from PDF
        logger.info("Extracting text from PDF")
        text = extract_text_from_pdf(pdf_bytes)
        if not text or not text.strip():
            raise ValueError("No text extracted from PDF")

        # 5. Split text into chunks
        logger.info("Splitting text into chunks")
        chunks = split_text(text)
        if not chunks:
            raise ValueError("No chunks generated from the document")

        # 6. Generate embeddings for every chunk (using OpenAI batching)
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = generate_embeddings(chunks)

        # 7. Map to tuples: (index, content, embedding)
        chunks_payload = [
            (idx, chunk_content, embedding)
            for idx, (chunk_content, embedding) in enumerate(zip(chunks, embeddings))
        ]

        # 8. Save chunks in database (deletes old ones first)
        logger.info("Inserting chunks into database")
        await insert_document_chunks(document_id, chunks_payload)

        # 9. Mark job as completed
        await update_job_status(job_id, "completed")
        logger.info(f"Job {job_id} completed successfully")

        return {
            "status": "completed",
            "job_id": job_id,
            "document_id": document_id,
            "chunks_created": len(chunks),
        }

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        # Make sure status is updated to failed
        try:
            await update_job_status(job_id, "failed", str(e))
        except Exception as db_err:
            logger.error(f"Failed to set job {job_id} status to failed: {db_err}")
        raise

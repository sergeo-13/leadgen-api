"""Document management endpoints."""

import logging
import os
import re
import uuid as uuid_lib

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from src.config import settings
from src.models.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentMetadata,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from src.services.database import create_ingestion_job, search_document_chunks
from src.services.embedding_service import generate_embeddings
from src.services.ingestion_service import process_job
from src.services.minio_service import check_object_exists, upload_object

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── helpers ─────────────────────────────────────────────────────────────────

def _sanitize_object_key(filename: str) -> str:
    """
    Build a safe MinIO object key from an uploaded filename.

    - Strips any directory path components (prevents path traversal).
    - Lowercases the name.
    - Replaces whitespace and non-safe characters with underscores.
    - Collapses consecutive underscores.
    - Preserves the .pdf extension.
    """
    basename = os.path.basename(filename)          # strip path components
    name, ext = os.path.splitext(basename)
    name = name.lower()
    name = re.sub(r"[^\w\-]", "_", name)           # keep word chars and hyphens
    name = re.sub(r"_+", "_", name).strip("_")     # collapse/strip underscores
    ext = ext.lower()
    name = name or "upload"
    return f"{name}{ext}"


def _unique_object_key(base_key: str) -> str:
    """Prefix a base object key with a short UUID4 segment for uniqueness."""
    prefix = str(uuid_lib.uuid4())[:8]
    return f"{prefix}_{base_key}"


# ─── existing endpoint: JSON ingest ──────────────────────────────────────────

@router.post(
    "/documents/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new document (file must already be in MinIO)",
)
async def ingest_document(payload: DocumentIngestRequest):
    """
    Ingest a new document.

    1. Verify object exists in MinIO bucket.
    2. Insert document row.
    3. Insert ingestion job row.
    4. Return document_id, job_id, and status.
    """
    # 1. Verify object exists in MinIO bucket
    exists = check_object_exists(payload.object_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Object '{payload.object_key}' does not exist in MinIO bucket.",
        )

    # 2 & 3. Create ingestion job in DB
    try:
        doc_id, job_id, job_status = await create_ingestion_job(
            title=payload.title,
            object_key=payload.object_key,
            metadata=payload.metadata,
        )
        return DocumentIngestResponse(
            document_id=doc_id,
            job_id=job_id,
            status=job_status,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ingestion job: {e}",
        )


# ─── new endpoint: multipart upload ──────────────────────────────────────────

@router.post(
    "/documents/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF file and optionally process it immediately",
)
async def upload_document(
    file: UploadFile,
    title: str = Form(...),
    type: str = Form(...),
    client_name: str = Form(default=""),
    industry: str = Form(default=""),
    geography: str = Form(default=""),
    use_case: str = Form(default=""),
    tags: str = Form(default=""),
    authors: str = Form(default=""),
    process_immediately: bool = Form(default=True),
):
    """
    Upload a PDF document to MinIO, register it in the database, and
    optionally run the full ingestion pipeline immediately.

    When process_immediately=true the response includes chunks_created.
    When process_immediately=false the response has status='pending'.
    """
    # 1. File presence check
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    # 2. MVP: PDF only
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported in this MVP version.",
        )

    # 3. Build a safe base key from the original filename
    base_key = _sanitize_object_key(file.filename)

    # 4. Avoid overwriting an existing object — use a unique key
    if check_object_exists(base_key):
        object_key = _unique_object_key(base_key)
        logger.info(
            f"Object '{base_key}' already exists in MinIO; "
            f"using unique key '{object_key}'"
        )
    else:
        object_key = base_key

    # 5. Read file bytes
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 6. Upload to MinIO
    try:
        upload_object(settings.MINIO_BUCKET, object_key, file_bytes, "application/pdf")
    except Exception as e:
        logger.error(f"MinIO upload failed for '{object_key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage. Check server logs.",
        )

    # 7. Parse optional comma-separated metadata fields
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    authors_list = [a.strip() for a in authors.split(",") if a.strip()]

    metadata = DocumentMetadata(
        type=type,
        client_name=client_name,
        industry=industry,
        geography=geography,
        use_case=use_case,
        tags=tags_list,
        authors=authors_list,
    )

    # 8. Create document and ingestion job rows
    try:
        doc_id, job_id, _ = await create_ingestion_job(
            title=title,
            object_key=object_key,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"DB job creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File uploaded but failed to create ingestion job. Check server logs.",
        )

    # 9. Optionally process immediately
    if process_immediately:
        try:
            result = await process_job(job_id)
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        except Exception as e:
            logger.error(f"Immediate processing failed for job {job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File uploaded but processing failed. Check server logs.",
            )

    return {
        "document_id": doc_id,
        "job_id": job_id,
        "status": "pending",
    }


# ─── existing endpoint: semantic search ──────────────────────────────────────

@router.post(
    "/documents/search",
    response_model=DocumentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search document chunks semantically",
)
async def search_documents(payload: DocumentSearchRequest):
    """
    Search document chunks semantically using OpenAI query embeddings and pgvector.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty or whitespace-only.",
        )

    try:
        embeddings = generate_embeddings([payload.query])
        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embedding for search query.",
            )
        query_embedding = embeddings[0]

        results_data = await search_document_chunks(
            query_embedding=query_embedding,
            limit=payload.limit,
            filters=payload.filters,
        )

        results = [DocumentSearchResult(**item) for item in results_data]
        return DocumentSearchResponse(query=payload.query, results=results)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}",
        )

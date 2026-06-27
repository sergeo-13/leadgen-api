"""Document management endpoints."""

import logging
import os
import re
import uuid as uuid_lib
import json
import time
from typing import Optional, List

from fastapi import APIRouter, Form, HTTPException, UploadFile, status, Depends

from src.config import settings
from src.dependencies.auth import get_current_user
from src.dependencies.csrf import verify_csrf
from src.models.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentMetadata,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentResponse,
    JobResponse,
    DocumentUploadResponse,
    ReingestRequest,
)
from src.services.database import (
    create_ingestion_job,
    list_documents,
    get_document_by_id,
    update_document_metadata,
    update_document_source,
    get_jobs_by_document_id,
    archive_document,
    restore_document,
)
from src.services.search_service import perform_semantic_search
from src.services.document_parser import SUPPORTED_EXTENSIONS, SUPPORTED_FORMATS_ERROR
from src.services.ingestion_service import process_job
from src.services.minio_service import check_object_exists, upload_object

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


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
    basename = os.path.basename(filename)  # strip path components
    name, ext = os.path.splitext(basename)
    name = name.lower()
    name = re.sub(r"[^\w\-]", "_", name)  # keep word chars and hyphens
    name = re.sub(r"_+", "_", name).strip("_")  # collapse/strip underscores
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
    dependencies=[Depends(verify_csrf)],
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
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a source file and optionally process it immediately",
    dependencies=[Depends(verify_csrf)],
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
    description: Optional[str] = Form(default=None),
    source_type: Optional[str] = Form(default=None),
    source_url: Optional[str] = Form(default=None),
    metadata: Optional[str] = Form(default=None),
    process_immediately: bool = Form(default=True),
):
    """
    Upload a source document to MinIO, register it in the database, and
    optionally run the full ingestion pipeline immediately.

    When process_immediately=true the response includes chunks_created.
    When process_immediately=false the response has status='uploaded'.
    """
    # 1. File presence check
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    # 2. Check supported formats
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=SUPPORTED_FORMATS_ERROR,
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    file_size = len(file_bytes)
    mime_mappings = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".csv": "text/csv",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    inferred_mime = mime_mappings.get(ext, "application/octet-stream")
    mime_type = file.content_type or inferred_mime

    # 6. Upload to MinIO
    try:
        upload_object(settings.MINIO_BUCKET, object_key, file_bytes, mime_type)
        logger.info(
            f"Document uploaded successfully: {object_key} (size={file_size} bytes)"
        )
    except Exception as e:
        logger.error(f"MinIO upload failed for '{object_key}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage. Check server logs.",
        )

    # 7. Parse optional comma-separated metadata fields and custom metadata
    custom_metadata_dict = None
    if metadata and metadata.strip():
        try:
            custom_metadata_dict = json.loads(metadata)
            if not isinstance(custom_metadata_dict, dict):
                raise ValueError("Metadata must be a JSON object")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON metadata: {e}",
            )

    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
    authors_list = [a.strip() for a in authors.split(",") if a.strip()]

    metadata_obj = DocumentMetadata(
        type=type,
        client_name=client_name,
        industry=industry,
        geography=geography,
        use_case=use_case,
        tags=tags_list,
        authors=authors_list,
        description=description,
        source_type=source_type,
        source_url=source_url,
        file_name=base_key,
        mime_type=mime_type,
        file_size=file_size,
        metadata=custom_metadata_dict,
    )

    # 8. Create document and ingestion job rows
    try:
        doc_id, job_id, _ = await create_ingestion_job(
            title=title,
            object_key=object_key,
            metadata=metadata_obj,
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
            return DocumentUploadResponse(
                document_id=doc_id,
                job_id=job_id,
                status=result["status"],
                source_object_key=object_key,
                source_bucket=settings.MINIO_BUCKET,
                chunks_created=result.get("chunks_created"),
            )
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

    return DocumentUploadResponse(
        document_id=doc_id,
        job_id=job_id,
        status="uploaded",
        source_object_key=object_key,
        source_bucket=settings.MINIO_BUCKET,
    )


# ─── existing endpoint: semantic search ──────────────────────────────────────


@router.post(
    "/documents/search",
    response_model=DocumentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search document chunks semantically",
    dependencies=[Depends(verify_csrf)],
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
        results = await perform_semantic_search(
            query=payload.query,
            limit=payload.limit,
            filters=payload.filters,
        )
        return DocumentSearchResponse(query=payload.query, results=results)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}",
        )


@router.get(
    "/documents", response_model=List[DocumentResponse], summary="List all documents"
)
async def get_documents():
    """Retrieve all documents with chunk counts."""
    try:
        return await list_documents()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {e}",
        )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(document_id: str):
    """Retrieve details for a specific document."""
    try:
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {e}",
        )


@router.patch(
    "/documents/{document_id}",
    summary="Update document metadata",
    dependencies=[Depends(verify_csrf)],
)
async def patch_document(document_id: str, title: str, metadata: DocumentMetadata):
    """
    Update title and metadata columns for a specific document.
    Does NOT trigger re-ingest.
    """
    try:
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )

        success = await update_document_metadata(document_id, title, metadata)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update document metadata in database.",
            )
        return {
            "status": "success",
            "message": "Document metadata updated successfully.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update metadata: {e}",
        )


@router.post(
    "/documents/{document_id}/reingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rebuild Search Index",
    dependencies=[Depends(verify_csrf)],
)
async def reingest_document(document_id: str, payload: ReingestRequest):
    """
    Rebuild search index from the existing source file.
    Does NOT run if document is archived.
    """
    doc = await get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    if doc["status"] == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rebuild search index for an archived document. Please restore the document first.",
        )

    try:
        # Create a new ingestion job entry
        tags_list = doc["tags"]
        authors_list = doc["authors"]
        metadata_obj = DocumentMetadata(
            type=doc["type"] or "case",
            client_name=doc["client_name"] or "",
            industry=doc["industry"] or "",
            geography=doc["geography"] or "",
            use_case=doc["use_case"] or "",
            tags=tags_list,
            authors=authors_list,
            description=doc["description"],
            source_type=doc["source_type"],
            source_url=doc["source_url"],
            file_name=doc["file_name"],
            mime_type=doc["mime_type"],
            file_size=doc["file_size"],
            metadata=doc["metadata"],
        )

        doc_id, job_id, job_status = await create_ingestion_job(
            title=doc["title"],
            object_key=doc["source_object_key"],
            metadata=metadata_obj,
        )

        if payload.process_immediately:
            result = await process_job(job_id)
            return DocumentIngestResponse(
                document_id=doc_id, job_id=job_id, status=result["status"]
            )

        return DocumentIngestResponse(
            document_id=doc_id, job_id=job_id, status=job_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger rebuild: {e}",
        )


@router.post(
    "/documents/{document_id}/replace-file",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Replace document file and rebuild search index",
    dependencies=[Depends(verify_csrf)],
)
async def replace_document_file(
    document_id: str, file: UploadFile, process_immediately: bool = Form(default=True)
):
    """
    Upload a new file version key, update references, and rebuild search index.
    Does NOT overwrite previous source object in MinIO.
    If MinIO upload succeeds but DB update fails, logs orphan object_key clearly.
    """
    doc = await get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided."
        )

    _, ext = os.path.splitext(file.filename.lower())
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=SUPPORTED_FORMATS_ERROR,
        )

    # Build unique versioned key: documents/{document_id}/versions/{timestamp}_{safe_filename}
    safe_filename = _sanitize_object_key(file.filename)
    timestamp = int(time.time())
    new_object_key = f"documents/{document_id}/versions/{timestamp}_{safe_filename}"

    try:
        file_bytes = await file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )

    file_size = len(file_bytes)
    mime_mappings = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".csv": "text/csv",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    inferred_mime = mime_mappings.get(ext, "application/octet-stream")
    mime_type = file.content_type or inferred_mime

    # Upload new version to MinIO
    try:
        upload_object(settings.MINIO_BUCKET, new_object_key, file_bytes, mime_type)
        logger.info(f"New document version uploaded to MinIO: {new_object_key}")
    except Exception as e:
        logger.error(f"MinIO upload failed during replace file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload new version to storage.",
        )

    # Update DB references. If this fails, log the orphan key.
    try:
        success = await update_document_source(
            document_id=document_id,
            source_object_key=new_object_key,
            file_name=safe_filename,
            mime_type=mime_type,
            file_size=file_size,
        )
        if not success:
            raise Exception("Database update returned unsuccessful status.")
    except Exception:
        logger.error(
            f"CRITICAL: Replace file DB update failed for document {document_id}. "
            f"Uploaded orphan MinIO object_key: '{new_object_key}'"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File uploaded but database reference update failed. Check logs.",
        )

    # Trigger Rebuild Search Index
    try:
        # Get refreshed document details
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found after replace.",
            )
        tags_list = doc["tags"]
        authors_list = doc["authors"]
        metadata_obj = DocumentMetadata(
            type=doc["type"] or "case",
            client_name=doc["client_name"] or "",
            industry=doc["industry"] or "",
            geography=doc["geography"] or "",
            use_case=doc["use_case"] or "",
            tags=tags_list,
            authors=authors_list,
            description=doc["description"],
            source_type=doc["source_type"],
            source_url=doc["source_url"],
            file_name=doc["file_name"],
            mime_type=doc["mime_type"],
            file_size=doc["file_size"],
            metadata=doc["metadata"],
        )

        doc_id, job_id, job_status = await create_ingestion_job(
            title=doc["title"], object_key=new_object_key, metadata=metadata_obj
        )

        if process_immediately:
            result = await process_job(job_id)
            return DocumentUploadResponse(
                document_id=doc_id,
                job_id=job_id,
                status=result["status"],
                source_object_key=new_object_key,
                source_bucket=settings.MINIO_BUCKET,
                chunks_created=result.get("chunks_created"),
            )

        return DocumentUploadResponse(
            document_id=doc_id,
            job_id=job_id,
            status=job_status,
            source_object_key=new_object_key,
            source_bucket=settings.MINIO_BUCKET,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rebuild after file replacement failed: {e}",
        )


@router.post(
    "/documents/{document_id}/archive",
    summary="Archive document",
    dependencies=[Depends(verify_csrf)],
)
async def archive_doc(document_id: str):
    """Soft-delete/archive document. Sets status to 'archived'."""
    try:
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        success = await archive_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to archive document.",
            )
        return {
            "status": "success",
            "message": f"Document '{document_id}' archived successfully.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive document: {e}",
        )


@router.post(
    "/documents/{document_id}/restore",
    summary="Restore document",
    dependencies=[Depends(verify_csrf)],
)
async def restore_doc(document_id: str):
    """Restore document. If chunks are present, sets status to 'processed'; else 'uploaded'."""
    try:
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        success = await restore_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore document.",
            )
        # Fetch updated status to return
        updated_doc = await get_document_by_id(document_id)
        if not updated_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found after restore.",
            )
        return {
            "status": "success",
            "message": f"Document '{document_id}' restored successfully.",
            "document_status": updated_doc["status"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore document: {e}",
        )


@router.get(
    "/documents/{document_id}/jobs",
    response_model=List[JobResponse],
    summary="Get jobs associated with a document",
)
async def get_document_jobs(document_id: str):
    """Retrieve all ingestion jobs associated with the document."""
    try:
        doc = await get_document_by_id(document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        return await get_jobs_by_document_id(document_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs: {e}",
        )

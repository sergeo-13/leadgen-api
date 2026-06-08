"""Document management endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.models.schemas import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from src.services.database import create_ingestion_job, search_document_chunks
from src.services.embedding_service import generate_embeddings
from src.services.minio_service import check_object_exists

router = APIRouter()


@router.post(
    "/documents/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new document"
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
            detail=f"Object '{payload.object_key}' does not exist in MinIO bucket."
        )

    # 2 & 3. Create ingestion job in DB
    try:
        doc_id, job_id, job_status = await create_ingestion_job(
            title=payload.title,
            object_key=payload.object_key,
            metadata=payload.metadata
        )
        return DocumentIngestResponse(
            document_id=doc_id,
            job_id=job_id,
            status=job_status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ingestion job: {e}"
        )


@router.post(
    "/documents/search",
    response_model=DocumentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search document chunks semantically"
)
async def search_documents(payload: DocumentSearchRequest):
    """
    Search document chunks semantically using OpenAI query embeddings and pgvector.
    """
    # 1. Validate query is not empty (min_length=1 checks this, but we explicitly validate)
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty or whitespace-only."
        )

    try:
        # 2 & 3. Generate query embedding using OpenAI
        embeddings = generate_embeddings([payload.query])
        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate embedding for search query."
            )
        query_embedding = embeddings[0]

        # 4. Search document chunks
        results_data = await search_document_chunks(
            query_embedding=query_embedding,
            limit=payload.limit,
            filters=payload.filters
        )

        # 5. Format results
        results = [DocumentSearchResult(**item) for item in results_data]

        return DocumentSearchResponse(
            query=payload.query,
            results=results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )

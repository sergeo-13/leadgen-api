"""Ingestion API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends

from src.dependencies.auth import verify_ingestion_api_key
from src.models.schemas import JobResponse
from src.services.database import (
    get_job_details_by_id,
    list_ingestion_jobs,
    retry_ingestion_job,
)
from src.services.ingestion_service import process_job, process_next_job

router = APIRouter(dependencies=[Depends(verify_ingestion_api_key)])


@router.post(
    "/ingestion/process-next",
    status_code=status.HTTP_200_OK,
    summary="Process the next pending ingestion job",
)
async def process_next():
    """
    Process the next pending ingestion job.

    Loads one pending job from the database, claims it,
    downloads the file from MinIO, parses it, chunks it,
    generates embeddings via OpenAI, and stores it in Postgres.
    """
    try:
        result = await process_next_job()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion processing failed: {str(e)}",
        )


@router.get(
    "/ingestion/jobs",
    response_model=List[JobResponse],
    status_code=status.HTTP_200_OK,
    summary="List ingestion jobs",
)
async def list_jobs(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by job status"
    ),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset results"),
):
    """List all ingestion jobs with optional filtering by status and document_id, supporting pagination."""
    try:
        return await list_ingestion_jobs(
            status=status_filter, document_id=document_id, limit=limit, offset=offset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ingestion jobs: {e}",
        )


@router.get(
    "/ingestion/jobs/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ingestion job details",
)
async def get_job(job_id: str):
    """Retrieve details for a specific ingestion job."""
    try:
        job = await get_job_details_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingestion job '{job_id}' not found.",
            )
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion job: {e}",
        )


@router.post(
    "/ingestion/jobs/{job_id}/retry",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry a failed ingestion job",
)
async def retry_job(
    job_id: str,
    process_immediately: bool = Query(
        True, description="Process job immediately after retry"
    ),
):
    """
    Retry a failed ingestion job.
    Resets status to 'pending', error to NULL, and the related document status to 'uploaded'.
    If process_immediately is True, triggers immediate processing.
    Only allowed for failed jobs.
    """
    try:
        await retry_ingestion_job(job_id)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during retry: {e}",
        )

    if process_immediately:
        try:
            await process_job(job_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job retry reset succeeded, but immediate processing failed: {e}",
            )

    job_details = await get_job_details_by_id(job_id)
    if not job_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job '{job_id}' not found after retry.",
        )
    return job_details

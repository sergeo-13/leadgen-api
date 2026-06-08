"""Ingestion API endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.services.ingestion_service import process_next_job

router = APIRouter()


@router.post(
    "/ingestion/process-next",
    status_code=status.HTTP_200_OK,
    summary="Process the next pending ingestion job"
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
            detail=f"Ingestion processing failed: {str(e)}"
        )

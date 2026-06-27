"""Tests for the document ingestion processing endpoint."""

from unittest.mock import AsyncMock, patch
import pytest


def test_api_process_next_no_pending_jobs(client):
    """Test API endpoint when no pending jobs are available."""
    with patch(
        "src.api.v1.ingestion.process_next_job", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = {"status": "no_pending_jobs"}
        response = client.post("/api/v1/ingestion/process-next")
        assert response.status_code == 200
        assert response.json() == {"status": "no_pending_jobs"}
        mock_process.assert_called_once()


def test_api_process_next_success(client):
    """Test API endpoint success path."""
    expected_result = {
        "status": "completed",
        "job_id": "job-123",
        "document_id": "doc-456",
        "chunks_created": 3,
    }
    with patch(
        "src.api.v1.ingestion.process_next_job", new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = expected_result
        response = client.post("/api/v1/ingestion/process-next")
        assert response.status_code == 200
        assert response.json() == expected_result
        mock_process.assert_called_once()


def test_api_process_next_exception(client):
    """Test API endpoint error path."""
    with patch(
        "src.api.v1.ingestion.process_next_job", new_callable=AsyncMock
    ) as mock_process:
        mock_process.side_effect = Exception("OpenAI API limit exceeded")
        response = client.post("/api/v1/ingestion/process-next")
        assert response.status_code == 500
        assert "OpenAI API limit exceeded" in response.json()["detail"]
        mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_service_process_next_success():
    """Test core ingestion service successful run."""
    # get_and_claim_next_pending_job only needs job_id for delegation
    claim_mock = {"job_id": "job-uuid-1"}

    # get_job_by_id returns the full job details
    job_mock = {
        "job_id": "job-uuid-1",
        "document_id": "doc-uuid-1",
        "source_bucket": "leadgen-docs",
        "source_object_key": "proposal.pdf",
        "status": "pending",
    }

    from src.services.ingestion_service import process_next_job

    with patch(
        "src.services.ingestion_service.get_and_claim_next_pending_job",
        new_callable=AsyncMock,
    ) as mock_claim, patch(
        "src.services.ingestion_service.get_job_by_id", new_callable=AsyncMock
    ) as mock_get_job, patch(
        "src.services.ingestion_service.get_document_by_id", new_callable=AsyncMock
    ) as mock_get_doc, patch(
        "src.services.ingestion_service.claim_job", new_callable=AsyncMock
    ) as mock_claim_job, patch(
        "src.services.ingestion_service.download_object"
    ) as mock_download, patch(
        "src.services.ingestion_service.extract_text"
    ) as mock_parse, patch(
        "src.services.ingestion_service.split_text"
    ) as mock_chunk, patch(
        "src.services.ingestion_service.generate_embeddings"
    ) as mock_embed, patch(
        "src.services.ingestion_service.insert_document_chunks", new_callable=AsyncMock
    ) as mock_insert, patch(
        "src.services.ingestion_service.update_job_status", new_callable=AsyncMock
    ) as mock_update, patch(
        "src.services.ingestion_service.update_document_status", new_callable=AsyncMock
    ):

        mock_claim.return_value = claim_mock
        mock_get_job.return_value = job_mock
        mock_get_doc.return_value = {"id": "doc-uuid-1", "mime_type": "application/pdf"}
        mock_download.return_value = b"%PDF-1.4 mock content"
        mock_parse.return_value = "This is document content."
        mock_chunk.return_value = ["This is document content."]
        mock_embed.return_value = [[0.1] * 1536]

        result = await process_next_job()

        assert result == {
            "status": "completed",
            "job_id": "job-uuid-1",
            "document_id": "doc-uuid-1",
            "chunks_created": 1,
        }

        mock_claim.assert_called_once()
        mock_get_job.assert_called_once_with("job-uuid-1")
        mock_claim_job.assert_called_once_with("job-uuid-1")
        mock_download.assert_called_once_with("leadgen-docs", "proposal.pdf")
        mock_parse.assert_called_once_with(
            b"%PDF-1.4 mock content", "proposal.pdf", "application/pdf"
        )
        mock_chunk.assert_called_once_with("This is document content.")
        mock_embed.assert_called_once_with(["This is document content."])
        mock_insert.assert_called_once_with(
            "doc-uuid-1", [(0, "This is document content.", [0.1] * 1536)]
        )
        mock_update.assert_any_call("job-uuid-1", "completed")


@pytest.mark.asyncio
async def test_service_process_next_invalid_file_type():
    """Test core ingestion service file type verification failure."""
    claim_mock = {"job_id": "job-uuid-2"}

    job_mock = {
        "job_id": "job-uuid-2",
        "document_id": "doc-uuid-2",
        "source_bucket": "leadgen-docs",
        "source_object_key": "not_a_pdf.png",
        "status": "pending",
    }

    from src.services.ingestion_service import process_next_job

    with patch(
        "src.services.ingestion_service.get_and_claim_next_pending_job",
        new_callable=AsyncMock,
    ) as mock_claim, patch(
        "src.services.ingestion_service.get_job_by_id", new_callable=AsyncMock
    ) as mock_get_job, patch(
        "src.services.ingestion_service.claim_job", new_callable=AsyncMock
    ), patch(
        "src.services.ingestion_service.update_job_status", new_callable=AsyncMock
    ) as mock_update, patch(
        "src.services.ingestion_service.update_document_status", new_callable=AsyncMock
    ):

        mock_claim.return_value = claim_mock
        mock_get_job.return_value = job_mock

        with pytest.raises(ValueError) as exc:
            await process_next_job()

        assert "Unsupported file type" in str(exc.value)
        mock_update.assert_called_once_with(
            "job-uuid-2",
            "failed",
            "Unsupported file type. Supported formats: PDF, TXT, Markdown, CSV, DOCX, XLSX.",
        )

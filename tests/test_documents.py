"""Tests for document ingestion endpoint."""

from unittest.mock import AsyncMock, patch


def test_ingest_document_success(client):
    """Test successful document ingestion."""
    payload = {
        "object_key": "example.pdf",
        "title": "Example Document",
        "metadata": {
            "type": "case",
            "client_name": "Test Client",
            "industry": "Tech",
            "geography": "US",
            "use_case": "AI",
            "capabilities": ["Machine Learning"],
            "authors": ["John Doe"]
        }
    }

    # Mock MinIO check to return True and DB insert to succeed
    with patch("src.api.v1.documents.check_object_exists", return_value=True) as mock_minio, \
         patch("src.api.v1.documents.create_ingestion_job", new_callable=AsyncMock) as mock_db:

        mock_db.return_value = (
            "doc-uuid-1234",
            "job-uuid-5678",
            "pending"
        )

        response = client.post("/api/v1/documents/ingest", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["document_id"] == "doc-uuid-1234"
        assert data["job_id"] == "job-uuid-5678"
        assert data["status"] == "pending"

        mock_minio.assert_called_once_with("example.pdf")
        mock_db.assert_called_once()


def test_ingest_document_missing_minio_object(client):
    """Test ingestion fails when object is missing in MinIO."""
    payload = {
        "object_key": "nonexistent.pdf",
        "title": "Missing Document",
        "metadata": {
            "type": "case"
        }
    }

    with patch("src.api.v1.documents.check_object_exists", return_value=False) as mock_minio:
        response = client.post("/api/v1/documents/ingest", json=payload)
        assert response.status_code == 400
        assert "does not exist in MinIO" in response.json()["detail"]
        mock_minio.assert_called_once_with("nonexistent.pdf")


def test_ingest_document_validation_error(client):
    """Test ingestion validation error for missing required fields."""
    payload = {
        "object_key": "missing_metadata.pdf",
        "title": "Missing Metadata"
        # metadata is missing
    }

    response = client.post("/api/v1/documents/ingest", json=payload)
    assert response.status_code == 422

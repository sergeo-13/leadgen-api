"""Tests for document stabilization endpoints."""

from unittest.mock import AsyncMock, patch
from datetime import datetime


# ─── GET /api/v1/documents ───────────────────────────────────────────────────


def test_list_documents(client):
    """Test retrieving list of all documents."""
    mock_docs = [
        {
            "id": "doc-1",
            "title": "Document One",
            "type": "case",
            "client_name": "Acme",
            "industry": "Tech",
            "geography": "US",
            "use_case": "QA",
            "tags": ["ml"],
            "authors": ["Author A"],
            "source_bucket": "docs",
            "source_object_key": "doc1.pdf",
            "status": "processed",
            "confidentiality_level": "internal",
            "description": "Desc 1",
            "source_type": "local",
            "source_url": "http://doc1",
            "file_name": "doc1.pdf",
            "mime_type": "application/pdf",
            "file_size": 12345,
            "metadata": {},
            "chunks_count": 5,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    ]
    with patch(
        "src.api.v1.documents.list_documents", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_docs
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "doc-1"
        assert data[0]["chunks_count"] == 5
        mock_list.assert_called_once()


# ─── GET /api/v1/documents/{id} ───────────────────────────────────────────────


def test_get_document_by_id_success(client):
    """Test getting a specific document's details successfully."""
    mock_doc = {
        "id": "doc-1",
        "title": "Document One",
        "type": "case",
        "client_name": "Acme",
        "industry": "Tech",
        "geography": "US",
        "use_case": "QA",
        "tags": ["ml"],
        "authors": ["Author A"],
        "source_bucket": "docs",
        "source_object_key": "doc1.pdf",
        "status": "processed",
        "confidentiality_level": "internal",
        "description": "Desc 1",
        "source_type": "local",
        "source_url": "http://doc1",
        "file_name": "doc1.pdf",
        "mime_type": "application/pdf",
        "file_size": 12345,
        "metadata": {},
        "chunks_count": 5,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_doc
        response = client.get("/api/v1/documents/doc-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc-1"
        assert data["title"] == "Document One"
        mock_get.assert_called_once_with("doc-1")


def test_get_document_by_id_not_found(client):
    """Test getting a non-existent document returns 404."""
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None
        response = client.get("/api/v1/documents/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ─── PATCH /api/v1/documents/{id} ─────────────────────────────────────────────


def test_patch_document_metadata_success(client):
    """Test updating a document's metadata."""
    mock_doc = {
        "id": "doc-1",
        "title": "Document One",
        "status": "processed",
        "chunks_count": 5,
    }
    payload = {
        "type": "proposal",
        "client_name": "New Client",
        "industry": "Tech",
        "geography": "EU",
        "use_case": "Sales",
        "tags": ["tag1"],
        "authors": ["Author B"],
        "description": "New description",
        "source_type": "gdrive",
        "source_url": "http://gdrive/doc1",
        "metadata": {"custom_field": "val"},
    }
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get, patch(
        "src.api.v1.documents.update_document_metadata", new_callable=AsyncMock
    ) as mock_update:

        mock_get.return_value = mock_doc
        mock_update.return_value = True

        response = client.patch("/api/v1/documents/doc-1?title=New Title", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        mock_get.assert_called_once_with("doc-1")
        mock_update.assert_called_once()


# ─── POST /api/v1/documents/{id}/reingest ──────────────────────────────────────


def test_reingest_document_success(client):
    """Test rebuilding search index successfully."""
    mock_doc = {
        "id": "doc-1",
        "title": "Doc Title",
        "type": "case",
        "client_name": "Acme",
        "industry": "Tech",
        "geography": "US",
        "use_case": "QA",
        "tags": ["ml"],
        "authors": ["Author"],
        "source_bucket": "docs",
        "source_object_key": "doc1.pdf",
        "status": "processed",
        "description": "Desc",
        "source_type": "local",
        "source_url": "http://doc1",
        "file_name": "doc1.pdf",
        "mime_type": "application/pdf",
        "file_size": 12345,
        "metadata": {},
    }
    payload = {"process_immediately": True, "reason": "manual_rebuild"}
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get, patch(
        "src.api.v1.documents.create_ingestion_job", new_callable=AsyncMock
    ) as mock_create_job, patch(
        "src.api.v1.documents.process_job", new_callable=AsyncMock
    ) as mock_process:

        mock_get.return_value = mock_doc
        mock_create_job.return_value = ("doc-1", "job-1", "pending")
        mock_process.return_value = {"status": "completed", "chunks_created": 10}

        response = client.post("/api/v1/documents/doc-1/reingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["document_id"] == "doc-1"
        assert data["job_id"] == "job-1"
        assert data["status"] == "completed"

        mock_get.assert_called_once_with("doc-1")
        mock_create_job.assert_called_once()
        mock_process.assert_called_once_with("job-1")


def test_reingest_document_archived_error(client):
    """Test rebuilding search index fails for archived document."""
    mock_doc = {"id": "doc-1", "title": "Doc Title", "status": "archived"}
    payload = {"process_immediately": True, "reason": "manual_rebuild"}
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_doc
        response = client.post("/api/v1/documents/doc-1/reingest", json=payload)
        assert response.status_code == 400
        assert "archived document" in response.json()["detail"]


# ─── POST /api/v1/documents/{id}/replace-file ──────────────────────────────────


def test_replace_file_success(client):
    """Test replacing document file and rebuilding search index."""
    mock_doc = {
        "id": "doc-1",
        "title": "Doc Title",
        "type": "case",
        "client_name": "Acme",
        "industry": "Tech",
        "geography": "US",
        "use_case": "QA",
        "tags": ["ml"],
        "authors": ["Author"],
        "source_bucket": "docs",
        "source_object_key": "doc1.pdf",
        "status": "processed",
        "description": "Desc",
        "source_type": "local",
        "source_url": "http://doc1",
        "file_name": "doc1.pdf",
        "mime_type": "application/pdf",
        "file_size": 12345,
        "metadata": {},
    }
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get, patch("src.api.v1.documents.upload_object") as mock_upload, patch(
        "src.api.v1.documents.update_document_source", new_callable=AsyncMock
    ) as mock_update_src, patch(
        "src.api.v1.documents.create_ingestion_job", new_callable=AsyncMock
    ) as mock_create_job, patch(
        "src.api.v1.documents.process_job", new_callable=AsyncMock
    ) as mock_process:

        mock_get.return_value = mock_doc
        mock_update_src.return_value = True
        mock_create_job.return_value = ("doc-1", "job-2", "pending")
        mock_process.return_value = {"status": "completed", "chunks_created": 8}

        file_payload = {
            "file": ("new_version.pdf", b"%PDF-1.4 mock new content", "application/pdf")
        }
        response = client.post(
            "/api/v1/documents/doc-1/replace-file",
            files=file_payload,
            data={"process_immediately": "true"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["document_id"] == "doc-1"
        assert data["job_id"] == "job-2"
        assert data["status"] == "completed"

        mock_upload.assert_called_once()
        mock_update_src.assert_called_once()


# ─── POST /api/v1/documents/{id}/archive & restore ───────────────────────────────


def test_archive_and_restore_document(client):
    """Test archiving and restoring document endpoints."""
    mock_doc = {"id": "doc-1", "title": "Doc Title", "status": "processed"}
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get, patch(
        "src.api.v1.documents.archive_document", new_callable=AsyncMock
    ) as mock_archive, patch(
        "src.api.v1.documents.restore_document", new_callable=AsyncMock
    ) as mock_restore:

        mock_get.side_effect = [
            mock_doc,
            {**mock_doc, "status": "archived"},
            {**mock_doc, "status": "processed"},
        ]
        mock_archive.return_value = True
        mock_restore.return_value = True

        # Archive
        resp_arc = client.post("/api/v1/documents/doc-1/archive")
        assert resp_arc.status_code == 200
        assert resp_arc.json()["status"] == "success"
        mock_archive.assert_called_once_with("doc-1")

        # Restore
        resp_res = client.post("/api/v1/documents/doc-1/restore")
        assert resp_res.status_code == 200
        assert resp_res.json()["status"] == "success"
        mock_restore.assert_called_once_with("doc-1")


# ─── GET /api/v1/documents/{id}/jobs ─────────────────────────────────────────


def test_get_document_jobs(client):
    """Test listing jobs for a specific document."""
    mock_doc = {"id": "doc-1", "title": "Doc Title"}
    mock_jobs = [
        {
            "job_id": "job-1",
            "document_id": "doc-1",
            "source_bucket": "docs",
            "source_object_key": "doc1.pdf",
            "status": "completed",
            "error": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    ]
    with patch(
        "src.api.v1.documents.get_document_by_id", new_callable=AsyncMock
    ) as mock_get, patch(
        "src.api.v1.documents.get_jobs_by_document_id", new_callable=AsyncMock
    ) as mock_jobs_list:

        mock_get.return_value = mock_doc
        mock_jobs_list.return_value = mock_jobs

        response = client.get("/api/v1/documents/doc-1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["job_id"] == "job-1"


# ─── GET /api/v1/ingestion/jobs ───────────────────────────────────────────────


def test_list_ingestion_jobs(client):
    """Test listing ingestion jobs with filters."""
    mock_jobs = [
        {
            "job_id": "job-1",
            "document_id": "doc-1",
            "source_bucket": "docs",
            "source_object_key": "doc1.pdf",
            "status": "failed",
            "error": "Error processing",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    ]
    with patch(
        "src.api.v1.ingestion.list_ingestion_jobs", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_jobs
        response = client.get("/api/v1/ingestion/jobs?status=failed&document_id=doc-1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "failed"
        mock_list.assert_called_once_with(
            status="failed", document_id="doc-1", limit=50, offset=0
        )


# ─── GET /api/v1/ingestion/jobs/{id} ──────────────────────────────────────────


def test_get_job_details(client):
    """Test getting single job details."""
    mock_job = {
        "job_id": "job-1",
        "document_id": "doc-1",
        "source_bucket": "docs",
        "source_object_key": "doc1.pdf",
        "status": "completed",
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    with patch(
        "src.api.v1.ingestion.get_job_details_by_id", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_job
        response = client.get("/api/v1/ingestion/jobs/job-1")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-1"
        assert data["status"] == "completed"


# ─── POST /api/v1/ingestion/jobs/{id}/retry ───────────────────────────────────


def test_retry_job_success(client):
    """Test successfully retrying a failed job."""
    mock_job = {
        "job_id": "job-1",
        "document_id": "doc-1",
        "source_bucket": "docs",
        "source_object_key": "doc1.pdf",
        "status": "completed",  # updated status after processing
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    with patch(
        "src.api.v1.ingestion.retry_ingestion_job", new_callable=AsyncMock
    ) as mock_retry, patch(
        "src.api.v1.ingestion.process_job", new_callable=AsyncMock
    ) as mock_process, patch(
        "src.api.v1.ingestion.get_job_details_by_id", new_callable=AsyncMock
    ) as mock_get:

        mock_retry.return_value = True
        mock_process.return_value = {"status": "completed"}
        mock_get.return_value = mock_job

        response = client.post(
            "/api/v1/ingestion/jobs/job-1/retry?process_immediately=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-1"
        assert data["status"] == "completed"

        mock_retry.assert_called_once_with("job-1")
        mock_process.assert_called_once_with("job-1")


def test_retry_job_not_failed_error(client):
    """Test retrying a non-failed job returns 400 Bad Request."""
    with patch(
        "src.api.v1.ingestion.retry_ingestion_job", new_callable=AsyncMock
    ) as mock_retry:
        mock_retry.side_effect = ValueError("Only failed jobs can be retried.")
        response = client.post("/api/v1/ingestion/jobs/job-1/retry")
        assert response.status_code == 400
        assert "Only failed jobs" in response.json()["detail"]

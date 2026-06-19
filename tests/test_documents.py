"""Tests for document ingestion and search endpoints."""

from unittest.mock import AsyncMock, patch
import pytest


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
            "tags": ["Machine Learning"],
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


def test_search_documents_success(client):
    """Test successful semantic search with mocks."""
    payload = {
        "query": "What is the role of OpenClaw in the leadgen architecture?",
        "limit": 5,
        "filters": {
            "type": "case",
            "client_name": "Acme",
            "industry": None,
            "geography": None,
            "use_case": None,
            "tags": ["Parsing"]
        }
    }

    mock_db_result = [
        {
            "document_id": "doc-uuid-1",
            "title": "Expanded Leadgen PRD",
            "type": "case",
            "client_name": "Acme",
            "industry": "Tech",
            "geography": "Global",
            "use_case": "Integration",
            "tags": ["Parsing"],
            "authors": ["Sergii Poznokos"],
            "source_bucket": "leadgen-docs",
            "source_object_key": "leadgen_prd_expanded.pdf",
            "chunk_id": "chunk-uuid-1",
            "chunk_index": 0,
            "content": "Matched chunk content about OpenClaw role.",
            "score": 0.87
        }
    ]

    with patch("src.services.search_service.generate_embeddings") as mock_embed, \
         patch("src.services.search_service.search_document_chunks", new_callable=AsyncMock) as mock_db:

        mock_embed.return_value = [[0.1] * 1536]
        mock_db.return_value = mock_db_result

        response = client.post("/api/v1/documents/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is the role of OpenClaw in the leadgen architecture?"
        assert len(data["results"]) == 1
        assert data["results"][0]["document_id"] == "doc-uuid-1"
        assert data["results"][0]["title"] == "Expanded Leadgen PRD"
        assert data["results"][0]["score"] == 0.87

        mock_embed.assert_called_once_with(["What is the role of OpenClaw in the leadgen architecture?"])
        mock_db.assert_called_once()


def test_search_documents_filters_null(client):
    """Test successful semantic search when filters is null/omitted."""
    payload = {
        "query": "What is the role of OpenClaw in the leadgen architecture?",
        "limit": 3
    }

    mock_db_result = [
        {
            "document_id": "doc-uuid-1",
            "title": "Expanded Leadgen PRD",
            "type": "case",
            "client_name": "Acme",
            "industry": "Tech",
            "geography": "Global",
            "use_case": "Integration",
            "tags": ["Parsing"],
            "authors": ["Sergii Poznokos"],
            "source_bucket": "leadgen-docs",
            "source_object_key": "leadgen_prd_expanded.pdf",
            "chunk_id": "chunk-uuid-1",
            "chunk_index": 0,
            "content": "Matched chunk content about OpenClaw role.",
            "score": 0.87
        }
    ]

    with patch("src.services.search_service.generate_embeddings") as mock_embed, \
         patch("src.services.search_service.search_document_chunks", new_callable=AsyncMock) as mock_db:

        mock_embed.return_value = [[0.1] * 1536]
        mock_db.return_value = mock_db_result

        response = client.post("/api/v1/documents/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "What is the role of OpenClaw in the leadgen architecture?"
        assert len(data["results"]) == 1
        assert data["results"][0]["document_id"] == "doc-uuid-1"
        assert data["results"][0]["title"] == "Expanded Leadgen PRD"
        assert data["results"][0]["score"] == 0.87
        assert data["results"][0]["authors"] == ["Sergii Poznokos"]

        mock_embed.assert_called_once_with(["What is the role of OpenClaw in the leadgen architecture?"])
        mock_db.assert_called_once_with(
            query_embedding=[0.1] * 1536,
            limit=3,
            filters=None,
            query_text="What is the role of OpenClaw in the leadgen architecture?"
        )


def test_search_documents_empty_query(client):
    """Test search fails on empty or whitespace-only query."""
    payload = {
        "query": "   ",
        "limit": 5
    }
    response = client.post("/api/v1/documents/search", json=payload)
    # Pydantic or custom logic will trigger 422 or 400
    assert response.status_code in [400, 422]


def test_search_documents_exception(client):
    """Test search endpoint error handling."""
    payload = {
        "query": "some search query"
    }
    with patch("src.services.search_service.generate_embeddings") as mock_embed:
        mock_embed.side_effect = Exception("OpenAI API limit exceeded")
        response = client.post("/api/v1/documents/search", json=payload)
        assert response.status_code == 500
        assert "OpenAI API limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_search_document_chunks_sql_construction():
    """Test SQL query construction and parameters for semantic search."""
    from src.services.database import search_document_chunks
    from src.models.schemas import DocumentSearchFilters

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    with patch("src.services.database.asyncpg.connect", new_callable=AsyncMock, return_value=mock_conn) as mock_connect:
        filters = DocumentSearchFilters(
            type="case",
            tags=["Machine Learning"]
        )

        await search_document_chunks(
            query_embedding=[0.1] * 1536,
            limit=5,
            filters=filters
        )

        mock_connect.assert_called_once()
        mock_conn.fetch.assert_called_once()
        called_args = mock_conn.fetch.call_args[0]
        called_query = called_args[0]
        called_params = called_args[1:]

        # Verify SQL structure
        assert "d.type = $2" in called_query
        assert "d.tags && $3::text[]" in called_query
        assert "LIMIT $4" in called_query
        assert "c.embedding IS NOT NULL" in called_query
        assert "1 - (c.embedding <=> $1::vector) AS score" in called_query
        assert "ORDER BY c.embedding <=> $1::vector ASC" in called_query

        # Verify SQL parameter bindings
        assert called_params[0] == f"[{','.join(map(str, [0.1] * 1536))}]"
        assert called_params[1] == "case"
        assert called_params[2] == ["Machine Learning"]
        assert called_params[3] == 5

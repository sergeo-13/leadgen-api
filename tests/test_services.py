"""Unit tests for services: chunker, embedding_service, minio_service."""

import io
import pytest
from unittest.mock import MagicMock, patch

from src.core.exceptions import MinIOConnectionError
from src.services.chunker import split_text
from src.services.embedding_service import generate_embeddings
from src.services.minio_service import (
    check_minio,
    check_object_exists,
    download_object,
    upload_object,
)


# ─── Chunker Service Tests ───────────────────────────────────────────────────

def test_split_text_empty():
    """Verify split_text returns empty list for empty/None input."""
    assert split_text("") == []
    assert split_text(None) == []


def test_split_text_single_chunk():
    """Verify split_text returns the whole string if it is smaller than chunk_size."""
    text = "Hello word."
    assert split_text(text, chunk_size=20, overlap=5) == ["Hello word."]


def test_split_text_with_overlap():
    """Verify standard splitting logic with overlap."""
    text = "abcdefghij"  # len 10
    # chunk_size=4, overlap=2, step=2
    # Chunks:
    # 0:4 -> abcd
    # 2:6 -> cdef
    # 4:8 -> efgh
    # 6:10 -> ghij
    result = split_text(text, chunk_size=4, overlap=2)
    assert result == ["abcd", "cdef", "efgh", "ghij"]


def test_split_text_invalid_overlap():
    """Verify safeguard triggers when overlap is greater than or equal to chunk_size."""
    text = "abcdefghij"
    # overlap=4, chunk_size=4 => step would be 0 or negative.
    # Should fall back to step=chunk_size (4)
    # Chunks:
    # 0:4 -> abcd
    # 4:8 -> efgh
    # 8:10 -> ij
    result = split_text(text, chunk_size=4, overlap=5)
    assert result == ["abcd", "efgh", "ij"]


# ─── Embedding Service Tests ──────────────────────────────────────────────────

def test_generate_embeddings_empty():
    """Verify generate_embeddings returns empty list for empty list input."""
    assert generate_embeddings([]) == []


def test_generate_embeddings_success():
    """Verify standard embedding generation using mocked OpenAI client."""
    mock_data_1 = MagicMock()
    mock_data_1.embedding = [0.1, 0.2]
    mock_data_2 = MagicMock()
    mock_data_2.embedding = [0.3, 0.4]

    mock_response = MagicMock()
    mock_response.data = [mock_data_1, mock_data_2]

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    with patch("src.services.embedding_service.get_openai_client", return_value=mock_client):
        result = generate_embeddings(["text1", "text2"], batch_size=2)
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_client.embeddings.create.assert_called_once()


def test_generate_embeddings_exception():
    """Verify generate_embeddings raises exception if OpenAI call fails."""
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = Exception("API error")

    with patch("src.services.embedding_service.get_openai_client", return_value=mock_client):
        with pytest.raises(Exception) as exc:
            generate_embeddings(["text1"])
        assert "API error" in str(exc.value)


# ─── MinIO Service Tests ──────────────────────────────────────────────────────

def test_check_minio_bucket_exists():
    """Verify check_minio returns True when bucket exists."""
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        assert check_minio() is True
        mock_client.bucket_exists.assert_called_once()


def test_check_minio_bucket_not_exists():
    """Verify check_minio returns False when bucket does not exist."""
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        assert check_minio() is False


def test_check_minio_connection_error():
    """Verify check_minio raises MinIOConnectionError on client error."""
    mock_client = MagicMock()
    mock_client.bucket_exists.side_effect = Exception("Connection timed out")

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        with pytest.raises(MinIOConnectionError) as exc:
            check_minio()
        assert "Failed to connect to MinIO" in str(exc.value)


def test_check_object_exists_true():
    """Verify check_object_exists returns True when stat_object succeeds."""
    mock_client = MagicMock()
    mock_client.stat_object.return_value = MagicMock()

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        assert check_object_exists("file.pdf") is True


def test_check_object_exists_false():
    """Verify check_object_exists returns False when stat_object raises an exception."""
    mock_client = MagicMock()
    mock_client.stat_object.side_effect = Exception("NoSuchKey")

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        assert check_object_exists("file.pdf") is False


def test_download_object_success():
    """Verify download_object returns file content bytes."""
    mock_response = MagicMock()
    mock_response.read.return_value = b"file bytes"
    
    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_response

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        result = download_object("bucket", "key")
        assert result == b"file bytes"
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()


def test_download_object_error():
    """Verify download_object raises original error on failure."""
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("MinIO offline")

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        with pytest.raises(Exception) as exc:
            download_object("bucket", "key")
        assert "MinIO offline" in str(exc.value)


def test_upload_object_success():
    """Verify upload_object invokes put_object with correct arguments."""
    mock_client = MagicMock()

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        upload_object("bucket", "key", b"my content", "text/plain")
        mock_client.put_object.assert_called_once()
        args, kwargs = mock_client.put_object.call_args
        assert args[0] == "bucket"
        assert args[1] == "key"
        assert kwargs["content_type"] == "text/plain"
        assert kwargs["length"] == 10


def test_upload_object_error():
    """Verify upload_object raises exception if put_object fails."""
    mock_client = MagicMock()
    mock_client.put_object.side_effect = Exception("Write error")

    with patch("src.services.minio_service.get_minio_client", return_value=mock_client):
        with pytest.raises(Exception) as exc:
            upload_object("bucket", "key", b"data")
        assert "Write error" in str(exc.value)

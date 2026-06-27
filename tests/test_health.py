"""Tests for health check endpoint."""


def test_health_endpoint(client):
    """Test health check endpoint returns valid response."""
    for path in ["/health", "/api/v1/health"]:
        response = client.get(path)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "postgres" in data
        assert "minio" in data
        assert "hermes" in data
        assert "version" in data
        assert data["status"] in ["ok", "degraded"]
        assert isinstance(data["postgres"], str)
        assert isinstance(data["minio"], str)
        assert isinstance(data["hermes"], str)
        assert isinstance(data["version"], str)
        assert data["postgres"] in ["ok", "error"]
        assert data["minio"] in ["ok", "error"]
        assert data["hermes"] in ["ok", "error"]




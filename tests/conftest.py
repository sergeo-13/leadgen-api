"""Pytest configuration and fixtures."""

import os
import pytest

# Ensure environment variables are set before any src module imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["ENTRA_ENABLED"] = "false"
os.environ["POSTGRES_HOST"] = "localhost"

from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

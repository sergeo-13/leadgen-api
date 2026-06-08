"""Application configuration management."""

import os
import subprocess
from typing import Optional

from pydantic_settings import BaseSettings


def get_git_commit_sha() -> str:
    """Get the current git commit SHA."""
    # Check environment variable
    sha = os.getenv("COMMIT_SHA")
    if sha:
        return sha

    # Check git command
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("ascii").strip()
    except Exception:
        # Check local file
        try:
            with open("commit_sha.txt", "r") as f:
                return f.read().strip()
        except Exception:
            return "unknown"


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    APP_NAME: str = "Leadgen Bot API"
    APP_VERSION: str = "0.1.0"
    COMMIT_SHA: str = get_git_commit_sha()

    # PostgreSQL
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "leadgen-postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "leadgen")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "leadgen-docs")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

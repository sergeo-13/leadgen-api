"""Application configuration management."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    APP_NAME: str = "Leadgen API"
    APP_VERSION: str = "0.1.1"

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

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

    # Ingestion Safety Limits
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    MAX_EXTRACTED_CHARS: int = int(os.getenv("MAX_EXTRACTED_CHARS", "500000"))
    MAX_CSV_ROWS: int = int(os.getenv("MAX_CSV_ROWS", "5000"))
    MAX_XLSX_ROWS_PER_SHEET: int = int(os.getenv("MAX_XLSX_ROWS_PER_SHEET", "5000"))

    # Hermes
    HERMES_API_BASE_URL: str = os.getenv("HERMES_API_BASE_URL", "http://hermes-gateway:8642")
    HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
    HERMES_DEFAULT_MODEL: str = os.getenv("HERMES_DEFAULT_MODEL", "hermes-agent")
    HERMES_TIMEOUT_SECONDS: int = int(os.getenv("HERMES_TIMEOUT_SECONDS", "120"))

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()

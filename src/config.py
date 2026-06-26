"""Application configuration management."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
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
    HERMES_WEBUI_URL: str = os.getenv("HERMES_WEBUI_URL", "")

    # MCP
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "true").lower() == "true"
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")
    MCP_ALLOWED_HOSTS: str = os.getenv("MCP_ALLOWED_HOSTS", "localhost:8000,127.0.0.1:8000,leadgen-api:8000,leadgen-api-dev:8000,localhost:*,127.0.0.1:*")
    MCP_ALLOWED_ORIGINS: str = os.getenv("MCP_ALLOWED_ORIGINS", "")

    # Authentication
    ENTRA_ENABLED: bool = os.getenv("ENTRA_ENABLED", "true").lower() == "true"
    ENTRA_CLIENT_ID: str = os.getenv("ENTRA_CLIENT_ID", "")
    ENTRA_CLIENT_SECRET: str = os.getenv("ENTRA_CLIENT_SECRET", "")
    ENTRA_AUTHORITY: str = os.getenv("ENTRA_AUTHORITY", "https://login.microsoftonline.com/organizations")
    ENTRA_REDIRECT_URI: str = os.getenv("ENTRA_REDIRECT_URI", "")
    ENTRA_POST_LOGOUT_REDIRECT_URI: str = os.getenv("ENTRA_POST_LOGOUT_REDIRECT_URI", "")

    # Session
    AUTH_SESSION_SIGNING_SECRET: str = os.getenv("AUTH_SESSION_SIGNING_SECRET", "")
    AUTH_SESSION_MAX_AGE_SECONDS: int = int(os.getenv("AUTH_SESSION_MAX_AGE_SECONDS", "28800"))
    AUTH_SESSION_COOKIE_SECURE: bool = os.getenv("AUTH_SESSION_COOKIE_SECURE", "true").lower() == "true"
    AUTH_SESSION_COOKIE_NAME: str = os.getenv("AUTH_SESSION_COOKIE_NAME", "leadgen_session")
    AUTH_LOGIN_TRANSACTION_TTL_SECONDS: int = int(os.getenv("AUTH_LOGIN_TRANSACTION_TTL_SECONDS", "600"))
    AUTH_TOKEN_CLOCK_SKEW_SECONDS: int = int(os.getenv("AUTH_TOKEN_CLOCK_SKEW_SECONDS", "120"))

    # Security
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    INGESTION_API_KEY: str = os.getenv("INGESTION_API_KEY", "")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()

# Validation for deployed environments
if not settings.ENTRA_ENABLED and settings.ENVIRONMENT in ("development", "production"):
    raise ValueError(
        f"ENTRA_ENABLED=false is strictly restricted to local or test environments. "
        f"Cannot disable Entra in '{settings.ENVIRONMENT}' environment."
    )

"""Pydantic schemas for request/response models."""

from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall system status")
    postgres: bool = Field(..., description="PostgreSQL connection status")
    minio: bool = Field(..., description="MinIO connection status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "postgres": True,
                "minio": True,
            }
        }


class LeadBase(BaseModel):
    """Base lead schema."""

    name: str = Field(..., description="Lead name")
    email: str = Field(..., description="Lead email")
    company: Optional[str] = Field(None, description="Company name")
    source: str = Field(default="unknown", description="Lead source")


class LeadCreate(LeadBase):
    """Lead creation schema."""

    pass


class Lead(LeadBase):
    """Lead schema with ID."""

    id: int = Field(..., description="Lead ID")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class DocumentMetadata(BaseModel):
    """Metadata for document ingestion."""

    type: str = Field(..., description="Document type")
    client_name: str = Field(default="", description="Client name")
    industry: str = Field(default="", description="Industry")
    geography: str = Field(default="", description="Geography")
    use_case: str = Field(default="", description="Use case")
    capabilities: list[str] = Field(default_factory=list, description="List of capabilities")
    authors: list[str] = Field(default_factory=list, description="List of authors")


class DocumentIngestRequest(BaseModel):
    """Request schema for document ingestion."""

    object_key: str = Field(..., description="MinIO object key")
    title: str = Field(..., description="Document title")
    metadata: DocumentMetadata = Field(..., description="Document metadata")


class DocumentIngestResponse(BaseModel):
    """Response schema for document ingestion."""

    document_id: str = Field(..., description="UUID of the ingested document")
    job_id: str = Field(..., description="UUID of the ingestion job")
    status: str = Field(..., description="Job status")

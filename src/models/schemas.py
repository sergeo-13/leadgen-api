"""Pydantic schemas for request/response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall system status")
    postgres: bool = Field(..., description="PostgreSQL connection status")
    minio: bool = Field(..., description="MinIO connection status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "postgres": True,
                "minio": True,
            }
        }
    )


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

    model_config = ConfigDict(from_attributes=True)


class DocumentMetadata(BaseModel):
    """Metadata for document ingestion."""

    type: str = Field(..., description="Document type")
    client_name: str = Field(default="", description="Client name")
    industry: str = Field(default="", description="Industry")
    geography: str = Field(default="", description="Geography")
    use_case: str = Field(default="", description="Use case")
    tags: list[str] = Field(default_factory=list, description="List of tags")
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


class DocumentSearchFilters(BaseModel):
    """Filters for document search."""

    type: Optional[str] = None
    client_name: Optional[str] = None
    industry: Optional[str] = None
    geography: Optional[str] = None
    use_case: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DocumentSearchRequest(BaseModel):
    """Request schema for document search."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=100, description="Limit results")
    filters: Optional[DocumentSearchFilters] = None

    @field_validator("query", mode="before")
    @classmethod
    def trim_query(cls, v):
        """Trim leading/trailing whitespace from the query."""
        if isinstance(v, str):
            v = v.strip()
        return v


class DocumentSearchResult(BaseModel):
    """A single document search result chunk."""

    document_id: str
    title: str
    type: Optional[str] = None
    client_name: Optional[str] = None
    industry: Optional[str] = None
    geography: Optional[str] = None
    use_case: Optional[str] = None
    tags: list[str]
    authors: list[str] = Field(default_factory=list)
    source_bucket: str
    source_object_key: str
    chunk_id: str
    chunk_index: int
    content: str
    score: float


class DocumentSearchResponse(BaseModel):
    """Response schema for document search."""

    query: str
    results: list[DocumentSearchResult]

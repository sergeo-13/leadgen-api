import logging
from typing import List, Optional
from src.models.schemas import DocumentSearchFilters, DocumentSearchResult
from src.services.embedding_service import generate_embeddings
from src.services.database import search_document_chunks

logger = logging.getLogger(__name__)


async def perform_semantic_search(
    query: str,
    limit: int = 5,
    filters: Optional[DocumentSearchFilters] = None,
) -> List[DocumentSearchResult]:
    """
    Coordination service for semantic document search.
    Generates embeddings and queries pgvector.
    Does not contain HTTP exceptions or MCP-specific formatting.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty or whitespace-only.")

    embeddings = generate_embeddings([query])
    if not embeddings:
        raise RuntimeError("Failed to generate embedding for search query.")
    
    query_embedding = embeddings[0]

    results_data = await search_document_chunks(
        query_embedding=query_embedding,
        limit=limit,
        filters=filters,
        query_text=query,
    )

    return [DocumentSearchResult(**item) for item in results_data]

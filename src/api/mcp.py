import logging
import secrets
from typing import Annotated, List, Optional
from pydantic import Field

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from src.config import settings
from src.models.schemas import DocumentSearchFilters
from src.services.search_service import perform_semantic_search

logger = logging.getLogger(__name__)

# Parse allowed hosts and origins
allowed_hosts = [h.strip() for h in settings.MCP_ALLOWED_HOSTS.split(",") if h.strip()]
allowed_origins = [
    o.strip() for o in settings.MCP_ALLOWED_ORIGINS.split(",") if o.strip()
]

# Create FastMCP server with stateless HTTP, JSON responses, and configured DNS rebinding allowed lists
mcp = FastMCP(
    "knowledge-base",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    ),
)

if settings.MCP_ENABLED and not settings.MCP_API_KEY:
    logger.warning(
        "SECURITY WARNING: MCP is enabled but MCP_API_KEY is empty. The MCP server is running WITHOUT authentication."
    )


@mcp.tool(
    name="search_knowledge_base",
    description=(
        "Search the processed Knowledge Base for information relevant to a user question. "
        "Use this tool whenever the user asks about uploaded documents, cases, internal documents, "
        "services, clients, industries, capabilities, processes, or project information. "
        "Return grounded document chunks and metadata. Do not invent information when no useful results are found."
    ),
)
async def search_knowledge_base(
    query: Annotated[
        str,
        Field(
            min_length=1,
            description="Question or search query for the Knowledge Base.",
        ),
    ],
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=20,
            description="Maximum number of relevant chunks to return.",
        ),
    ] = 5,
    type: Optional[str] = None,
    client_name: Optional[str] = None,
    industry: Optional[str] = None,
    geography: Optional[str] = None,
    use_case: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Search the Knowledge Base semantically.
    """
    # Reject query if empty or whitespace-only
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty or whitespace-only.")

    # Limit validation bounds check
    if limit < 1 or limit > 20:
        raise ValueError("Limit must be between 1 and 20.")

    filters = DocumentSearchFilters(
        type=type,
        client_name=client_name,
        industry=industry,
        geography=geography,
        use_case=use_case,
        tags=tags or [],
    )

    try:
        results = await perform_semantic_search(
            query=query,
            limit=limit,
            filters=filters,
        )
    except ValueError as e:
        logger.warning(f"Invalid input provided to search_knowledge_base: {e}")
        raise
    except Exception as e:
        logger.error(
            f"Internal failure in search_knowledge_base service: {e}", exc_info=True
        )
        # Technical failures returned as tool error, details logged server-side without leaking internals
        raise RuntimeError("An internal service error occurred. Please try again.")

    # Explicit JSON serialization of response structures
    results_list = []
    for r in results:
        results_list.append(
            {
                "document_id": str(r.document_id),
                "title": r.title,
                "type": r.type,
                "client_name": r.client_name,
                "industry": r.industry,
                "geography": r.geography,
                "use_case": r.use_case,
                "tags": list(r.tags),
                "authors": list(r.authors),
                "source_bucket": r.source_bucket,
                "source_object_key": r.source_object_key,
                "chunk_id": str(r.chunk_id),
                "chunk_index": int(r.chunk_index),
                "content": r.content,
                "score": float(r.score),
            }
        )

    if not results_list:
        return {
            "query": query,
            "result_count": 0,
            "results": [],
            "message": "No relevant processed documents were found.",
        }

    return {"query": query, "result_count": len(results_list), "results": results_list}


class MCPAuthMiddleware:
    """
    Isolated ASGI middleware to enforce Bearer token authentication
    strictly around the mounted MCP application subtree.
    """

    def __init__(self, app, api_key: str):
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")

            authenticated = False
            if not self.api_key:
                authenticated = True
            elif auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                if secrets.compare_digest(token, self.api_key):
                    authenticated = True

            if not authenticated:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"www-authenticate", b"Bearer"),
                            (b"content-type", b"application/json"),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"detail": "Unauthorized: Invalid or missing Bearer token"}',
                        "more_body": False,
                    }
                )
                return

        await self.app(scope, receive, send)

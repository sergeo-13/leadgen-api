from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import documents, health, hermes, ingestion
from src.api import ui
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Explicit startup/shutdown handling for MCP session manager
    if settings.MCP_ENABLED:
        from src.api.mcp import mcp
        async with mcp.session_manager.run():
            yield
    else:
        yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(health.router, tags=["health"])  # Expose /health at root
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(hermes.router, prefix="/api/v1", tags=["hermes"])
app.include_router(ui.router, tags=["ui"])

# Conditionally mount MCP application under isolated /mcp prefix
if settings.MCP_ENABLED:
    from src.api.mcp import mcp, MCPAuthMiddleware
    mcp_asgi_app = mcp.streamable_http_app()
    authenticated_mcp_app = MCPAuthMiddleware(mcp_asgi_app, settings.MCP_API_KEY)
    app.mount("/mcp", authenticated_mcp_app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Leadgen API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

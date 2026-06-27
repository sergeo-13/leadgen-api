from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.sessions import SessionMiddleware

from src.api.v1 import documents, health, hermes, ingestion, info
from src.api import ui, auth, home
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
allowed_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for Entra authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.AUTH_SESSION_SIGNING_SECRET,
    max_age=settings.AUTH_SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=settings.AUTH_SESSION_COOKIE_SECURE
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(health.router, tags=["health"])  # Expose /health at root
app.include_router(info.router, prefix="/api/v1", tags=["info"])
app.include_router(auth.router, tags=["auth"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(hermes.router, prefix="/api/v1", tags=["hermes"])
app.include_router(ui.router, tags=["ui"])
app.include_router(home.router, tags=["home"])

# Conditionally mount MCP application under isolated /mcp prefix
if settings.MCP_ENABLED:
    from src.api.mcp import mcp, MCPAuthMiddleware
    mcp_asgi_app = mcp.streamable_http_app()
    authenticated_mcp_app = MCPAuthMiddleware(mcp_asgi_app, settings.MCP_API_KEY)
    app.mount("/mcp", authenticated_mcp_app)

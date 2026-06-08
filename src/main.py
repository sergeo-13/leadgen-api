"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import health
from src.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Leadgen Bot API",
        "version": settings.APP_VERSION,
        "commit_sha": settings.COMMIT_SHA,
        "docs": "/docs",
    }

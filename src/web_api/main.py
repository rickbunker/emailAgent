"""
FastAPI main application for Inveniam Email Agent.

This module creates and configures the FastAPI application with all routers,
middleware, and lifecycle management.
"""

# # Standard library imports
from contextlib import asynccontextmanager
from pathlib import Path

# # Third-party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger
from src.web_api.dependencies import (
    initialize_services,
    cleanup_services,
    get_templates,
)

# Import routers
from src.web_api.routers import (
    assets,
    health,
    senders,
    ui,
    email_processing,
    human_review,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Inveniam Email Agent API...")
    await initialize_services()
    logger.info("✅ API started successfully")
    yield
    logger.info("Shutting down Inveniam Email Agent API...")
    await cleanup_services()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Inveniam Email Agent API",
    description="Intelligent email processing and asset management system",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for logo and other assets
app.mount("/static", StaticFiles(directory="src/web_api/static"), name="static")

# Templates are handled via dependency injection (get_templates)

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
app.include_router(senders.router, prefix="/api/v1", tags=["senders"])
app.include_router(email_processing.router, prefix="/api/v1", tags=["email_processing"])
app.include_router(human_review.router, prefix="/api/v1", tags=["human_review"])

# Include UI router (for demo frontend)
app.include_router(ui.router, tags=["ui"])


# Root redirect
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Redirect root to UI dashboard."""
    return {"message": "Welcome to Asset Management System", "docs": "/api/docs"}


if __name__ == "__main__":
    uvicorn.run(
        "src.web_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

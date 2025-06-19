"""
Main FastAPI application for Asset Management System.

This module sets up the FastAPI application with all routers,
middleware, and configuration.
"""

# # Standard library imports
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# # Third-party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# # Local application imports
from src.utils.logging_system import get_logger

# Import services setup
from src.web_api.dependencies import cleanup_services, initialize_services

# Import routers
from src.web_api.routers import assets, health, senders, ui

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle.

    Initialize services on startup and cleanup on shutdown.
    """
    # Startup
    logger.info("Starting Asset Management API...")
    await initialize_services()
    logger.info("✅ API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Asset Management API...")
    await cleanup_services()
    logger.info("API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Asset Management API",
    description="API for managing private market investment documents",
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

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Configure templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

# Include API routers
app.include_router(health.router, prefix="/api/v1", tags=["system"])
app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
app.include_router(senders.router, prefix="/api/v1", tags=["senders"])

# Include UI router (for demo frontend)
app.include_router(ui.router, tags=["ui"])


# Root redirect
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Redirect root to UI dashboard."""
    return {"message": "Welcome to Asset Management System", "docs": "/api/docs"}


if __name__ == "__main__":
    # # Third-party imports
    import uvicorn

    uvicorn.run(
        "src.web_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

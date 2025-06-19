"""
Health check and system status endpoints.

This module provides endpoints for monitoring system health
and service availability.
"""

# # Standard library imports
from datetime import datetime
from typing import Any

# # Third-party imports
from fastapi import APIRouter, Depends

# # Local application imports
from src.utils.logging_system import get_logger
from src.web_api.dependencies import get_asset_service, get_qdrant_client

logger = get_logger(__name__)

router = APIRouter(prefix="/system")

# Track startup time
startup_time = datetime.utcnow()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Health status and basic system info
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    asset_service=Depends(get_asset_service),
    qdrant_client=Depends(get_qdrant_client),
) -> dict[str, Any]:
    """
    Detailed health check with service status.

    Returns:
        Detailed health status for all services
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "services": {},
    }

    # Check asset service
    try:
        # Try to list assets (with limit 1 for performance)
        assets = await asset_service.list_assets()
        health_status["services"]["asset_service"] = {
            "status": "healthy",
            "asset_count": len(assets),
        }
    except Exception as e:
        health_status["services"]["asset_service"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    # Check Qdrant
    if qdrant_client:
        try:
            collections = qdrant_client.get_collections()
            health_status["services"]["qdrant"] = {
                "status": "healthy",
                "collections": len(collections.collections),
            }
        except Exception as e:
            health_status["services"]["qdrant"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health_status["status"] = "degraded"
    else:
        health_status["services"]["qdrant"] = {
            "status": "not_configured",
            "message": "Qdrant client not available",
        }

    # Check file system
    try:
        # # Standard library imports
        from pathlib import Path

        # # Local application imports
        from src.utils.config import config

        assets_path = Path(config.assets_base_path)
        if assets_path.exists():
            health_status["services"]["storage"] = {
                "status": "healthy",
                "path": str(assets_path),
                "accessible": True,
            }
        else:
            health_status["services"]["storage"] = {
                "status": "warning",
                "path": str(assets_path),
                "accessible": False,
                "message": "Assets directory does not exist",
            }
    except Exception as e:
        health_status["services"]["storage"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    return health_status


@router.get("/info")
async def system_info() -> dict[str, Any]:
    """
    Get system configuration information.

    Returns:
        System configuration (non-sensitive)
    """
    # # Local application imports
    from src.utils.config import config

    return {
        "version": "1.0.0",
        "environment": getattr(config, "environment", "development"),
        "config": {
            "assets_base_path": str(config.assets_base_path),
            "qdrant_host": config.qdrant_host,
            "qdrant_port": config.qdrant_port,
            "memory_limits": {
                "semantic": getattr(config, "semantic_memory_max_items", 50000),
                "episodic": getattr(config, "episodic_memory_max_items", 100000),
                "procedural": getattr(config, "procedural_memory_max_items", 10000),
                "contact": getattr(config, "contact_memory_max_items", 25000),
            },
        },
        "features": {
            "qdrant_enabled": get_qdrant_client is not None,
            "email_processing": True,
            "human_review": True,
            "memory_system": True,
        },
    }

"""
Asset management endpoints.

This module provides CRUD operations for managing assets.
"""

# # Standard library imports
from typing import Any, Optional

# # Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# # Local application imports
from src.asset_management import Asset, AssetType
from src.asset_management.services.asset_service import AssetService
from src.utils.logging_system import get_logger
from src.web_api.dependencies import get_asset_service

logger = get_logger(__name__)

router = APIRouter(prefix="/assets")


# Pydantic models for request/response


class AssetCreate(BaseModel):
    """Request model for creating an asset."""

    deal_name: str = Field(..., description="Short name for the asset")
    asset_name: str = Field(..., description="Full descriptive name")
    asset_type: AssetType = Field(..., description="Type of private market asset")
    identifiers: list[str] = Field(
        default_factory=list, description="Alternative names/identifiers"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


class AssetUpdate(BaseModel):
    """Request model for updating an asset."""

    deal_name: Optional[str] = Field(None, description="New deal name")
    asset_name: Optional[str] = Field(None, description="New asset name")
    asset_type: Optional[AssetType] = Field(None, description="New asset type")
    identifiers: Optional[list[str]] = Field(None, description="New identifiers")
    metadata: Optional[dict[str, Any]] = Field(None, description="New metadata")


class AssetResponse(BaseModel):
    """Response model for asset data."""

    deal_id: str
    deal_name: str
    asset_name: str
    asset_type: AssetType
    folder_path: str
    identifiers: list[str]
    created_date: str
    last_updated: str
    metadata: Optional[dict[str, Any]]


class AssetListResponse(BaseModel):
    """Response model for asset list."""

    items: list[AssetResponse]
    total: int
    limit: int
    offset: int


class AssetStatsResponse(BaseModel):
    """Response model for asset statistics."""

    total_assets: int
    by_type: dict[str, int]
    recent_assets: list[AssetResponse]


# Helper function to convert Asset to response model
def asset_to_response(asset: Asset) -> AssetResponse:
    """Convert Asset domain model to API response model."""
    return AssetResponse(
        deal_id=asset.deal_id,
        deal_name=asset.deal_name,
        asset_name=asset.asset_name,
        asset_type=asset.asset_type,
        folder_path=asset.folder_path,
        identifiers=asset.identifiers,
        created_date=asset.created_date.isoformat(),
        last_updated=asset.last_updated.isoformat(),
        metadata=asset.metadata,
    )


# API Endpoints


@router.get("/", response_model=AssetListResponse)
async def list_assets(
    asset_service: AssetService = Depends(get_asset_service),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    search: Optional[str] = Query(None, description="Search in names/identifiers"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> AssetListResponse:
    """
    List all assets with optional filtering.

    Args:
        asset_type: Optional filter by asset type
        search: Optional search string for names/identifiers
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        List of assets with pagination info
    """
    try:
        # Get all assets
        all_assets = await asset_service.list_assets()

        # Apply filters
        filtered_assets = all_assets

        if asset_type:
            filtered_assets = [a for a in filtered_assets if a.asset_type == asset_type]

        if search:
            search_lower = search.lower()
            filtered_assets = [
                a
                for a in filtered_assets
                if search_lower in a.deal_name.lower()
                or search_lower in a.asset_name.lower()
                or any(search_lower in ident.lower() for ident in a.identifiers)
            ]

        # Apply pagination
        total = len(filtered_assets)
        paginated_assets = filtered_assets[offset : offset + limit]

        return AssetListResponse(
            items=[asset_to_response(a) for a in paginated_assets],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list assets: {str(e)}")


@router.get("/stats", response_model=AssetStatsResponse)
async def get_asset_stats(
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetStatsResponse:
    """
    Get asset statistics.

    Returns:
        Asset statistics including counts by type and recent assets
    """
    try:
        all_assets = await asset_service.list_assets()

        # Calculate stats
        by_type = {}
        for asset in all_assets:
            asset_type = asset.asset_type.value
            by_type[asset_type] = by_type.get(asset_type, 0) + 1

        # Get recent assets (last 5)
        recent_assets = sorted(all_assets, key=lambda a: a.created_date, reverse=True)[
            :5
        ]

        return AssetStatsResponse(
            total_assets=len(all_assets),
            by_type=by_type,
            recent_assets=[asset_to_response(a) for a in recent_assets],
        )

    except Exception as e:
        logger.error(f"Failed to get asset stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get asset stats: {str(e)}"
        )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    """
    Get a specific asset by ID.

    Args:
        asset_id: The asset's deal_id

    Returns:
        The requested asset

    Raises:
        404: If asset not found
    """
    try:
        asset = await asset_service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

        return asset_to_response(asset)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get asset: {str(e)}")


@router.post("/", response_model=dict[str, Any])
async def create_asset(
    asset_data: AssetCreate,
    asset_service: AssetService = Depends(get_asset_service),
) -> dict[str, Any]:
    """
    Create a new asset.

    Args:
        asset_data: Asset creation data

    Returns:
        Created asset ID and full asset data
    """
    try:
        asset_id = await asset_service.create_asset(
            deal_name=asset_data.deal_name,
            asset_name=asset_data.asset_name,
            asset_type=asset_data.asset_type,
            identifiers=asset_data.identifiers,
            metadata=asset_data.metadata,
        )

        # Get the created asset
        asset = await asset_service.get_asset(asset_id)

        return {
            "asset_id": asset_id,
            "asset": asset_to_response(asset) if asset else None,
            "message": f"Asset created successfully: {asset_data.deal_name}",
        }

    except Exception as e:
        logger.error(f"Failed to create asset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    asset_data: AssetUpdate,
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetResponse:
    """
    Update an existing asset.

    Args:
        asset_id: The asset's deal_id
        asset_data: Fields to update

    Returns:
        Updated asset data

    Raises:
        404: If asset not found
    """
    try:
        # Check if asset exists
        existing_asset = await asset_service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

        # Update asset
        success = await asset_service.update_asset(
            deal_id=asset_id,
            deal_name=asset_data.deal_name,
            asset_name=asset_data.asset_name,
            asset_type=asset_data.asset_type,
            identifiers=asset_data.identifiers,
            metadata=asset_data.metadata,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update asset")

        # Get updated asset
        updated_asset = await asset_service.get_asset(asset_id)
        if not updated_asset:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve updated asset"
            )

        return asset_to_response(updated_asset)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update asset: {str(e)}")


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
    preserve_files: bool = Query(True, description="Preserve asset files on disk"),
) -> dict[str, Any]:
    """
    Delete an asset.

    Args:
        asset_id: The asset's deal_id
        preserve_files: Whether to preserve files on disk (default: True)

    Returns:
        Deletion confirmation

    Raises:
        404: If asset not found
    """
    try:
        # Check if asset exists
        existing_asset = await asset_service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")

        # Delete asset
        success = await asset_service.delete_asset(asset_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete asset")

        return {
            "deleted": True,
            "asset_id": asset_id,
            "message": f"Asset deleted successfully. Files preserved: {preserve_files}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete asset: {str(e)}")

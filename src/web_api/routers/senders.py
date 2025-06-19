"""
Sender mapping management endpoints.

This module provides CRUD operations for managing sender email
to asset mappings.
"""

# # Standard library imports
from typing import Any, Optional

# # Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

# # Local application imports
from src.asset_management import SenderMapping
from src.asset_management.memory_integration.sender_mappings import SenderMappingService
from src.asset_management.services.asset_service import AssetService
from src.utils.logging_system import get_logger
from src.web_api.dependencies import get_asset_service, get_sender_mapping_service

logger = get_logger(__name__)

router = APIRouter(prefix="/senders")


# Pydantic models for request/response


class SenderMappingCreate(BaseModel):
    """Request model for creating a sender mapping."""

    sender_email: EmailStr = Field(..., description="Sender email address")
    default_asset_id: str = Field(..., description="Default asset ID for this sender")
    sender_name: Optional[str] = Field(None, description="Human-readable sender name")
    organization: Optional[str] = Field(None, description="Sender's organization")
    notes: Optional[str] = Field(None, description="Additional notes about the sender")


class SenderMappingUpdate(BaseModel):
    """Request model for updating a sender mapping."""

    default_asset_id: Optional[str] = Field(None, description="New default asset ID")
    sender_name: Optional[str] = Field(None, description="New sender name")
    organization: Optional[str] = Field(None, description="New organization")
    notes: Optional[str] = Field(None, description="New notes")
    active: Optional[bool] = Field(None, description="Active status")


class SenderMappingResponse(BaseModel):
    """Response model for sender mapping data."""

    sender_email: str
    default_asset_id: str
    sender_name: Optional[str]
    organization: Optional[str]
    notes: Optional[str]
    created_date: str
    last_updated: str
    active: bool
    # Include asset details for convenience
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None


class SenderMappingListResponse(BaseModel):
    """Response model for sender mapping list."""

    items: list[SenderMappingResponse]
    total: int
    limit: int
    offset: int


# Helper function to convert SenderMapping to response model
async def sender_mapping_to_response(
    mapping: SenderMapping, asset_service: AssetService
) -> SenderMappingResponse:
    """Convert SenderMapping domain model to API response model."""
    # Get asset details
    asset = await asset_service.get_asset(mapping.default_asset_id)

    return SenderMappingResponse(
        sender_email=mapping.sender_email,
        default_asset_id=mapping.default_asset_id,
        sender_name=mapping.sender_name,
        organization=mapping.organization,
        notes=mapping.notes,
        created_date=mapping.created_date.isoformat(),
        last_updated=mapping.last_updated.isoformat(),
        active=mapping.active,
        asset_name=asset.asset_name if asset else None,
        asset_type=asset.asset_type.value if asset else None,
    )


# API Endpoints


@router.get("/", response_model=SenderMappingListResponse)
async def list_sender_mappings(
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
    search: Optional[str] = Query(
        None, description="Search in email/name/organization"
    ),
    asset_id: Optional[str] = Query(None, description="Filter by asset ID"),
    active_only: bool = Query(True, description="Show only active mappings"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> SenderMappingListResponse:
    """
    List all sender mappings with optional filtering.

    Args:
        search: Optional search string for email/name/organization
        asset_id: Optional filter by asset ID
        active_only: Whether to show only active mappings
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        List of sender mappings with pagination info
    """
    try:
        # Get all mappings
        all_mappings = await sender_service.list_all_mappings()

        # Apply filters
        filtered_mappings = all_mappings

        if active_only:
            filtered_mappings = [m for m in filtered_mappings if m.active]

        if asset_id:
            filtered_mappings = [
                m for m in filtered_mappings if m.default_asset_id == asset_id
            ]

        if search:
            search_lower = search.lower()
            filtered_mappings = [
                m
                for m in filtered_mappings
                if search_lower in m.sender_email.lower()
                or (m.sender_name and search_lower in m.sender_name.lower())
                or (m.organization and search_lower in m.organization.lower())
            ]

        # Apply pagination
        total = len(filtered_mappings)
        paginated_mappings = filtered_mappings[offset : offset + limit]

        # Convert to response models
        response_items = []
        for mapping in paginated_mappings:
            response_items.append(
                await sender_mapping_to_response(mapping, asset_service)
            )

        return SenderMappingListResponse(
            items=response_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list sender mappings: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list sender mappings: {str(e)}"
        )


@router.get("/{sender_email}", response_model=SenderMappingResponse)
async def get_sender_mapping(
    sender_email: str,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> SenderMappingResponse:
    """
    Get a specific sender mapping by email.

    Args:
        sender_email: The sender's email address

    Returns:
        The requested sender mapping

    Raises:
        404: If sender mapping not found
    """
    try:
        mapping = await sender_service.get_mapping(sender_email)
        if not mapping:
            raise HTTPException(
                status_code=404, detail=f"Sender mapping not found: {sender_email}"
            )

        return await sender_mapping_to_response(mapping, asset_service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sender mapping {sender_email}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sender mapping: {str(e)}"
        )


@router.post("/", response_model=dict[str, Any])
async def create_sender_mapping(
    mapping_data: SenderMappingCreate,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> dict[str, Any]:
    """
    Create a new sender mapping.

    Args:
        mapping_data: Sender mapping creation data

    Returns:
        Created sender mapping details
    """
    try:
        # Verify asset exists
        asset = await asset_service.get_asset(mapping_data.default_asset_id)
        if not asset:
            raise HTTPException(
                status_code=400,
                detail=f"Asset not found: {mapping_data.default_asset_id}",
            )

        # Check if mapping already exists
        existing = await sender_service.get_mapping(mapping_data.sender_email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Sender mapping already exists: {mapping_data.sender_email}",
            )

        # Create the mapping
        success = await sender_service.add_mapping(
            sender_email=mapping_data.sender_email,
            default_asset_id=mapping_data.default_asset_id,
            sender_name=mapping_data.sender_name,
            organization=mapping_data.organization,
            notes=mapping_data.notes,
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to create sender mapping"
            )

        # Get the created mapping
        mapping = await sender_service.get_mapping(mapping_data.sender_email)

        return {
            "mapping": (
                await sender_mapping_to_response(mapping, asset_service)
                if mapping
                else None
            ),
            "message": f"Sender mapping created successfully: {mapping_data.sender_email}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create sender mapping: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create sender mapping: {str(e)}"
        )


@router.put("/{sender_email}", response_model=SenderMappingResponse)
async def update_sender_mapping(
    sender_email: str,
    mapping_data: SenderMappingUpdate,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> SenderMappingResponse:
    """
    Update an existing sender mapping.

    Args:
        sender_email: The sender's email address
        mapping_data: Fields to update

    Returns:
        Updated sender mapping data

    Raises:
        404: If sender mapping not found
    """
    try:
        # Check if mapping exists
        existing_mapping = await sender_service.get_mapping(sender_email)
        if not existing_mapping:
            raise HTTPException(
                status_code=404, detail=f"Sender mapping not found: {sender_email}"
            )

        # Verify new asset if provided
        if mapping_data.default_asset_id:
            asset = await asset_service.get_asset(mapping_data.default_asset_id)
            if not asset:
                raise HTTPException(
                    status_code=400,
                    detail=f"Asset not found: {mapping_data.default_asset_id}",
                )

        # Update mapping
        success = await sender_service.update_mapping(
            sender_email=sender_email,
            default_asset_id=mapping_data.default_asset_id,
            sender_name=mapping_data.sender_name,
            organization=mapping_data.organization,
            notes=mapping_data.notes,
            active=mapping_data.active,
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to update sender mapping"
            )

        # Get updated mapping
        updated_mapping = await sender_service.get_mapping(sender_email)
        if not updated_mapping:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve updated sender mapping"
            )

        return await sender_mapping_to_response(updated_mapping, asset_service)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update sender mapping {sender_email}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update sender mapping: {str(e)}"
        )


@router.delete("/{sender_email}")
async def delete_sender_mapping(
    sender_email: str,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
) -> dict[str, Any]:
    """
    Delete a sender mapping.

    Args:
        sender_email: The sender's email address

    Returns:
        Deletion confirmation

    Raises:
        404: If sender mapping not found
    """
    try:
        # Check if mapping exists
        existing_mapping = await sender_service.get_mapping(sender_email)
        if not existing_mapping:
            raise HTTPException(
                status_code=404, detail=f"Sender mapping not found: {sender_email}"
            )

        # Delete mapping
        success = await sender_service.delete_mapping(sender_email)

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete sender mapping"
            )

        return {
            "deleted": True,
            "sender_email": sender_email,
            "message": f"Sender mapping deleted successfully: {sender_email}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete sender mapping {sender_email}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete sender mapping: {str(e)}"
        )


@router.get("/stats/by-asset", response_model=dict[str, Any])
async def get_sender_stats_by_asset(
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> dict[str, Any]:
    """
    Get sender mapping statistics grouped by asset.

    Returns:
        Statistics about sender mappings per asset
    """
    try:
        all_mappings = await sender_service.list_all_mappings()
        active_mappings = [m for m in all_mappings if m.active]

        # Group by asset
        by_asset = {}
        for mapping in active_mappings:
            asset_id = mapping.default_asset_id
            if asset_id not in by_asset:
                by_asset[asset_id] = {
                    "count": 0,
                    "senders": [],
                    "asset_name": None,
                    "asset_type": None,
                }

            by_asset[asset_id]["count"] += 1
            by_asset[asset_id]["senders"].append(
                {
                    "email": mapping.sender_email,
                    "name": mapping.sender_name,
                    "organization": mapping.organization,
                }
            )

        # Add asset details
        for asset_id in by_asset:
            asset = await asset_service.get_asset(asset_id)
            if asset:
                by_asset[asset_id]["asset_name"] = asset.asset_name
                by_asset[asset_id]["asset_type"] = asset.asset_type.value

        return {
            "total_mappings": len(all_mappings),
            "active_mappings": len(active_mappings),
            "by_asset": by_asset,
        }

    except Exception as e:
        logger.error(f"Failed to get sender stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sender stats: {str(e)}"
        )

"""
UI routes for the demo frontend.

This module serves HTML pages using Jinja2 templates with HTMX
for dynamic behavior without a full SPA framework.
"""

# # Standard library imports
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# # Third-party imports
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_404_NOT_FOUND

# # Local application imports
from src.asset_management import AssetType
from src.asset_management.core.data_models import Asset
from src.asset_management.memory_integration.sender_mappings import SenderMappingService
from src.asset_management.services.asset_service import AssetService
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function
from src.web_api.dependencies import (
    get_asset_service,
    get_document_processor,
    get_sender_mapping_service,
    get_templates,
)

logger = get_logger(__name__)

router = APIRouter()

# Configure templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Main dashboard page.

    Shows asset statistics and quick actions.
    """
    try:
        # Get asset stats
        all_assets = await asset_service.list_assets()

        # Calculate stats
        by_type = {}
        for asset in all_assets:
            asset_type = asset.asset_type.value
            by_type[asset_type] = by_type.get(asset_type, 0) + 1

        # Get recent assets
        recent_assets = sorted(all_assets, key=lambda a: a.created_date, reverse=True)[
            :5
        ]

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "total_assets": len(all_assets),
                "by_type": by_type,
                "recent_assets": recent_assets,
            },
        )

    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets", response_class=HTMLResponse)
async def assets_list(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
    asset_type: Optional[str] = None,
    search: Optional[str] = None,
) -> HTMLResponse:
    """
    Assets list page.

    Shows all assets with filtering and search.
    """
    try:
        # Get all assets
        all_assets = await asset_service.list_assets()

        # Apply filters
        filtered_assets = all_assets

        if asset_type and asset_type != "all":
            filtered_assets = [
                a for a in filtered_assets if a.asset_type.value == asset_type
            ]

        if search:
            search_lower = search.lower()
            filtered_assets = [
                a
                for a in filtered_assets
                if search_lower in a.deal_name.lower()
                or search_lower in a.asset_name.lower()
                or any(search_lower in ident.lower() for ident in a.identifiers)
            ]

        # Get asset types for filter dropdown
        asset_types = [t.value for t in AssetType]

        return templates.TemplateResponse(
            "assets.html",
            {
                "request": request,
                "assets": filtered_assets,
                "asset_types": asset_types,
                "selected_type": asset_type,
                "search_query": search,
            },
        )

    except Exception as e:
        logger.error(f"Failed to load assets list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/new", response_class=HTMLResponse)
async def new_asset_form(request: Request) -> HTMLResponse:
    """
    New asset creation form.
    """
    asset_types = [t.value for t in AssetType]

    return templates.TemplateResponse(
        "asset_form.html",
        {
            "request": request,
            "asset_types": asset_types,
            "is_edit": False,
        },
    )


@router.post("/assets/new", response_class=HTMLResponse)
async def create_asset_ui(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
    deal_name: str = Form(...),
    asset_name: str = Form(...),
    asset_type: str = Form(...),
    identifiers: str = Form(""),
) -> HTMLResponse:
    """
    Handle asset creation from form submission.

    Returns an HTMX response for dynamic update.
    """
    try:
        # Parse identifiers - handle both comma and newline separators
        identifier_list = []
        if identifiers:
            # Replace newlines with commas for consistent parsing
            identifiers = identifiers.replace("\n", ",").replace("\r", ",")
            identifier_list = [i.strip() for i in identifiers.split(",") if i.strip()]

        # Create asset
        asset_id = await asset_service.create_asset(
            deal_name=deal_name,
            asset_name=asset_name,
            asset_type=AssetType(asset_type),
            identifiers=identifier_list,
        )

        # Get the created asset
        asset = await asset_service.get_asset(asset_id)

        # Return a success message with HTMX redirect
        return templates.TemplateResponse(
            "partials/asset_created.html",
            {
                "request": request,
                "asset": asset,
                "message": f"Asset '{deal_name}' created successfully!",
            },
        )

    except Exception as e:
        logger.error(f"Failed to create asset: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.get("/assets/{asset_id}", response_class=HTMLResponse)
async def view_asset(
    request: Request,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    View asset details page.
    """
    try:
        asset = await asset_service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        return templates.TemplateResponse(
            "asset_detail.html",
            {
                "request": request,
                "asset": asset,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/{asset_id}/edit", response_class=HTMLResponse)
async def edit_asset_form(
    request: Request,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Edit asset form.
    """
    try:
        asset = await asset_service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset_types = [t.value for t in AssetType]

        return templates.TemplateResponse(
            "asset_form.html",
            {
                "request": request,
                "asset": asset,
                "asset_types": asset_types,
                "is_edit": True,
                "identifiers_str": ", ".join(asset.identifiers),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load edit form for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assets/{asset_id}/edit", response_class=HTMLResponse)
async def update_asset_ui(
    request: Request,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
    deal_name: str = Form(...),
    asset_name: str = Form(...),
    asset_type: str = Form(...),
    identifiers: str = Form(""),
) -> HTMLResponse:
    """
    Handle asset update from form submission.

    Returns an HTMX response for dynamic update.
    """
    try:
        # Parse identifiers - handle both comma and newline separators
        identifier_list = []
        if identifiers:
            # Replace newlines with commas for consistent parsing
            identifiers = identifiers.replace("\n", ",").replace("\r", ",")
            identifier_list = [i.strip() for i in identifiers.split(",") if i.strip()]

        # Update asset
        success = await asset_service.update_asset(
            deal_id=asset_id,
            deal_name=deal_name,
            asset_name=asset_name,
            asset_type=AssetType(asset_type),
            identifiers=identifier_list,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update asset")

        # Get the updated asset
        asset = await asset_service.get_asset(asset_id)

        # Return a success message with HTMX redirect
        return templates.TemplateResponse(
            "partials/asset_updated.html",
            {
                "request": request,
                "asset": asset,
                "message": f"Asset '{deal_name}' updated successfully!",
            },
        )

    except Exception as e:
        logger.error(f"Failed to update asset: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.delete("/assets/{asset_id}", response_class=HTMLResponse)
async def delete_asset_ui(
    request: Request,
    asset_id: str,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Handle asset deletion via HTMX.

    Returns empty response to remove the asset row.
    """
    try:
        success = await asset_service.delete_asset(asset_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete asset")

        # Return empty response - HTMX will remove the element
        return HTMLResponse("")

    except Exception as e:
        logger.error(f"Failed to delete asset {asset_id}: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.get("/health", response_class=HTMLResponse)
async def health_check_ui(request: Request) -> HTMLResponse:
    """
    Health check UI page.

    Shows system status with a nice UI.
    """
    # # Third-party imports
    import aiohttp

    # Get health data from API
    health_data = {}
    detailed_health = {}
    system_info = {}

    try:
        async with aiohttp.ClientSession() as session:
            # Basic health
            async with session.get(
                "http://localhost:8000/api/v1/system/health"
            ) as resp:
                if resp.status == 200:
                    health_data = await resp.json()

            # Detailed health
            async with session.get(
                "http://localhost:8000/api/v1/system/health/detailed"
            ) as resp:
                if resp.status == 200:
                    detailed_health = await resp.json()

            # System info
            async with session.get("http://localhost:8000/api/v1/system/info") as resp:
                if resp.status == 200:
                    system_info = await resp.json()

    except Exception as e:
        logger.error(f"Failed to fetch health data: {e}")

    return templates.TemplateResponse(
        "health.html",
        {
            "request": request,
            "health": health_data,
            "detailed": detailed_health,
            "info": system_info,
        },
    )


# Sender Mapping UI Routes


@router.get("/senders", response_class=HTMLResponse)
async def senders_list(
    request: Request,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
    search: Optional[str] = None,
    asset_id: Optional[str] = None,
) -> HTMLResponse:
    """
    Sender mappings list page.

    Shows all sender mappings with filtering.
    """
    try:
        # Get all mappings and assets
        all_mappings, total_count = await sender_service.list_all_mappings()
        all_assets = await asset_service.list_assets()

        # Apply filters
        filtered_mappings = all_mappings

        if asset_id and asset_id != "all":
            filtered_mappings = [m for m in filtered_mappings if m.asset_id == asset_id]

        if search:
            search_lower = search.lower()
            filtered_mappings = [
                m
                for m in filtered_mappings
                if search_lower in m.sender_email.lower()
                or (
                    m.metadata
                    and "organization" in m.metadata
                    and m.metadata["organization"]
                    and search_lower in m.metadata["organization"].lower()
                )
            ]

        # Create asset lookup for efficiency
        asset_lookup = {a.deal_id: a for a in all_assets}

        # Enhance mappings with asset info
        enhanced_mappings = []
        for mapping in filtered_mappings:
            asset = asset_lookup.get(mapping.asset_id)
            enhanced_mappings.append(
                {
                    "mapping": mapping,
                    "asset": asset,
                }
            )

        return templates.TemplateResponse(
            "senders.html",
            {
                "request": request,
                "mappings": enhanced_mappings,
                "assets": all_assets,
                "selected_asset": asset_id,
                "search_query": search,
            },
        )

    except Exception as e:
        logger.error(f"Failed to load sender mappings list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/senders/new", response_class=HTMLResponse)
async def new_sender_mapping_form(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    New sender mapping creation form.
    """
    try:
        # Get all assets for dropdown
        assets = await asset_service.list_assets()

        return templates.TemplateResponse(
            "sender_form.html",
            {
                "request": request,
                "assets": assets,
                "is_edit": False,
            },
        )

    except Exception as e:
        logger.error(f"Failed to load sender form: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/senders/new", response_class=HTMLResponse)
async def create_sender_mapping_ui(
    request: Request,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
    sender_email: str = Form(...),
    default_asset_id: str = Form(...),
    sender_name: str = Form(""),
    organization: str = Form(""),
    notes: str = Form(""),
) -> HTMLResponse:
    """
    Handle sender mapping creation from form submission.
    """
    try:
        # Create sender mapping
        mapping = await sender_service.create_mapping(
            sender_email=sender_email,
            asset_id=default_asset_id,
            organization=organization or None,
            notes=notes or None,
        )

        # Get the asset details
        asset = await asset_service.get_asset(default_asset_id)

        # Return a success message with HTMX redirect
        return templates.TemplateResponse(
            "partials/sender_created.html",
            {
                "request": request,
                "mapping": mapping,
                "asset": asset,
                "message": f"Sender mapping for '{sender_email}' created successfully!",
            },
        )

    except Exception as e:
        logger.error(f"Failed to create sender mapping: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.get("/senders/{mapping_id}/edit", response_class=HTMLResponse)
async def edit_sender_mapping_form(
    request: Request,
    mapping_id: str,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Edit sender mapping form.
    """
    try:
        mapping = await sender_service.get_mapping(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Sender mapping not found")

        assets = await asset_service.list_assets()

        return templates.TemplateResponse(
            "sender_form.html",
            {
                "request": request,
                "mapping": mapping,
                "assets": assets,
                "is_edit": True,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load edit form for mapping {mapping_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/senders/{mapping_id}/edit", response_class=HTMLResponse)
async def update_sender_mapping_ui(
    request: Request,
    mapping_id: str,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
    asset_service: AssetService = Depends(get_asset_service),
    default_asset_id: str = Form(...),
    sender_name: str = Form(""),
    organization: str = Form(""),
    notes: str = Form(""),
    active: bool = Form(True),
) -> HTMLResponse:
    """
    Handle sender mapping update from form submission.
    """
    try:
        # Update sender mapping
        mapping = await sender_service.update_mapping(
            mapping_id=mapping_id,
            asset_id=default_asset_id,
            organization=organization or None,
            notes=notes or None,
        )

        if not mapping:
            raise HTTPException(
                status_code=500, detail="Failed to update sender mapping"
            )

        # Get the asset
        asset = await asset_service.get_asset(mapping.asset_id)

        # Return a success message with HTMX redirect
        return templates.TemplateResponse(
            "partials/sender_updated.html",
            {
                "request": request,
                "mapping": mapping,
                "asset": asset,
                "message": f"Sender mapping for '{mapping.sender_email}' updated successfully!",
            },
        )

    except Exception as e:
        logger.error(f"Failed to update sender mapping: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.delete("/senders/{mapping_id}", response_class=HTMLResponse)
async def delete_sender_mapping_ui(
    request: Request,
    mapping_id: str,
    sender_service: SenderMappingService = Depends(get_sender_mapping_service),
) -> HTMLResponse:
    """
    Handle sender mapping deletion via HTMX.
    """
    try:
        success = await sender_service.delete_mapping(mapping_id)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to delete sender mapping"
            )

        # Return empty response - HTMX will remove the element
        return HTMLResponse("")

    except Exception as e:
        logger.error(f"Failed to delete sender mapping {mapping_id}: {e}")
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": str(e),
            },
        )


@router.get("/email-processing", response_class=HTMLResponse)
async def email_processing_ui(
    request: Request,
) -> HTMLResponse:
    """
    Email processing UI page.
    """
    # Get configured mailboxes from config
    mailboxes = []

    # Check for Gmail configuration
    if (
        hasattr(config, "gmail_credentials_path")
        and Path(config.gmail_credentials_path).exists()
    ):
        mailboxes.append(
            {
                "id": "gmail",
                "name": "Gmail",
                "type": "gmail",
                "icon": "bi-envelope-fill",
            }
        )

    # Check for Microsoft Graph configuration
    if (
        hasattr(config, "msgraph_credentials_path")
        and Path(config.msgraph_credentials_path).exists()
    ):
        mailboxes.append(
            {
                "id": "msgraph",
                "name": "Microsoft 365",
                "type": "microsoft_graph",
                "icon": "bi-microsoft",
            }
        )

    # Fetch recent processing runs from persistent storage
    recent_runs = []
    total_runs = 0

    try:
        # Import the persistent storage functions from email_processing router
        from src.web_api.routers.email_processing import _get_processing_runs

        # Get runs from persistent storage
        all_runs = await _get_processing_runs(limit=20)
        recent_runs = all_runs[:10]  # Show last 10 runs
        total_runs = len(all_runs)
    except Exception as e:
        logger.warning(f"Failed to fetch recent processing runs: {e}")
        # Continue with empty runs - page will still work

    return templates.TemplateResponse(
        "email_processing.html",
        {
            "request": request,
            "mailboxes": mailboxes,
            "recent_runs": recent_runs,
            "total_runs": total_runs,
        },
    )


@router.get("/human-review", response_class=HTMLResponse)
async def human_review_ui(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Human review queue UI page.
    """
    # Get available assets for dropdowns
    assets = await asset_service.list_assets()

    return templates.TemplateResponse(
        "human_review.html",
        {
            "request": request,
            "pending_items": [],  # Will be populated dynamically via API
            "assets": assets,
            "stats": {
                "total_items": 0,
                "pending": 0,
                "completed": 0,
                "in_review": 0,
                "completion_rate": 0,
            },
        },
    )


@router.get("/classification-inspector", response_class=HTMLResponse)
@log_function()
async def classification_inspector_list(request: Request) -> HTMLResponse:
    """
    Show list of processed files for classification inspection.

    Returns:
        HTML response with file browser for classification inspection
    """
    try:
        processed_files = []
        processed_dir = Path(config.processed_attachments_path)

        if processed_dir.exists():
            # Walk through asset folders to find processed files
            for asset_dir in processed_dir.iterdir():
                if asset_dir.is_dir():
                    for category_dir in asset_dir.iterdir():
                        if category_dir.is_dir():
                            for file_path in category_dir.iterdir():
                                if (
                                    file_path.is_file()
                                    and not file_path.name.startswith(".")
                                ):
                                    processed_files.append(
                                        {
                                            "filename": file_path.name,
                                            "asset_folder": asset_dir.name,
                                            "category": category_dir.name,
                                            "relative_path": str(
                                                file_path.relative_to(processed_dir)
                                            ),
                                            "full_path": str(file_path),
                                            "size": file_path.stat().st_size,
                                            "modified": file_path.stat().st_mtime,
                                        }
                                    )

        # Sort by modification time (most recent first)
        processed_files.sort(key=lambda x: x["modified"], reverse=True)

        return templates.TemplateResponse(
            "classification_inspector_list.html",
            {
                "request": request,
                "files": processed_files,
                "total_files": len(processed_files),
            },
        )

    except Exception as e:
        logger.error(f"Failed to load classification inspector list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classification-inspector/{file_path:path}", response_class=HTMLResponse)
@log_function()
async def inspect_classification(request: Request, file_path: str) -> HTMLResponse:
    """
    Inspect the classification reasoning for a specific processed file.

    Args:
        file_path: Relative path to the processed file

    Returns:
        HTML response with detailed classification reasoning
    """
    try:
        # Get full file path
        full_file_path = Path(config.processed_attachments_path) / file_path

        if not full_file_path.exists():
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=f"File not found: {file_path}"
            )

        # Extract file info
        file_info = {
            "filename": full_file_path.name,
            "relative_path": file_path,
            "full_path": str(full_file_path),
            "size": full_file_path.stat().st_size,
            "modified": full_file_path.stat().st_mtime,
            "asset_folder": full_file_path.parent.parent.name,
            "category": full_file_path.parent.name,
        }

        # Try to find corresponding processing metadata in semantic memory
        semantic_memory = SemanticMemory()
        episodic_memory = EpisodicMemory()

        classification_info = None
        processing_metadata = None

        # Search for processing information by filename
        search_results = await semantic_memory.search(
            query=f"processed_file:{full_file_path.name}", limit=5
        )

        # Also search episodic memory for processing decisions
        decision_results = await episodic_memory.search(
            query=f"filename:{full_file_path.name}", limit=5
        )

        # Try to reconstruct processing information
        if search_results:
            for memory_item, score in search_results:
                if score > 0.7:  # High confidence match
                    metadata = memory_item.metadata or {}
                    if "processing_result" in metadata or "classification" in metadata:
                        processing_metadata = {
                            "source": "semantic_memory",
                            "confidence": score,
                            "content": memory_item.content,
                            "metadata": metadata,
                        }
                        break

        # Build classification info from available data
        if processing_metadata or decision_results:
            classification_info = await _build_classification_info(
                file_info,
                processing_metadata,
                decision_results,
                semantic_memory,
                episodic_memory,
            )

        return templates.TemplateResponse(
            "classification_inspector.html",
            {
                "request": request,
                "file_info": file_info,
                "classification_info": classification_info,
                "processing_metadata": processing_metadata,
                "has_metadata": processing_metadata is not None
                or bool(decision_results),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to inspect classification for {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@log_function()
async def _build_classification_info(
    file_info: Dict[str, Any],
    processing_metadata: Optional[Dict[str, Any]],
    decision_results: List[tuple],
    semantic_memory: SemanticMemory,
    episodic_memory: EpisodicMemory,
) -> Dict[str, Any]:
    """
    Build comprehensive classification information from available sources.

    This function reconstructs the two-step processing workflow (asset identification
    and document categorization) from available memory sources, following the
    Email Agent's architecture where semantic memory captures human feedback
    in two distinct parts: asset matching feedback and document type feedback.

    Args:
        file_info: Basic file information including filename, paths, and folder structure
        processing_metadata: Metadata from semantic memory searches
        decision_results: Results from episodic memory searches
        semantic_memory: Semantic memory instance for additional lookups
        episodic_memory: Episodic memory instance for decision history

    Returns:
        Dictionary with comprehensive classification reasoning including:
        - Two-step processing breakdown (asset identification + categorization)
        - Memory source contributions (semantic, episodic, procedural, contact)
        - Confidence levels and decision flow
        - Human feedback integration paths

    Raises:
        ProcessingError: If classification info cannot be built
    """
    try:
        logger.info(f"Building classification info for: {file_info['filename']}")

        classification_info = {
            "filename": file_info["filename"],
            "asset_folder": file_info["asset_folder"],
            "category": file_info["category"],
            "confidence": 0.0,
            "confidence_level": "unknown",
            "processing_source": "file_location",
            "decision_flow": [],
            "step1_asset_identification": {
                "final_asset": file_info["asset_folder"],
                "confidence": None,
                "method": "inferred_from_location",
                "reasoning": [],
            },
            "step2_document_categorization": {
                "final_category": file_info["category"],
                "confidence": None,
                "method": "inferred_from_location",
                "reasoning": [],
            },
            "memory_sources": {
                "semantic": [],
                "episodic": [],
                "procedural": [],
                "contact": [],
            },
            "reasoning_summary": "",
        }

        # Extract info from file location (two-step process breakdown)
        classification_info["step1_asset_identification"]["reasoning"].append(
            f"Asset inferred from folder structure: {file_info['asset_folder']}"
        )
        classification_info["step2_document_categorization"]["reasoning"].append(
            f"Category inferred from folder structure: {file_info['category']}"
        )

        # Combined decision flow for legacy view
        classification_info["decision_flow"].append(
            f"Step 1 - Asset Identification: {file_info['asset_folder']} (inferred from location)"
        )
        classification_info["decision_flow"].append(
            f"Step 2 - Document Categorization: {file_info['category']} (inferred from location)"
        )

        # Add processing metadata if available
        if processing_metadata:
            metadata = processing_metadata.get("metadata", {})
            classification_info["confidence"] = processing_metadata.get(
                "confidence", 0.0
            )
            classification_info["processing_source"] = processing_metadata.get(
                "source", "unknown"
            )

            if "asset_confidence" in metadata:
                classification_info["asset_confidence"] = metadata["asset_confidence"]
                classification_info["step1_asset_identification"]["confidence"] = (
                    metadata["asset_confidence"]
                )
                classification_info["step1_asset_identification"][
                    "method"
                ] = "memory_based"
                classification_info["decision_flow"].append(
                    f"Asset identification confidence: {metadata['asset_confidence']:.2f}"
                )

            if "document_category" in metadata:
                classification_info["document_category"] = metadata["document_category"]
                classification_info["step2_document_categorization"]["confidence"] = (
                    classification_info["confidence"]
                )
                classification_info["step2_document_categorization"][
                    "method"
                ] = "memory_based"
                classification_info["decision_flow"].append(
                    f"Document classified as: {metadata['document_category']}"
                )

        # Add episodic memory information
        for memory_item, score in decision_results:
            if score > 0.6:
                classification_info["memory_sources"]["episodic"].append(
                    {
                        "content": memory_item.content,
                        "confidence": score,
                        "metadata": memory_item.metadata or {},
                    }
                )
                classification_info["decision_flow"].append(
                    f"Episodic memory match (confidence: {score:.2f}): {memory_item.content[:100]}..."
                )

        # Determine confidence level
        avg_confidence = classification_info.get("confidence", 0.0)
        if avg_confidence >= 0.8:
            classification_info["confidence_level"] = "high"
        elif avg_confidence >= 0.6:
            classification_info["confidence_level"] = "medium"
        elif avg_confidence >= 0.4:
            classification_info["confidence_level"] = "low"
        else:
            classification_info["confidence_level"] = "very_low"

        # Build reasoning summary
        if classification_info["decision_flow"]:
            classification_info["reasoning_summary"] = (
                f"File processed through {len(classification_info['decision_flow'])} decision steps. "
                f"Primary evidence from {classification_info['processing_source']}. "
                f"Overall confidence: {classification_info['confidence_level']}"
            )
        else:
            classification_info["reasoning_summary"] = (
                f"File classification inferred from folder structure. "
                f"No detailed processing metadata available."
            )

        logger.info(
            f"Successfully built classification info for: {file_info['filename']}"
        )
        return classification_info

    except KeyError as e:
        logger.error(f"Missing required file info key: {e}")
        # Return minimal classification info with error indication
        return {
            "filename": file_info.get("filename", "unknown"),
            "asset_folder": file_info.get("asset_folder", "unknown"),
            "category": file_info.get("category", "unknown"),
            "confidence": 0.0,
            "confidence_level": "error",
            "processing_source": "error",
            "decision_flow": [f"Error building classification info: {str(e)}"],
            "step1_asset_identification": {
                "final_asset": "error",
                "confidence": None,
                "method": "error",
                "reasoning": [f"Error: {str(e)}"],
            },
            "step2_document_categorization": {
                "final_category": "error",
                "confidence": None,
                "method": "error",
                "reasoning": [f"Error: {str(e)}"],
            },
            "memory_sources": {
                "semantic": [],
                "episodic": [],
                "procedural": [],
                "contact": [],
            },
            "reasoning_summary": f"Error building classification info: {str(e)}",
        }
    except Exception as e:
        logger.error(
            f"Unexpected error building classification info for {file_info.get('filename', 'unknown')}: {e}"
        )
        # Return minimal classification info with error indication
        return {
            "filename": file_info.get("filename", "unknown"),
            "asset_folder": file_info.get("asset_folder", "unknown"),
            "category": file_info.get("category", "unknown"),
            "confidence": 0.0,
            "confidence_level": "error",
            "processing_source": "error",
            "decision_flow": [f"Unexpected error: {str(e)}"],
            "step1_asset_identification": {
                "final_asset": "error",
                "confidence": None,
                "method": "error",
                "reasoning": [f"Error: {str(e)}"],
            },
            "step2_document_categorization": {
                "final_category": "error",
                "confidence": None,
                "method": "error",
                "reasoning": [f"Error: {str(e)}"],
            },
            "memory_sources": {
                "semantic": [],
                "episodic": [],
                "procedural": [],
                "contact": [],
            },
            "reasoning_summary": f"Unexpected error building classification info: {str(e)}",
        }

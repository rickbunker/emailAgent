"""
Memory management router for Email Agent Web API.

Provides comprehensive memory system management including:
- Memory dashboard with all 4 memory types
- Individual memory operations (view, delete, clear)
- Knowledge base loading and management
- Asset loading from JSON into memory systems
- Memory monitoring and cleanup operations

Implements requirements from WEB_UI_FEATURE_REQUIREMENTS.md Section 7: Memory System Dashboards
"""

# # Standard library imports
import json
from pathlib import Path
from typing import Any

# # Third-party imports
from fastapi import APIRouter, Body, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...utils.config import PROJECT_ROOT, config
from ...utils.logging_system import get_logger, log_function
from ..dependencies import get_memory_systems

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

# Configure templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


@router.get("/", response_class=HTMLResponse)
@log_function()
async def memory_dashboard(request: Request):
    """
    Memory system dashboard showing all 4 memory types.

    WEB_UI_FEATURE_REQUIREMENTS.md Section 7.1: Memory Overview
    """
    try:
        memory_systems = get_memory_systems()

        # Get memory statistics for all systems
        memory_stats = {}
        total_items = 0
        total_max_items = 0

        for memory_type, memory_system in memory_systems.items():
            try:
                # ProceduralMemory has different API and multiple collections
                if memory_type == "procedural":
                    # Get stats from all procedural collections
                    procedural_stats = await get_procedural_memory_stats(memory_system)

                    # Add each procedural collection as a separate entry
                    for collection_name, collection_stats in procedural_stats.items():
                        display_name = f"procedural_{collection_name}"
                        memory_stats[display_name] = collection_stats
                        total_items += collection_stats["current_items"]
                        total_max_items += collection_stats["max_items"]
                else:
                    collection_info = await memory_system.get_collection_info()
                    current_items = collection_info.get("points_count", 0)

                    max_items = getattr(
                        config, f"{memory_type}_memory_max_items", 10000
                    )
                    usage_percentage = (
                        (current_items / max_items) * 100 if max_items > 0 else 0
                    )
                    estimated_size_mb = (current_items * 2048) / (1024 * 1024)

                    memory_stats[memory_type] = {
                        "current_items": current_items,
                        "max_items": max_items,
                        "usage_percentage": usage_percentage,
                        "estimated_size_mb": estimated_size_mb,
                        "collection_info": collection_info,
                    }

                    total_items += current_items
                    total_max_items += max_items

            except Exception as e:
                logger.error(f"Failed to get stats for {memory_type}: {e}")
                memory_stats[memory_type] = {
                    "current_items": 0,
                    "max_items": 0,
                    "usage_percentage": 0,
                    "estimated_size_mb": 0,
                    "error": str(e),
                }

        # Get system resource information
        system_info = config.get_system_resource_info()

        context = {
            "memory_stats": memory_stats,
            "total_items": total_items,
            "total_max_items": total_max_items,
            "total_usage_percentage": (
                (total_items / total_max_items * 100) if total_max_items > 0 else 0
            ),
            "system_info": system_info,
        }

        return templates.TemplateResponse(
            "memory_dashboard.html", {"request": request, **context}
        )

    except Exception as e:
        logger.error(f"Memory dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load memory dashboard: {str(e)}",
        )


@router.get("/api/stats")
@log_function()
async def get_memory_stats() -> dict[str, Any]:
    """
    Get memory statistics for all memory systems.

    Returns:
        Memory statistics and system resource information
    """
    try:
        memory_systems = get_memory_systems()
        stats = {}

        for memory_type, memory_system in memory_systems.items():
            # ProceduralMemory has different API than other memory systems
            if memory_type == "procedural":
                # Get stats from all procedural collections
                procedural_stats = await get_procedural_memory_stats(memory_system)

                # Add each procedural collection as a separate entry
                for collection_name, collection_stats in procedural_stats.items():
                    display_name = f"procedural_{collection_name}"
                    stats[display_name] = collection_stats
            else:
                collection_info = await memory_system.get_collection_info()
                current_items = collection_info.get("points_count", 0)

                max_items = getattr(config, f"{memory_type}_memory_max_items", 10000)
                usage_percentage = (
                    (current_items / max_items) * 100 if max_items > 0 else 0
                )

                stats[memory_type] = {
                    "current_items": current_items,
                    "max_items": max_items,
                    "usage_percentage": usage_percentage,
                    "estimated_size_mb": (current_items * 2048) / (1024 * 1024),
                    "collection_info": collection_info,
                }

        system_info = config.get_system_resource_info()

        return {
            "memory_stats": stats,
            "system_info": system_info,
        }

    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory statistics: {str(e)}",
        )


@router.get("/{memory_type}")
@log_function()
async def view_memory_type(
    request: Request, memory_type: str, response_class=HTMLResponse
):
    """
    View individual memory system details.

    WEB_UI_FEATURE_REQUIREMENTS.md Section 7.2: Individual Memory Views

    Args:
        memory_type: Type of memory (semantic, episodic, procedural, contact, or procedural subtypes)
    """
    valid_memory_types = [
        "semantic",
        "episodic",
        "procedural",
        "contact",
        "procedural_classification",
        "procedural_asset",
        "procedural_configuration",
        "procedural_confidence",
    ]

    if memory_type not in valid_memory_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory type: {memory_type}",
        )

    try:
        memory_systems = get_memory_systems()

        # Handle procedural subtypes by using the main procedural memory system
        if memory_type.startswith("procedural_"):
            base_memory_type = "procedural"
            procedural_subtype = memory_type.replace("procedural_", "")
        else:
            base_memory_type = memory_type
            procedural_subtype = None

        if base_memory_type not in memory_systems:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory system not found: {base_memory_type}",
            )

        memory_system = memory_systems[base_memory_type]

        # Get detailed collection information
        if memory_type == "procedural" or memory_type.startswith("procedural_"):
            if procedural_subtype:
                # For procedural subtypes, get specific collection stats
                current_items = await get_procedural_subtype_stats(
                    memory_system, procedural_subtype
                )
                collection_info = {
                    "current_items": current_items,
                    "subtype": procedural_subtype,
                }
            else:
                # For general procedural, get total patterns from all collections
                collection_info = await memory_system.get_pattern_stats()
                current_items = collection_info.get("total_patterns", 0)
        else:
            collection_info = await memory_system.get_collection_info()
            current_items = collection_info.get("points_count", 0)

        max_items = getattr(config, f"{memory_type}_memory_max_items", 10000)

        # Get sample items from the memory system
        sample_items = []
        try:
            # Use different search approaches based on memory type
            if memory_type == "procedural" or memory_type.startswith("procedural_"):
                # For procedural memory, get items directly from Qdrant collection
                if procedural_subtype:
                    sample_items = await get_procedural_sample_items(
                        memory_system, procedural_subtype
                    )
                else:
                    logger.debug("Skipping sample items for general procedural memory")
            else:
                # For other memory types, search with a general query
                search_results = await memory_system.search("data", limit=20)

                for result in search_results[:20]:
                    # Handle both tuple format (BaseMemory) and item format (SemanticMemory)
                    if isinstance(result, tuple):
                        item, score = result
                    else:
                        item, score = (
                            result,
                            1.0,
                        )  # Default score for items without score

                    sample_items.append(
                        {
                            "id": getattr(item, "id", "N/A"),
                            "content": (
                                getattr(item, "content", "N/A")[:200] + "..."
                                if len(getattr(item, "content", "")) > 200
                                else getattr(item, "content", "N/A")
                            ),
                            "metadata": getattr(item, "metadata", {}),
                            "created_at": getattr(item, "created_at", "N/A"),
                            "last_accessed": getattr(item, "last_accessed", "N/A"),
                            "score": score,
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to get sample items from {memory_type}: {e}")

        context = {
            "memory_type": memory_type,
            "memory_type_title": get_memory_type_title(memory_type),
            "current_items": current_items,
            "max_items": max_items,
            "usage_percentage": (
                (current_items / max_items * 100) if max_items > 0 else 0
            ),
            "collection_info": collection_info,
            "sample_items": sample_items,
            "description": get_memory_type_description(memory_type),
        }

        return templates.TemplateResponse(
            "memory_type_detail.html", {"request": request, **context}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to view {memory_type} memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to view {memory_type} memory: {str(e)}",
        )


@router.post("/{memory_type}/clear")
@log_function()
async def clear_memory_type(memory_type: str) -> dict[str, Any]:
    """
    Clear all items from a specific memory type.

    WEB_UI_FEATURE_REQUIREMENTS.md Section 7.3: Memory Operations

    Args:
        memory_type: Type of memory to clear
    """
    valid_memory_types = [
        "semantic",
        "episodic",
        "procedural",
        "contact",
        "procedural_classification",
        "procedural_asset",
        "procedural_configuration",
        "procedural_confidence",
    ]

    if memory_type not in valid_memory_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory type: {memory_type}",
        )

    try:
        memory_systems = get_memory_systems()

        # Handle procedural subtypes by using the main procedural memory system
        if memory_type.startswith("procedural_"):
            base_memory_type = "procedural"
            procedural_subtype = memory_type.replace("procedural_", "")
        else:
            base_memory_type = memory_type
            procedural_subtype = None

        if base_memory_type not in memory_systems:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory system not found: {base_memory_type}",
            )

        memory_system = memory_systems[base_memory_type]

        # Get count before clearing
        if memory_type == "procedural" or memory_type.startswith("procedural_"):
            if procedural_subtype:
                # For procedural subtypes, get specific collection stats
                items_before = await get_procedural_subtype_stats(
                    memory_system, procedural_subtype
                )
            else:
                # For general procedural, get total patterns from all collections
                collection_info = await memory_system.get_pattern_stats()
                items_before = collection_info.get("total_patterns", 0)
        else:
            collection_info = await memory_system.get_collection_info()
            items_before = collection_info.get("points_count", 0)

        # Clear the memory system
        if memory_type == "procedural" or memory_type.startswith("procedural_"):
            # ProceduralMemory doesn't have a clear method implemented yet
            logger.warning(f"Clearing not implemented for {memory_type} memory")
            items_after = items_before
        else:
            await memory_system.clear()
            # Verify clearing
            collection_info_after = await memory_system.get_collection_info()
            items_after = collection_info_after.get("points_count", 0)

        logger.info(
            f"Cleared {memory_type} memory: {items_before} -> {items_after} items"
        )

        return {
            "success": True,
            "memory_type": memory_type,
            "items_before": items_before,
            "items_after": items_after,
            "items_cleared": items_before - items_after,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear {memory_type} memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear {memory_type} memory: {str(e)}",
        )


@router.get("/api/knowledge-base")
@log_function()
async def list_knowledge_files() -> dict[str, Any]:
    """
    List available knowledge base files.

    WEB_UI_FEATURE_REQUIREMENTS.md Section 8.1: Knowledge Base Viewer

    Returns:
        List of knowledge files with metadata
    """
    try:
        knowledge_path = Path(PROJECT_ROOT) / "knowledge"

        if not knowledge_path.exists():
            return {"files": []}

        files = []
        for json_file in knowledge_path.glob("*.json"):
            try:
                stat = json_file.stat()
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                files.append(
                    {
                        "name": json_file.name,
                        "path": str(json_file.relative_to(PROJECT_ROOT)),
                        "size_bytes": stat.st_size,
                        "modified": stat.st_mtime,
                        "item_count": (
                            len(data) if isinstance(data, (list, dict)) else 0
                        ),
                        "type": type(data).__name__,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to read knowledge file {json_file.name}: {e}")
                files.append(
                    {
                        "name": json_file.name,
                        "path": str(json_file.relative_to(PROJECT_ROOT)),
                        "size_bytes": 0,
                        "modified": 0,
                        "item_count": 0,
                        "type": "error",
                        "error": str(e),
                    }
                )

        return {
            "files": sorted(files, key=lambda x: x["name"]),
            "total_files": len(files),
            "knowledge_path": str(knowledge_path),
        }

    except Exception as e:
        logger.error(f"Failed to list knowledge files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list knowledge files: {str(e)}",
        )


@router.post("/api/load-knowledge")
@log_function()
async def load_knowledge_into_memory(
    files: list[str] = Body(..., description="List of knowledge file names to load")
) -> dict[str, Any]:
    """
    Load knowledge base files into memory systems.

    This is the asset loading from JSON functionality requested by the user.

    Args:
        files: List of knowledge file names to load

    Returns:
        Loading results with success/failure details
    """
    try:
        knowledge_path = Path(PROJECT_ROOT) / "knowledge"
        memory_systems = get_memory_systems()

        results = {
            "success": True,
            "files_processed": [],
            "total_items_loaded": 0,
            "errors": [],
        }

        for filename in files:
            file_result = {
                "filename": filename,
                "items_loaded": 0,
                "memory_system": None,
                "success": False,
                "error": None,
            }

            try:
                file_path = knowledge_path / filename

                if not file_path.exists():
                    file_result["error"] = f"File not found: {filename}"
                    results["errors"].append(file_result)
                    continue

                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Determine which memory system to load into based on filename
                target_memory = determine_target_memory_system(filename)
                file_result["memory_system"] = target_memory

                if target_memory not in memory_systems:
                    file_result[
                        "error"
                    ] = f"Memory system not available: {target_memory}"
                    results["errors"].append(file_result)
                    continue

                memory_system = memory_systems[target_memory]

                # Load data into memory system
                items_loaded = await load_data_into_memory(
                    memory_system, data, filename
                )

                file_result["items_loaded"] = items_loaded
                file_result["success"] = True
                results["total_items_loaded"] += items_loaded

                logger.info(
                    f"Loaded {items_loaded} items from {filename} into {target_memory} memory"
                )

            except Exception as e:
                file_result["error"] = str(e)
                results["errors"].append(file_result)
                logger.error(f"Failed to load {filename}: {e}")

            results["files_processed"].append(file_result)

        # Set overall success based on whether any errors occurred
        results["success"] = len(results["errors"]) == 0

        return results

    except Exception as e:
        logger.error(f"Failed to load knowledge into memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load knowledge into memory: {str(e)}",
        )


# Helper functions


def get_memory_type_title(memory_type: str) -> str:
    """Get proper display title for memory type."""
    titles = {
        "semantic": "Semantic Memory",
        "episodic": "Episodic Memory",
        "procedural": "Procedural Memory",
        "contact": "Contact Memory",
        "procedural_classification": "Procedural: Classification Patterns",
        "procedural_asset": "Procedural: Asset Patterns",
        "procedural_configuration": "Procedural: Configuration Rules",
        "procedural_confidence": "Procedural: Confidence Models",
    }
    return titles.get(memory_type, memory_type.replace("_", " ").title())


def get_memory_type_description(memory_type: str) -> str:
    """Get description for memory type."""
    descriptions = {
        "semantic": "Asset knowledge, human feedback, classification hints, and experiential learning data.",
        "episodic": "Past experiences, decision outcomes, pattern recognition, and success/failure tracking.",
        "procedural": "Business rules, classification patterns, asset matching rules. No dynamic learning.",
        "contact": "Sender profiles, trust scores, communication patterns, and organization relationships.",
        "procedural_classification": "Document classification patterns and regex rules for identifying asset types.",
        "procedural_asset": "Asset matching procedures, keywords, and identification patterns.",
        "procedural_configuration": "System configuration rules and business logic parameters.",
        "procedural_confidence": "Confidence scoring models and decision routing thresholds.",
    }
    return descriptions.get(
        memory_type, "Memory system for storing and retrieving information."
    )


def determine_target_memory_system(filename: str) -> str:
    """
    Determine which memory system to load a knowledge file into.

    Args:
        filename: Name of the knowledge file

    Returns:
        Target memory system name
    """
    filename_lower = filename.lower()

    if "asset" in filename_lower or "classification" in filename_lower:
        return "semantic"
    elif "business_rules" in filename_lower or "patterns" in filename_lower:
        return "procedural"
    elif "contact" in filename_lower or "sender" in filename_lower:
        return "contact"
    elif "spam" in filename_lower:
        return "procedural"  # Spam rules go to procedural
    else:
        return "semantic"  # Default to semantic for general knowledge


async def load_data_into_memory(memory_system, data: Any, filename: str) -> int:
    """
    Load data from a knowledge file into a memory system.

    Args:
        memory_system: Target memory system
        data: Data from the JSON file
        filename: Name of the source file

    Returns:
        Number of items loaded
    """
    items_loaded = 0

    if isinstance(data, list):
        # Load each item in the list
        for item in data:
            try:
                await memory_system.add(
                    content=json.dumps(item) if isinstance(item, dict) else str(item),
                    metadata={
                        "source": filename,
                        "type": "knowledge",
                        "loaded_from_file": True,
                    },
                    confidence="high",
                )
                items_loaded += 1
            except Exception as e:
                logger.warning(f"Failed to load item from {filename}: {e}")

    elif isinstance(data, dict):
        # Load the entire dict as one item, or iterate over key-value pairs
        if len(data) < 100:  # If small dict, load individual key-value pairs
            for key, value in data.items():
                try:
                    await memory_system.add(
                        content=f"{key}: {json.dumps(value) if isinstance(value, dict) else str(value)}",
                        metadata={
                            "source": filename,
                            "type": "knowledge",
                            "key": key,
                            "loaded_from_file": True,
                        },
                        confidence="high",
                    )
                    items_loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load {key} from {filename}: {e}")
        else:
            # Load entire dict as one item if large
            try:
                await memory_system.add(
                    content=json.dumps(data),
                    metadata={
                        "source": filename,
                        "type": "knowledge",
                        "loaded_from_file": True,
                    },
                    confidence="high",
                )
                items_loaded = 1
            except Exception as e:
                logger.warning(f"Failed to load data from {filename}: {e}")

    return items_loaded


async def get_procedural_sample_items(
    procedural_memory, subtype: str, limit: int = 10
) -> list[dict[str, Any]]:
    """
    Get sample items from a specific procedural memory subtype collection.

    Args:
        procedural_memory: The procedural memory system instance
        subtype: The subtype (classification, asset, configuration, confidence)
        limit: Maximum number of items to retrieve

    Returns:
        List of sample items with metadata
    """
    # Map subtypes to collection names
    collection_mapping = {
        "classification": "classification_patterns",
        "asset": "asset_patterns",
        "configuration": "configuration_rules",
        "confidence": "confidence_models",
    }

    collection_key = collection_mapping.get(subtype)
    if not collection_key:
        logger.warning(f"Unknown procedural subtype: {subtype}")
        return []

    try:
        # Get the actual collection name from procedural memory's collections dict
        collection_name = procedural_memory.collections.get(collection_key)
        if not collection_name:
            logger.warning(f"Collection not found for key: {collection_key}")
            return []

        # Get sample items using scroll
        scroll_result = procedural_memory.qdrant.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        sample_items = []
        for point in scroll_result[0]:  # scroll returns (points, next_page_offset)
            try:
                payload = point.payload

                # Extract useful information from the payload
                content = ""

                # Handle classification patterns (pattern data at top level)
                if "document_category" in payload:
                    content = f"Category: {payload.get('document_category', 'N/A')}"
                    if "asset_type" in payload:
                        content += f", Asset: {payload.get('asset_type', 'N/A')}"
                    if "regex_patterns" in payload:
                        content += (
                            f", Patterns: {len(payload['regex_patterns'])} regex rules"
                        )
                    if "keywords" in payload:
                        keywords = payload.get("keywords", [])
                        content += f", Keywords: {', '.join(keywords[:3])}"
                        if len(keywords) > 3:
                            content += f"... (+{len(keywords)-3} more)"
                    if "filename_indicators" in payload:
                        content += f", Files: {payload.get('filename_indicators', [])}"

                # Handle nested pattern_data format (if any)
                elif "pattern_data" in payload:
                    pattern_data = payload["pattern_data"]
                    content = (
                        f"Category: {pattern_data.get('document_category', 'N/A')}"
                    )
                    if "regex_patterns" in pattern_data:
                        content += f", Patterns: {len(pattern_data['regex_patterns'])} regex rules"
                    if "keywords" in pattern_data:
                        content += f", Keywords: {pattern_data.get('keywords', [])}"

                # Handle rule-based patterns
                elif "rule_name" in payload:
                    content = f"Rule: {payload.get('rule_name', 'N/A')}"
                    if "rule_config" in payload:
                        content += f", Config: {payload['rule_config']}"

                # Handle generic pattern type
                elif "pattern_type" in payload:
                    content = f"Type: {payload.get('pattern_type', 'N/A')}"
                    if "asset_type" in payload:
                        content += f", Asset: {payload.get('asset_type', 'N/A')}"

                # Fallback to raw payload
                else:
                    content = str(payload)[:200]

                sample_items.append(
                    {
                        "id": point.id,
                        "content": (
                            content[:200] + "..." if len(content) > 200 else content
                        ),
                        "metadata": payload,
                        "confidence": (
                            payload.get("confidence_range", ["N/A"])[0]
                            if "confidence_range" in payload
                            else "N/A"
                        ),
                        "timestamp": payload.get("created_date", "N/A"),
                        "score": 1.0,  # Default score for procedural items
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to process procedural item: {e}")

        return sample_items

    except Exception as e:
        logger.warning(f"Failed to get sample items for {subtype}: {e}")
        return []


async def get_procedural_subtype_stats(procedural_memory, subtype: str) -> int:
    """
    Get item count for a specific procedural memory subtype collection.

    Args:
        procedural_memory: The procedural memory system instance
        subtype: The subtype (classification, asset, configuration, confidence)

    Returns:
        Number of items in the specific collection
    """
    # Map subtypes to collection names
    collection_mapping = {
        "classification": "classification_patterns",
        "asset": "asset_patterns",
        "configuration": "configuration_rules",
        "confidence": "confidence_models",
    }

    collection_key = collection_mapping.get(subtype)
    if not collection_key:
        logger.warning(f"Unknown procedural subtype: {subtype}")
        return 0

    try:
        # Get the actual collection name from procedural memory's collections dict
        collection_name = procedural_memory.collections.get(collection_key)
        if not collection_name:
            logger.warning(f"Collection not found for key: {collection_key}")
            return 0

        # Get count from Qdrant
        result = procedural_memory.qdrant.count(collection_name=collection_name)
        return result.count

    except Exception as e:
        logger.warning(f"Failed to get count for {subtype}: {e}")
        return 0


async def get_procedural_memory_stats(procedural_memory) -> dict[str, dict[str, Any]]:
    """
    Get statistics from all ProceduralMemory collections.

    Returns stats for each of the 4 procedural collections:
    - classification_patterns
    - asset_patterns
    - configuration_rules
    - confidence_models
    """
    stats = {}

    # Define the subtypes we need to check
    subtypes = ["classification", "asset", "configuration", "confidence"]

    for subtype in subtypes:
        try:
            current_items = await get_procedural_subtype_stats(
                procedural_memory, subtype
            )
            max_items = getattr(config, f"procedural_{subtype}_memory_max_items", 2500)
            usage_percentage = (current_items / max_items) * 100 if max_items > 0 else 0
            estimated_size_mb = (current_items * 2048) / (1024 * 1024)

            stats[subtype] = {
                "current_items": current_items,
                "max_items": max_items,
                "usage_percentage": usage_percentage,
                "estimated_size_mb": estimated_size_mb,
                "collection_info": {"subtype": subtype, "points_count": current_items},
            }

        except Exception as e:
            logger.warning(f"Failed to get stats for procedural {subtype}: {e}")
            stats[subtype] = {
                "current_items": 0,
                "max_items": 2500,
                "usage_percentage": 0,
                "estimated_size_mb": 0,
                "error": str(e),
            }

    return stats

"""
Human Review API endpoints.

This module provides endpoints for managing items that require human review,
allowing corrections and learning from human feedback.
"""

# # Standard library imports
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

# # Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# # Local application imports
from src.asset_management.services.asset_service import AssetService
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function
from src.web_api.dependencies import get_asset_service, get_templates

logger = get_logger(__name__)

router = APIRouter(prefix="/human-review", tags=["human-review"])
templates = get_templates()


# Pydantic models for request/response
class ReviewItem(BaseModel):
    """Item requiring human review."""

    review_id: str
    email_id: str
    mailbox_id: str
    attachment_filename: str
    email_subject: str
    email_body: str
    sender_email: str
    sender_name: Optional[str] = None
    email_date: str

    # System's analysis
    system_confidence: float
    system_asset_suggestions: list[dict[str, Any]] = []
    system_reasoning: str
    document_category: Optional[str] = None
    confidence_level: str

    # Review metadata
    created_at: str
    status: str = Field(
        default="pending", description="pending, in_review, completed, rejected"
    )
    assigned_to: Optional[str] = None

    # Human correction (filled when reviewed)
    human_asset_id: Optional[str] = None
    human_document_category: Optional[str] = None
    human_reasoning: Optional[str] = None
    human_feedback: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None


class SubmitReviewRequest(BaseModel):
    """Request model for submitting human review."""

    human_asset_id: Optional[str] = Field(
        None, description="Asset ID selected by human reviewer"
    )
    human_document_category: str = Field(
        ..., description="Document category chosen by reviewer"
    )
    human_reasoning: str = Field(..., description="Reasoning for the classification")
    human_feedback: Optional[str] = Field(None, description="Additional feedback")
    is_asset_related: bool = Field(
        True, description="Whether document is asset-related"
    )
    reviewed_by: str = Field(default="human_reviewer", description="ID of the reviewer")


class ReviewQueueStats(BaseModel):
    """Statistics for the review queue."""

    total_items: int
    pending: int
    completed: int
    in_review: int
    completion_rate: float


class AddReviewItemRequest(BaseModel):
    """Request model for adding a review item."""

    email_id: str
    mailbox_id: str
    attachment_data: dict[str, Any]
    email_data: dict[str, Any]
    processing_result: dict[str, Any]


# In-memory storage for review items (will be replaced with proper persistence)
review_queue: list[ReviewItem] = []


@router.get("/", response_class=HTMLResponse)
@log_function()
async def human_review_page(
    request: Request,
    asset_service: AssetService = Depends(get_asset_service),
) -> HTMLResponse:
    """
    Display the human review queue page.

    Shows pending items and provides interface for reviewing them.
    """
    logger.info("Loading human review page")

    # Get pending review items
    pending_items = [item for item in review_queue if item.status == "pending"][:50]

    # Get available assets for dropdown
    assets = await asset_service.list_assets()

    # Get queue statistics
    stats = _get_queue_stats()

    return templates.TemplateResponse(
        "human_review.html",
        {
            "request": request,
            "pending_items": pending_items,
            "assets": assets,
            "stats": stats,
        },
    )


@router.get("/items")
@log_function()
async def get_review_items(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ReviewItem]:
    """
    Get review items with optional filtering.

    Args:
        status: Filter by status (pending, in_review, completed, rejected)
        limit: Maximum number of items to return
        offset: Number of items to skip

    Returns:
        List of review items
    """
    logger.info(
        f"Getting review items (status={status}, limit={limit}, offset={offset})"
    )

    filtered_items = review_queue
    if status:
        filtered_items = [item for item in review_queue if item.status == status]

    # Apply pagination
    paginated_items = filtered_items[offset : offset + limit]

    return paginated_items


@router.get("/items/{review_id}")
@log_function()
async def get_review_item(review_id: str) -> ReviewItem:
    """
    Get a specific review item by ID.

    Args:
        review_id: The review item ID

    Returns:
        ReviewItem details

    Raises:
        HTTPException: If item not found
    """
    logger.info(f"Getting review item: {review_id}")

    item = next((item for item in review_queue if item.review_id == review_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    return item


@router.post("/items/{review_id}/submit")
@log_function()
async def submit_review(
    review_id: str,
    review_request: SubmitReviewRequest,
) -> dict[str, str]:
    """
    Submit human review and corrections for an item.

    This endpoint processes human feedback and stores learning
    in the memory systems for future improvement.

    Args:
        review_id: The review item ID
        review_request: Review submission data

    Returns:
        Success message

    Raises:
        HTTPException: If item not found or validation fails
    """
    logger.info(f"Submitting review for item: {review_id}")

    # Find the review item
    item = next((item for item in review_queue if item.review_id == review_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    # Validate asset ID if provided
    if review_request.is_asset_related and not review_request.human_asset_id:
        raise HTTPException(
            status_code=400, detail="Asset ID is required for asset-related documents"
        )

    # Update the item with human corrections
    item.human_asset_id = review_request.human_asset_id
    item.human_document_category = review_request.human_document_category
    item.human_reasoning = review_request.human_reasoning
    item.human_feedback = review_request.human_feedback
    item.reviewed_at = datetime.now(UTC).isoformat()
    item.reviewed_by = review_request.reviewed_by
    item.status = "completed"

    # Store learning experience in memory systems
    await _store_learning_experience(item, review_request.is_asset_related)

    logger.info(
        f"Review completed for item: {review_id} -> "
        f"{'asset ' + review_request.human_asset_id if review_request.is_asset_related else 'non-asset-related'}"
    )

    return {
        "status": "success",
        "message": "Review submitted successfully",
        "review_id": review_id,
    }


@router.get("/stats")
@log_function()
async def get_review_stats() -> ReviewQueueStats:
    """Get review queue statistics."""
    logger.info("Getting review queue statistics")

    stats = _get_queue_stats()
    return ReviewQueueStats(**stats)


@router.post("/items")
@log_function()
async def add_review_item(
    review_request: AddReviewItemRequest,
) -> dict[str, str]:
    """
    Add an item to the review queue.

    This endpoint is typically called by the email processing system
    when an attachment requires human review.

    Args:
        review_request: Review item data

    Returns:
        Review item ID
    """
    logger.info(
        f"Adding item for review: {review_request.attachment_data.get('filename', 'unknown')}"
    )

    review_id = str(uuid4())

    # Extract system suggestions from processing result
    system_suggestions = review_request.processing_result.get("asset_suggestions", [])

    # Create review item
    review_item = ReviewItem(
        review_id=review_id,
        email_id=review_request.email_id,
        mailbox_id=review_request.mailbox_id,
        attachment_filename=review_request.attachment_data.get("filename", "unknown"),
        email_subject=review_request.email_data.get("subject", ""),
        email_body=review_request.email_data.get("body", ""),
        sender_email=review_request.email_data.get("sender_email", ""),
        sender_name=review_request.email_data.get("sender_name"),
        email_date=review_request.email_data.get(
            "date", datetime.now(UTC).isoformat()
        ),
        system_confidence=review_request.processing_result.get("confidence", 0.0),
        system_asset_suggestions=system_suggestions,
        system_reasoning=review_request.processing_result.get(
            "reasoning", "Automated analysis"
        ),
        document_category=review_request.processing_result.get("document_category"),
        confidence_level=review_request.processing_result.get(
            "confidence_level", "unknown"
        ),
        created_at=datetime.now(UTC).isoformat(),
    )

    review_queue.append(review_item)

    logger.info(
        f"Added item for human review: {review_item.attachment_filename} (ID: {review_id})"
    )

    return {
        "status": "success",
        "message": "Item added for review",
        "review_id": review_id,
    }


# Helper functions
def _get_queue_stats() -> dict[str, Any]:
    """Get review queue statistics."""
    total = len(review_queue)
    pending = sum(1 for item in review_queue if item.status == "pending")
    completed = sum(1 for item in review_queue if item.status == "completed")
    in_review = sum(1 for item in review_queue if item.status == "in_review")

    return {
        "total_items": total,
        "pending": pending,
        "completed": completed,
        "in_review": in_review,
        "completion_rate": (completed / total * 100) if total > 0 else 0,
    }


async def _store_learning_experience(item: ReviewItem, is_asset_related: bool) -> None:
    """
    Store the learning experience in memory systems.

    This function integrates with the memory systems to learn from
    human corrections and improve future classification accuracy.

    Args:
        item: The reviewed item with human corrections
        is_asset_related: Whether the document is asset-related

    Note:
        This uses the memory-focused approach - learning patterns are stored
        in memory systems rather than hardcoded rules.
    """
    try:
        # Import memory systems here to avoid circular imports
        # # Local application imports
        from src.memory.episodic import EpisodicMemory
        from src.memory.semantic import SemanticMemory

        # Initialize memory systems using config
        semantic_memory = SemanticMemory(
            max_items=config.semantic_memory_max_items,
            qdrant_url=config.qdrant_url,
            embedding_model=config.embedding_model,
        )

        episodic_memory = EpisodicMemory(
            max_items=config.episodic_memory_max_items,
            qdrant_url=config.qdrant_url,
            embedding_model=config.embedding_model,
        )

        if is_asset_related:
            # Store classification feedback in semantic memory
            learning_content = _create_learning_content(item)

            await semantic_memory.add(
                content=learning_content,
                metadata={
                    "type": "human_correction",
                    "review_id": item.review_id,
                    "filename": item.attachment_filename,
                    "sender_email": item.sender_email,
                    "sender_domain": _extract_domain(item.sender_email),
                    "file_extension": _get_file_extension(item.attachment_filename),
                    "human_asset_id": item.human_asset_id,
                    "human_category": item.human_document_category,
                    "system_confidence": item.system_confidence,
                    "correction_type": _determine_correction_type(item),
                    "learning_priority": _calculate_learning_priority(item),
                    "timestamp": item.reviewed_at,
                    "reviewed_by": item.reviewed_by,
                },
                importance=0.95,  # High importance for human corrections
            )

            # Store episodic experience
            await episodic_memory.add(
                content=f"Human review correction for {item.attachment_filename}",
                metadata={
                    "event_type": "human_review_correction",
                    "review_id": item.review_id,
                    "original_prediction": item.document_category,
                    "human_correction": item.human_document_category,
                    "asset_id": item.human_asset_id,
                    "system_confidence": item.system_confidence,
                    "human_reasoning": item.human_reasoning,
                    "context": {
                        "email_subject": item.email_subject,
                        "sender": item.sender_email,
                        "filename": item.attachment_filename,
                    },
                },
                importance=0.9,
            )

            logger.info(
                f"Stored learning experience for review: {item.review_id} -> {item.human_document_category}"
            )
        else:
            # Store non-asset-related correction
            await semantic_memory.add(
                content=f"Non-asset document: {item.attachment_filename} from {item.sender_email}",
                metadata={
                    "type": "non_asset_correction",
                    "review_id": item.review_id,
                    "filename": item.attachment_filename,
                    "sender_email": item.sender_email,
                    "sender_domain": _extract_domain(item.sender_email),
                    "file_extension": _get_file_extension(item.attachment_filename),
                    "human_reasoning": item.human_reasoning,
                    "human_feedback": item.human_feedback,
                    "system_confidence": item.system_confidence,
                    "timestamp": item.reviewed_at,
                },
                importance=0.8,
            )

            logger.info(
                f"Stored non-asset correction for review: {item.review_id} -> non_asset_related"
            )

    except Exception as e:
        logger.error(f"Failed to store learning experience in memory systems: {e}")
        # Don't fail the review submission if memory storage fails


def _create_learning_content(item: ReviewItem) -> str:
    """Create structured learning content from review item."""
    return f"""
Human Review Correction:
Filename: {item.attachment_filename}
Email Subject: {item.email_subject}
Sender: {item.sender_email}
System Predicted: {item.document_category or 'Unknown'} (confidence: {item.system_confidence:.2f})
Human Corrected: {item.human_document_category}
Asset: {item.human_asset_id}
Reasoning: {item.human_reasoning}
System Suggestions: {len(item.system_asset_suggestions)} options provided
Correction Type: {_determine_correction_type(item)}
Learning Priority: {_calculate_learning_priority(item)}
""".strip()


def _extract_domain(email: str) -> str:
    """Extract domain from email address."""
    return email.split("@")[1] if "@" in email else ""


def _get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return filename.split(".")[-1].lower() if "." in filename else ""


def _determine_correction_type(item: ReviewItem) -> str:
    """Determine the type of correction made."""
    if not item.system_asset_suggestions:
        return "no_suggestions_provided"
    elif item.human_asset_id in [
        s.get("asset_id") for s in item.system_asset_suggestions
    ]:
        return "selected_from_suggestions"
    else:
        return "completely_different_asset"


def _calculate_learning_priority(item: ReviewItem) -> str:
    """Calculate learning priority based on correction context."""
    if item.system_confidence > config.low_confidence_threshold:
        return "high"  # System was confident but wrong
    elif item.system_confidence > config.requires_review_threshold:
        return "medium"
    else:
        return "low"  # System wasn't confident anyway

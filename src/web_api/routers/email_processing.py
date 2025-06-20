"""
Email processing API endpoints.

This module provides endpoints for processing emails from configured mailboxes,
viewing processing history, and managing email processing runs.
"""

# # Standard library imports
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

# # Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# # Local application imports
from src.asset_management.processing.document_processor import DocumentProcessor
from src.asset_management.services.asset_service import AssetService
from src.email_interface.base import EmailSearchCriteria
from src.email_interface.factory import EmailInterfaceFactory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function
from src.web_api.dependencies import get_asset_service, get_document_processor

logger = get_logger(__name__)

router = APIRouter(prefix="/email-processing", tags=["email-processing"])


# Pydantic models for request/response
class ProcessEmailsRequest(BaseModel):
    """Request model for processing emails."""

    mailbox_id: str = Field(..., description="ID of the mailbox to process")
    hours_back: int = Field(
        default=24, description="Number of hours to look back for emails"
    )
    force_reprocess: bool = Field(
        default=False, description="Force reprocessing of already processed emails"
    )


class EmailProcessingResult(BaseModel):
    """Result of processing a single email."""

    email_id: str
    success: bool
    attachments_processed: int
    error_message: Optional[str] = None
    processing_time: float


class ProcessingRunResult(BaseModel):
    """Result of a complete processing run."""

    run_id: str
    mailbox_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    emails_processed: int
    attachments_processed: int
    errors: int
    results: list[EmailProcessingResult] = []


# In-memory storage for processing runs (will be replaced with proper persistence)
processing_runs: dict[str, ProcessingRunResult] = {}
processing_cancelled = False


@router.post("/process")
@log_function()
async def process_emails(
    request: ProcessEmailsRequest,
    document_processor: DocumentProcessor = Depends(get_document_processor),
    asset_service: AssetService = Depends(get_asset_service),
) -> ProcessingRunResult:
    """
    Process emails from the specified mailbox.

    This endpoint starts email processing for the given mailbox,
    processing emails from the last N hours.
    """
    global processing_cancelled
    processing_cancelled = False

    logger.info(
        f"Starting email processing for mailbox: {request.mailbox_id} "
        f"(hours_back={request.hours_back})"
    )

    # Get mailbox configuration
    mailboxes = _get_configured_mailboxes()
    mailbox_config = next((m for m in mailboxes if m["id"] == request.mailbox_id), None)

    if not mailbox_config:
        raise HTTPException(
            status_code=404, detail=f"Mailbox {request.mailbox_id} not found"
        )

    # Create processing run
    run_id = str(uuid4())
    run_result = ProcessingRunResult(
        run_id=run_id,
        mailbox_id=request.mailbox_id,
        status="running",
        started_at=datetime.now(UTC).isoformat(),
        emails_processed=0,
        attachments_processed=0,
        errors=0,
    )
    processing_runs[run_id] = run_result

    try:
        # Create email interface
        email_interface = EmailInterfaceFactory.create(
            system_type=mailbox_config["type"],
            credentials_path=mailbox_config.get("credentials_file"),
        )

        # Connect to email interface
        connected = await email_interface.connect()
        if not connected:
            raise HTTPException(
                status_code=500, detail="Failed to connect to email system"
            )

        # Get emails from the last N hours
        since_date = datetime.now(UTC) - timedelta(hours=request.hours_back)

        criteria = EmailSearchCriteria(
            date_after=since_date,
            has_attachments=True,  # Only process emails with attachments
        )

        emails = await email_interface.list_emails(criteria)

        logger.info(f"Found {len(emails)} emails to process")

        # Get list of known assets
        assets = await asset_service.list_assets()

        # Process each email
        for email in emails:
            if processing_cancelled:
                run_result.status = "cancelled"
                break

            # Check if already processed (unless force reprocess)
            if not request.force_reprocess and _is_email_processed(
                email.id, request.mailbox_id
            ):
                logger.debug(f"Skipping already processed email: {email.id}")
                continue

            email_result = await _process_single_email(
                email, email_interface, document_processor, assets, request.mailbox_id
            )

            run_result.results.append(email_result)
            run_result.emails_processed += 1
            run_result.attachments_processed += email_result.attachments_processed

            if not email_result.success:
                run_result.errors += 1

            # Mark as processed
            _mark_email_processed(email.id, request.mailbox_id)

        run_result.completed_at = datetime.now(UTC).isoformat()
        run_result.status = "completed" if not processing_cancelled else "cancelled"

    except Exception as e:
        logger.error(f"Email processing failed: {e}")
        run_result.status = "failed"
        run_result.errors += 1
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(
        f"Email processing completed: {run_result.emails_processed} emails, "
        f"{run_result.attachments_processed} attachments"
    )

    return run_result


@router.post("/stop")
@log_function()
async def stop_processing() -> dict[str, str]:
    """Stop ongoing email processing."""
    global processing_cancelled
    processing_cancelled = True
    logger.info("Processing cancellation requested")
    return {"status": "success", "message": "Processing cancellation requested"}


@router.get("/runs")
@log_function()
async def get_processing_runs(limit: int = 20) -> list[ProcessingRunResult]:
    """Get recent processing runs."""
    runs = sorted(processing_runs.values(), key=lambda x: x.started_at, reverse=True)[
        :limit
    ]
    return runs


@router.get("/runs/{run_id}")
@log_function()
async def get_processing_run(run_id: str) -> ProcessingRunResult:
    """Get details of a specific processing run."""
    if run_id not in processing_runs:
        raise HTTPException(status_code=404, detail="Processing run not found")
    return processing_runs[run_id]


@router.get("/mailboxes")
@log_function()
async def get_mailboxes() -> list[dict[str, Any]]:
    """Get configured mailboxes."""
    return _get_configured_mailboxes()


# Helper functions
def _get_configured_mailboxes() -> list[dict[str, Any]]:
    """
    Get list of configured mailboxes from config.

    Returns:
        List of mailbox configurations
    """
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
                "credentials_file": config.gmail_credentials_path,
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
                "credentials_file": config.msgraph_credentials_path,
                "icon": "bi-microsoft",
            }
        )

    return mailboxes


# Simple in-memory tracking of processed emails (will be replaced with proper persistence)
processed_emails: dict[str, dict[str, Any]] = {}


def _is_email_processed(email_id: str, mailbox_id: str) -> bool:
    """Check if an email has been processed."""
    key = f"{mailbox_id}:{email_id}"
    return key in processed_emails


def _mark_email_processed(email_id: str, mailbox_id: str) -> None:
    """Mark an email as processed."""
    key = f"{mailbox_id}:{email_id}"
    processed_emails[key] = {
        "processed_at": datetime.now(UTC).isoformat(),
    }


async def _process_single_email(
    email: Any,  # Email object from email_interface
    email_interface: Any,
    document_processor: DocumentProcessor,
    assets: list[Any],
    mailbox_id: str,
) -> EmailProcessingResult:
    """
    Process a single email and its attachments.

    Args:
        email: Email object from email interface
        email_interface: Email interface for fetching attachments
        document_processor: Document processor service
        assets: List of known assets
        mailbox_id: ID of the mailbox

    Returns:
        EmailProcessingResult with processing details
    """
    start_time = datetime.now()

    try:
        attachments_processed = 0

        # Process each attachment
        for attachment in email.attachments:
            try:
                # Get attachment content
                content = await email_interface.get_attachment_content(
                    email.id, attachment.attachment_id
                )

                # Prepare attachment data
                attachment_data = {
                    "filename": attachment.filename,
                    "content": content,
                    "size": attachment.size,
                    "content_type": attachment.content_type,
                }

                # Prepare email data for context
                email_data = {
                    "id": email.id,
                    "sender_email": email.sender.address,
                    "subject": email.subject,
                    "body": email.body_content,
                    "date": email.sent_date.isoformat() if email.sent_date else None,
                }

                # Process the attachment
                result = await document_processor.process_attachment(
                    attachment_data=attachment_data,
                    email_data=email_data,
                    known_assets=assets,
                )

                if result.status.value == "success":
                    attachments_processed += 1

            except Exception as e:
                logger.error(f"Failed to process attachment {attachment.filename}: {e}")

        processing_time = (datetime.now() - start_time).total_seconds()

        return EmailProcessingResult(
            email_id=email.id,
            success=True,
            attachments_processed=attachments_processed,
            processing_time=processing_time,
        )

    except Exception as e:
        logger.error(f"Failed to process email {email.id}: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()

        return EmailProcessingResult(
            email_id=email.id,
            success=False,
            attachments_processed=0,
            error_message=str(e),
            processing_time=processing_time,
        )

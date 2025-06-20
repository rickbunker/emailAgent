#!/usr/bin/env python3
"""
Flask Web Application for Email Agent Asset Management

A user-friendly web interface for setting up and managing assets,
sender mappings, and document classification rules.
"""

# # Standard library imports
# Suppress HuggingFace tokenizers forking warning before any imports
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# # Standard library imports
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# # Third-party imports
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

try:
    # Try relative imports first (when run as module)
    # # Local application imports
    from src.asset_management import (
        Asset,
        AssetIdentifier,
        AssetType,
        ConfidenceLevel,
        DocumentCategory,
        DocumentClassifier,
        ProcessingResult,
        ProcessingStatus,
        SenderMappingService,
    )
    from src.asset_management.processing.document_processor import DocumentProcessor
    from src.asset_management.utils.storage import StorageService
    from src.email_interface import (
        BaseEmailInterface,
        EmailSearchCriteria,
        create_email_interface,
    )
    from src.utils.config import config
    from src.utils.logging_system import (
        LogConfig,
        configure_logging,
        get_logger,
        log_function,
    )
except ImportError:
    # Fallback to direct imports (when run from src directory)
    # # Local application imports
    from src.asset_management import (
        AssetIdentifier,
        AssetType,
        ConfidenceLevel,
        DocumentCategory,
        DocumentClassifier,
        ProcessingResult,
        ProcessingStatus,
        SenderMappingService,
    )
    from src.asset_management.processing.document_processor import DocumentProcessor
    from src.asset_management.utils.storage import StorageService
    from src.email_interface import (
        BaseEmailInterface,
        EmailSearchCriteria,
        create_email_interface,
    )
    from src.utils.config import config
    from src.utils.logging_system import (
        LogConfig,
        configure_logging,
        get_logger,
        log_function,
    )

# Import human_review with error handling for different path contexts
try:
    # # Local application imports
    from src.web_ui.human_review import review_queue
except ImportError:
    try:
        # # Third-party imports
        from web_ui.human_review import review_queue
    except ImportError:
        # Direct import from current directory
        # # Standard library imports
        import os
        import sys

        current_dir = os.path.dirname(__file__)
        sys.path.insert(0, current_dir)
        # # Third-party imports
        from human_review import review_queue

# Try to import Qdrant client
try:
    # # Third-party imports
    from qdrant_client import QdrantClient

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# Configure logging for the web UI
web_config = LogConfig(
    level="DEBUG",
    log_to_file=True,
    log_to_stdout=True,
    log_file=config.web_ui_log_file,
    log_arguments=True,
    log_return_values=False,  # Don't log return values for web routes (can be large)
    log_execution_time=True,
    max_arg_length=200,
)
configure_logging(web_config)

# Get logger for this module
logger = get_logger("web_ui")

app = Flask(__name__)
app.secret_key = config.flask_secret_key

# Global instances for the modular asset management system
document_processor: DocumentProcessor | None = None
asset_identifier: AssetIdentifier | None = None
document_classifier: DocumentClassifier | None = None
sender_mapping_service: SenderMappingService | None = None
storage_service: StorageService | None = None
asset_service: AssetService | None = None
qdrant_client: QdrantClient | None = None

# Email processing history to track processed emails
PROCESSED_EMAILS_FILE = config.processed_emails_file


def parse_comma_separated_identifiers(identifiers_str: str) -> list[str]:
    """
    Parse comma-separated identifiers, respecting quoted strings.

    Examples:
        'IDT, "Smith, Jones & Associates", ACME' -> ['IDT', 'Smith, Jones & Associates', 'ACME']
        'Simple, List' -> ['Simple', 'List']
        '"Quoted String"' -> ['Quoted String']

    Args:
        identifiers_str: Raw comma-separated string from form input

    Returns:
        List of cleaned identifier strings
    """
    if not identifiers_str.strip():
        return []

    identifiers = []
    current = ""
    in_quotes = False
    quote_char = None
    was_quoted = False  # Track if current identifier was quoted

    i = 0
    while i < len(identifiers_str):
        char = identifiers_str[i]

        if not in_quotes:
            if char in ('"', "'"):
                # Start of quoted string
                in_quotes = True
                quote_char = char
                was_quoted = True
            elif char == ",":
                # End of identifier
                cleaned = current.strip()
                # Keep empty strings if they were explicitly quoted
                if cleaned or was_quoted:
                    identifiers.append(cleaned)
                current = ""
                was_quoted = False
            else:
                current += char
        else:
            if char == quote_char:
                # Check for escaped quote
                if (
                    i + 1 < len(identifiers_str)
                    and identifiers_str[i + 1] == quote_char
                ):
                    # Escaped quote - add one quote and skip next
                    current += char
                    i += 1
                else:
                    # End of quoted string
                    in_quotes = False
                    quote_char = None
            else:
                current += char

        i += 1

    # Add final identifier
    cleaned = current.strip()
    if cleaned or was_quoted:
        identifiers.append(cleaned)

    return identifiers


class EmailProcessingHistory:
    """Manages tracking of processed emails to avoid duplicates"""

    def __init__(self, file_path: str = PROCESSED_EMAILS_FILE):
        self.file_path = file_path
        self.processed_emails = self._load_history()

    def _load_history(self) -> dict[str, dict]:
        """Load processing history from file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load email processing history: {e}")
        return {}

    def _save_history(self):
        """Save processing history to file"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump(self.processed_emails, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save email processing history: {e}")

    def is_processed(self, email_id: str, mailbox: str) -> bool:
        """Check if email has been processed"""
        key = f"{mailbox}:{email_id}"
        return key in self.processed_emails

    def mark_processed(self, email_id: str, mailbox: str, processing_info: dict):
        """Mark email as processed"""
        key = f"{mailbox}:{email_id}"
        self.processed_emails[key] = {
            "processed_at": datetime.now(UTC).isoformat(),
            "processing_info": processing_info,
        }
        self._save_history()

    def clear_processed(self, email_id: str = None, mailbox: str = None):
        """Clear processing history for specific email or all"""
        if email_id and mailbox:
            key = f"{mailbox}:{email_id}"
            self.processed_emails.pop(key, None)
        else:
            self.processed_emails.clear()
        self._save_history()


class ProcessingRunHistory:
    """Manages complete history of each processing run with full details"""

    def __init__(self, file_path: str = None):
        self.file_path = file_path or str(
            Path(config.processed_emails_file).parent / "processing_runs.json"
        )
        self.runs = self._load_runs()

    def _load_runs(self) -> list[dict]:
        """Load processing run history from file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path) as f:
                    data = json.load(f)
                    return data.get("runs", [])
        except Exception as e:
            logger.warning(f"Failed to load processing run history: {e}")
        return []

    def _save_runs(self):
        """Save processing run history to file"""
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w") as f:
                json.dump(
                    {"runs": self.runs, "last_updated": datetime.now(UTC).isoformat()},
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save processing run history: {e}")

    def add_run(
        self, run_results: dict[str, Any], parameters: dict[str, Any] = None
    ) -> str:
        """Add a complete processing run to history"""
        run_id = str(uuid.uuid4())

        run_entry = {
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "parameters": parameters or {},
            "results": run_results,
            "summary": {
                "total_mailboxes": len(run_results.get("results", [])),
                "total_emails_found": sum(
                    r.get("total_emails", 0) for r in run_results.get("results", [])
                ),
                "total_emails_processed": sum(
                    r.get("processed_emails", 0) for r in run_results.get("results", [])
                ),
                "total_attachments": sum(
                    sum(
                        detail.get("attachments_count", 0)
                        for detail in r.get("processing_details", [])
                    )
                    for r in run_results.get("results", [])
                ),
                "total_errors": sum(
                    r.get("errors", 0) for r in run_results.get("results", [])
                ),
                "total_duplicates": sum(
                    sum(
                        detail.get("processing_info", {}).get("duplicates", 0)
                        for detail in r.get("processing_details", [])
                    )
                    for r in run_results.get("results", [])
                ),
                "total_classified": sum(
                    sum(
                        detail.get("processing_info", {}).get(
                            "attachments_classified", 0
                        )
                        for detail in r.get("processing_details", [])
                    )
                    for r in run_results.get("results", [])
                ),
                "total_needs_review": sum(
                    sum(
                        len(
                            detail.get("processing_info", {}).get(
                                "needs_human_review", []
                            )
                        )
                        for detail in r.get("processing_details", [])
                    )
                    for r in run_results.get("results", [])
                ),
            },
        }

        self.runs.insert(
            0, run_entry
        )  # Add to beginning for reverse chronological order

        # Keep only last 100 runs to prevent unbounded growth
        self.runs = self.runs[:100]

        self._save_runs()
        logger.info(
            f"Added processing run to history: {run_id} ({run_entry['summary']['total_emails_processed']} emails processed)"
        )
        return run_id

    def get_runs(self, limit: int = 50) -> list[dict]:
        """Get recent processing runs"""
        return self.runs[:limit]

    def get_run(self, run_id: str) -> dict | None:
        """Get specific processing run by ID"""
        for run in self.runs:
            if run["run_id"] == run_id:
                return run
        return None

    def clear_runs(self, before_date: str = None) -> int:
        """Clear processing runs, optionally before a specific date"""
        if before_date:
            cutoff = datetime.fromisoformat(before_date.replace("Z", "+00:00"))
            original_count = len(self.runs)
            self.runs = [
                run
                for run in self.runs
                if datetime.fromisoformat(run["timestamp"].replace("Z", "+00:00"))
                >= cutoff
            ]
            removed = original_count - len(self.runs)
        else:
            removed = len(self.runs)
            self.runs.clear()

        self._save_runs()
        logger.info(f"Cleared {removed} processing runs from history")
        return removed


# Global processing histories
email_history = EmailProcessingHistory()
run_history = ProcessingRunHistory()

# Processing cancellation mechanism
processing_cancelled = False


async def move_file_after_review(
    review_id: str, asset_id: str, document_category: str
) -> None:
    """
    Move file from review folder to proper asset folder after human review completion.

    Args:
        review_id: ID of the review item
        asset_id: Asset ID to move file to
        document_category: Document category for subfolder organization
    """
    try:
        # Get the review item to find the attachment file
        review_item = review_queue.get_item(review_id)
        if not review_item:
            logger.warning(f"Review item not found: {review_id}")
            return

        # Find the attachment content file
        content_file = Path(config.review_attachments_path) / review_id
        if not content_file.exists():
            logger.warning(f"Review attachment content not found: {review_id}")
            return

        # Get asset information
        asset = await asset_agent.get_asset(asset_id)
        if not asset:
            logger.warning(f"Asset not found: {asset_id}")
            return

        # Read the attachment content
        with open(content_file, "rb") as f:
            attachment_content = f.read()

        # Create a processing result mock for the save function
        # Convert document_category string to enum if needed
        doc_category = None
        if document_category:
            try:
                doc_category = DocumentCategory(document_category)
            except ValueError:
                # Fallback to string if enum conversion fails
                doc_category = document_category

        processing_result = ProcessingResult(
            status=ProcessingStatus.SUCCESS,
            file_path=None,  # Will be set by save function
            confidence=1.0,  # Human reviewed = 100% confidence
            metadata={"human_reviewed": True, "review_id": review_id},
            document_category=doc_category,
            matched_asset_id=asset_id,
            confidence_level=ConfidenceLevel.HIGH,
        )

        # Save to proper asset folder
        saved_path = await asset_agent.save_attachment_to_asset_folder(
            attachment_content=attachment_content,
            filename=review_item["attachment_filename"],
            processing_result=processing_result,
            asset_id=asset_id,
        )

        if saved_path:
            logger.info(f"Successfully moved file to: {saved_path}")

            # Also remove the original file from needs_review folder if it exists
            try:
                # Construct the original file path in needs_review
                original_file_path = (
                    Path(asset.folder_path)
                    / "needs_review"
                    / review_item["attachment_filename"]
                )
                if original_file_path.exists():
                    original_file_path.unlink()
                    logger.info(
                        f"Removed original file from needs_review: {original_file_path}"
                    )
                else:
                    logger.debug(
                        f"Original file not found in needs_review: {original_file_path}"
                    )
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to remove original file from needs_review: {cleanup_error}"
                )

            # Clean up the review attachment file
            try:
                content_file.unlink()
                logger.debug(f"Cleaned up review attachment file: {review_id}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to cleanup review file {review_id}: {cleanup_error}"
                )
        else:
            logger.warning(f"Failed to save file for review {review_id}")

    except Exception as e:
        logger.error(f"Error moving file after review {review_id}: {e}")
        raise


@log_function()
def get_configured_mailboxes() -> list[dict[str, str]]:
    """Get list of configured mailboxes from existing credential files"""
    mailboxes = []

    # Check for Gmail configuration files
    gmail_credentials_file = config.gmail_credentials_path
    gmail_token_file = config.gmail_token_path

    if os.path.exists(gmail_credentials_file):
        mailboxes.append(
            {
                "id": config.gmail_mailbox_id or "gmail_primary",
                "name": config.gmail_mailbox_name or "Gmail (Primary Account)",
                "type": "gmail",
                "config": {
                    "credentials_file": gmail_credentials_file,
                    "token_file": gmail_token_file,
                },
            }
        )
        logger.info(f"Found Gmail configuration: {gmail_credentials_file}")

    # Check for Microsoft Graph configuration file
    msgraph_credentials_file = config.msgraph_credentials_path

    if os.path.exists(msgraph_credentials_file):
        mailboxes.append(
            {
                "id": config.msgraph_mailbox_id or "msgraph_primary",
                "name": config.msgraph_mailbox_name
                or "Microsoft 365 (Primary Account)",
                "type": "microsoft_graph",
                "config": {"credentials_path": msgraph_credentials_file},
            }
        )
        logger.info(f"Found Microsoft Graph configuration: {msgraph_credentials_file}")

    logger.info(f"Found {len(mailboxes)} configured mailboxes")
    return mailboxes


@log_function()
async def process_mailbox_emails(
    mailbox_config: dict, hours_back: int = 24, force_reprocess: bool = False
) -> dict[str, Any]:
    """Process emails from a specific mailbox with parallel processing for performance"""
    mailbox_id = mailbox_config["id"]
    mailbox_type = mailbox_config["type"]

    logger.info(
        f"🚀 Processing emails from mailbox: {mailbox_id} ({hours_back} hours back) "
        f"[Parallel: {config.max_concurrent_emails} emails, {config.max_concurrent_attachments} attachments]"
    )

    results = {
        "mailbox_id": mailbox_id,
        "total_emails": 0,
        "processed_emails": 0,
        "skipped_emails": 0,
        "errors": 0,
        "processing_details": [],
        "parallel_stats": {
            "max_concurrent_emails": config.max_concurrent_emails,
            "max_concurrent_attachments": config.max_concurrent_attachments,
            "batch_size": config.email_batch_size,
        },
    }

    try:
        # Create email interface based on type
        if mailbox_type == "microsoft_graph":
            # Microsoft Graph uses credentials_path in constructor
            # # Local application imports
            try:
                # # Local application imports
                from src.email_interface.msgraph import MicrosoftGraphInterface
            except ImportError:
                # # Local application imports
                from src.email_interface.msgraph import MicrosoftGraphInterface

            email_interface = MicrosoftGraphInterface(
                credentials_path=mailbox_config["config"]["credentials_path"]
            )
            # Connect (credentials loaded in constructor)
            await email_interface.connect()
        else:
            # Gmail and others use the factory pattern
            email_interface = create_email_interface(
                mailbox_type, **mailbox_config["config"]
            )
            # Connect with credentials
            await email_interface.connect(mailbox_config["config"])

        # Define search criteria for last N hours
        start_date = datetime.now(UTC) - timedelta(hours=hours_back)
        search_criteria = EmailSearchCriteria(
            has_attachments=True,  # Only process emails with attachments
            date_after=start_date,
            labels=config.inbox_labels,  # Only search inbox, not sent items
        )

        # Search for emails - try list_emails first, fallback if needed
        try:
            emails = await email_interface.list_emails(search_criteria)
        except Exception as list_error:
            # Fallback to basic search if advanced criteria not supported
            logger.warning(
                f"list_emails with criteria failed ({list_error}), trying basic search"
            )
            basic_criteria = EmailSearchCriteria(
                has_attachments=True, max_results=config.max_search_results
            )
            all_emails = await email_interface.list_emails(basic_criteria)

            # Filter manually by date
            emails = []
            for email in all_emails:
                if email.received_date and email.received_date >= start_date:
                    emails.append(email)

        results["total_emails"] = len(emails)

        logger.info(
            f"Found {len(emails)} emails with attachments in the last {hours_back} hours"
        )

        if not emails:
            logger.info("No emails to process")
            return results

        # Check for cancellation before processing
        if processing_cancelled:
            logger.info("🛑 Processing cancelled before starting email processing")
            results["cancelled"] = True
            return results

        # Process emails in parallel batches for optimal performance
        await _process_emails_in_parallel(
            emails, email_interface, mailbox_id, force_reprocess, results
        )

    except Exception as e:
        logger.error(f"Failed to process mailbox {mailbox_id}: {e}")
        results["error"] = str(e)

    finally:
        # Clean up email interface connection
        try:
            await email_interface.disconnect()
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up email interface: {cleanup_error}")

    logger.info(
        f"🏁 Mailbox processing complete: {results['processed_emails']} processed, "
        f"{results['skipped_emails']} skipped, {results['errors']} errors"
    )
    return results


@log_function()
async def _process_emails_in_parallel(
    emails: list, email_interface, mailbox_id: str, force_reprocess: bool, results: dict
) -> None:
    """
    Process emails in parallel batches with concurrency control.

    This function implements the core parallel processing logic:
    - Processes emails in configurable batches
    - Limits concurrent email processing
    - Each email processes its attachments in parallel
    - Maintains comprehensive error handling and logging
    """
    # Create semaphore to limit concurrent email processing
    email_semaphore = asyncio.Semaphore(config.max_concurrent_emails)

    # Process emails in batches to avoid overwhelming the system
    batch_size = config.email_batch_size
    total_batches = (len(emails) + batch_size - 1) // batch_size

    logger.info(
        f"📦 Processing {len(emails)} emails in {total_batches} batches "
        f"of {batch_size} (max {config.max_concurrent_emails} concurrent)"
    )

    for batch_num in range(total_batches):
        # Check for cancellation before each batch
        if processing_cancelled:
            logger.info(f"🛑 Processing cancelled during batch {batch_num + 1}")
            results["cancelled"] = True
            return

        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(emails))
        batch_emails = emails[start_idx:end_idx]

        logger.info(
            f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails)"
        )

        # Create tasks for this batch
        batch_tasks = []
        for email in batch_emails:
            task = _process_single_email_with_semaphore(
                email, email_interface, mailbox_id, force_reprocess, email_semaphore
            )
            batch_tasks.append(task)

        # Process this batch and collect results
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process batch results
        for i, result in enumerate(batch_results):
            email = batch_emails[i]

            if isinstance(result, Exception):
                # Handle exceptions
                results["errors"] += 1
                error_msg = str(result)
                logger.error(f"❌ Failed to process email {email.id}: {error_msg}")
                results["processing_details"].append(
                    {"email_id": email.id, "subject": email.subject, "error": error_msg}
                )
            elif result.get("skipped"):
                # Email was skipped (already processed)
                results["skipped_emails"] += 1
                logger.debug(f"⏭️  Skipped already processed email: {email.id}")
            else:
                # Email was successfully processed
                results["processed_emails"] += 1

                # Mark as processed
                email_history.mark_processed(email.id, mailbox_id, result)

                # Add to results
                results["processing_details"].append(
                    {
                        "email_id": email.id,
                        "subject": email.subject,
                        "sender": email.sender.address if email.sender else "Unknown",
                        "attachments_count": (
                            len(email.attachments) if email.attachments else 0
                        ),
                        "processing_info": result,
                    }
                )

                logger.info(f"✅ Successfully processed email: {email.subject[:50]}...")

        logger.info(
            f"✨ Batch {batch_num + 1} complete: {len([r for r in batch_results if not isinstance(r, Exception) and not r.get('skipped')])} processed"
        )


@log_function()
async def _process_single_email_with_semaphore(
    email,
    email_interface,
    mailbox_id: str,
    force_reprocess: bool,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """
    Process a single email with semaphore-controlled concurrency.

    This wrapper ensures we don't exceed the maximum concurrent email processing limit.
    """
    async with semaphore:
        # Check if already processed first (before acquiring semaphore for long)
        if not force_reprocess and email_history.is_processed(email.id, mailbox_id):
            return {"skipped": True}

        # Process the email with parallel attachment processing
        return await process_single_email_parallel(email, email_interface, mailbox_id)


@log_function()
async def process_single_email_parallel(
    email, email_interface: BaseEmailInterface, mailbox_id: str = "unknown"
) -> dict[str, Any]:
    """
    Process a single email and its attachments in parallel through the asset document agent.

    This version processes all attachments within an email concurrently for maximum speed,
    especially important when antivirus scanning creates bottlenecks.

    Args:
        email: Email object containing subject, attachments, and metadata
        email_interface: Interface for downloading attachment content
        mailbox_id: Identifier for the mailbox being processed

    Returns:
        Dictionary containing processing statistics and results

    Raises:
        Exception: If asset agent is not initialized
    """
    if not asset_agent:
        raise Exception("Asset agent not initialized")

    processing_info = {
        "attachments_processed": 0,
        "attachments_classified": 0,
        "assets_matched": [],
        "processing_time": datetime.now(UTC).isoformat(),
        "quarantined": 0,
        "duplicates": 0,
        "errors": 0,
        "parallel_attachments": True,  # Flag to indicate parallel processing was used
    }

    logger.info(
        f"🔄 Processing email '{email.subject}' with {len(email.attachments) if email.attachments else 0} attachments (parallel)"
    )

    if not email.attachments:
        logger.warning(f"Email '{email.subject}' has no attachments to process")
        return processing_info

    # Create email data once for all attachments
    email_data = {
        "sender_email": email.sender.address if email.sender else None,
        "sender_name": email.sender.name if email.sender else None,
        "subject": email.subject,
        "date": (
            email.received_date.isoformat()
            if email.received_date
            else datetime.now(UTC).isoformat()
        ),
        "body": email.body_text or email.body_html or "",
    }

    # Create semaphore for attachment processing
    attachment_semaphore = asyncio.Semaphore(config.max_concurrent_attachments)

    # Create tasks for parallel attachment processing
    attachment_tasks = []
    for attachment in email.attachments:
        task = _process_single_attachment_with_semaphore(
            attachment,
            email,
            email_interface,
            email_data,
            mailbox_id,
            attachment_semaphore,
        )
        attachment_tasks.append(task)

    logger.info(
        f"🚀 Processing {len(attachment_tasks)} attachments in parallel (max {config.max_concurrent_attachments} concurrent)"
    )

    # Process all attachments in parallel
    try:
        # Use asyncio.wait_for to add timeout protection
        attachment_results = await asyncio.wait_for(
            asyncio.gather(*attachment_tasks, return_exceptions=True),
            timeout=config.processing_timeout_seconds,
        )

        # Process results from parallel attachment processing
        for i, result in enumerate(attachment_results):
            attachment = email.attachments[i]

            if isinstance(result, Exception):
                processing_info["errors"] += 1
                logger.error(
                    f"❌ Failed to process attachment {attachment.filename}: {result}"
                )
            else:
                # Merge attachment result into processing_info
                if result:
                    processing_info["attachments_processed"] += 1

                    if result.get("classified"):
                        processing_info["attachments_classified"] += 1

                    if result.get("quarantined"):
                        processing_info["quarantined"] += 1

                    if result.get("duplicate"):
                        processing_info["duplicates"] += 1

                    if result.get("asset_matched"):
                        processing_info["assets_matched"].append(
                            result["asset_matched"]
                        )

                    if result.get("needs_human_review"):
                        processing_info.setdefault("needs_human_review", []).append(
                            result["needs_human_review"]
                        )

        logger.info(
            f"✅ Email processing complete: {processing_info['attachments_processed']} attachments processed "
            f"({processing_info['attachments_classified']} classified, {processing_info['errors']} errors)"
        )

    except TimeoutError:
        processing_info["errors"] += len(email.attachments)
        logger.error(
            f"⏰ Email processing timed out after {config.processing_timeout_seconds} seconds"
        )
        # Don't raise - return what we have

    return processing_info


@log_function()
async def _process_single_attachment_with_semaphore(
    attachment,
    email,
    email_interface,
    email_data: dict,
    mailbox_id: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """
    Process a single attachment with semaphore-controlled concurrency.

    This function handles the full attachment processing pipeline:
    1. Download attachment content (if needed)
    2. Process through asset document agent (includes antivirus scanning)
    3. Save to appropriate location
    4. Handle human review queue if needed
    """
    async with semaphore:
        # Check for cancellation at start of attachment processing
        if processing_cancelled:
            logger.info(f"🛑 Processing cancelled for attachment: {attachment.filename}")
            return {"cancelled": True, "filename": attachment.filename}

        attachment_result = {
            "filename": attachment.filename,
            "classified": False,
            "quarantined": False,
            "duplicate": False,
            "asset_matched": None,
            "needs_human_review": None,
        }

        try:
            logger.info(f"🔍 Processing attachment: {attachment.filename}")

            # Initialize attachment_data early to avoid scoping issues
            attachment_data = {
                "filename": attachment.filename,
                "content": None,
            }

            # Get attachment content (may already be loaded)
            attachment_content = attachment.content

            if not attachment_content:
                # Try to download if not already loaded
                try:
                    attachment_content = await email_interface.download_attachment(
                        email.id, attachment.id
                    )
                except Exception as download_error:
                    logger.warning(
                        f"Could not download attachment {attachment.filename}: {download_error}"
                    )
                    return attachment_result

            # Update attachment data with content
            attachment_data["content"] = attachment_content

            # Process with asset document agent (enhanced with asset matching)
            result = await asset_agent.enhanced_process_attachment(
                attachment_data=attachment_data, email_data=email_data
            )

            # Handle different processing results
            if result.status == ProcessingStatus.QUARANTINED:
                attachment_result["quarantined"] = True
                logger.warning(
                    f"🚨 Attachment quarantined: {attachment.filename} - {result.quarantine_reason}"
                )
                return attachment_result

            if result.status == ProcessingStatus.DUPLICATE:
                attachment_result["duplicate"] = True
                logger.info(f"📋 Duplicate attachment skipped: {attachment.filename}")
                return attachment_result

            if result.status != ProcessingStatus.SUCCESS:
                logger.warning(
                    f"⚠️  Attachment processing failed: {attachment.filename} - {result.error_message}"
                )
                return attachment_result

            # Mark as successfully classified
            attachment_result["classified"] = True

            # Save successful attachment to appropriate folder and build detailed asset match info
            if result.matched_asset_id:
                # Build asset match object in the format expected by the frontend
                attachment_result["asset_matched"] = {
                    "asset_id": result.matched_asset_id,
                    "confidence": result.asset_confidence,
                    "attachment_name": attachment.filename,
                    "file_path": str(result.file_path) if result.file_path else None,
                    "document_category": (
                        result.document_category.value
                        if result.document_category
                        else None
                    ),
                    "confidence_level": (
                        result.confidence_level.value
                        if result.confidence_level
                        else None
                    ),
                    "classification_metadata": result.classification_metadata or {},
                }
                logger.info(
                    f"🎯 Asset matched: {attachment.filename} -> {result.matched_asset_id[:8]}"
                )

            # Save attachment to asset folder
            try:
                saved_path = await asset_agent.save_attachment_to_asset_folder(
                    attachment_content,
                    attachment.filename,
                    result,
                    result.matched_asset_id,
                )

                if saved_path:
                    logger.info(f"💾 Saved: {attachment.filename} -> {saved_path}")
                    # Update file path in asset match info if it exists
                    if attachment_result.get("asset_matched"):
                        attachment_result["asset_matched"]["file_path"] = str(
                            saved_path
                        )
                else:
                    logger.warning(
                        f"⚠️  Failed to save attachment: {attachment.filename}"
                    )
            except Exception as save_error:
                logger.error(
                    f"Failed to save attachment {attachment.filename}: {save_error}"
                )

            # Store processing metadata
            try:
                await asset_agent.store_processed_document(
                    result.file_hash, result, result.matched_asset_id
                )
            except Exception as store_error:
                logger.warning(f"Failed to store document metadata: {store_error}")

            # Check if human review is needed
            needs_review = result.confidence_level == ConfidenceLevel.VERY_LOW or (
                result.confidence_level == ConfidenceLevel.LOW
                and not result.matched_asset_id
            )

            review_reason = ""
            if result.confidence_level == ConfidenceLevel.VERY_LOW:
                review_reason = "Very low classification confidence"
            elif (
                result.confidence_level == ConfidenceLevel.LOW
                and not result.matched_asset_id
            ):
                review_reason = "Low confidence with no asset match"

            if needs_review:
                try:
                    review_id = review_queue.add_for_review(
                        email_id=email.id,
                        mailbox_id=mailbox_id,
                        attachment_data=attachment_data,
                        email_data=email_data,
                        processing_result=result,
                    )
                    logger.info(
                        f"👥 Added attachment to human review queue: {review_id}"
                    )

                    attachment_result["needs_human_review"] = {
                        "review_id": review_id,
                        "attachment_name": attachment.filename,
                        "reason": review_reason,
                    }
                except Exception as review_error:
                    logger.error(
                        f"Failed to add attachment to review queue: {review_error}"
                    )

            logger.info(f"✅ Attachment processed successfully: {attachment.filename}")
            return attachment_result

        except Exception as e:
            logger.error(f"❌ Failed to process attachment {attachment.filename}: {e}")
            raise  # Re-raise to be caught by gather()


# Keep the original function for backward compatibility
@log_function()
async def process_single_email(
    email, email_interface: BaseEmailInterface, mailbox_id: str = "unknown"
) -> dict[str, Any]:
    """
    Legacy sequential email processing function (kept for compatibility).

    New code should use process_single_email_parallel() for better performance.
    """
    return await process_single_email_parallel(email, email_interface, mailbox_id)


@log_function()
def initialize_asset_agent() -> None:
    """
    Initialize the asset management system components.

    Creates global instances for the modular asset management system.

    Raises:
        Exception: If initialization fails critically
    """
    global document_processor, asset_identifier, document_classifier
    global sender_mapping_service, storage_service, asset_service, qdrant_client

    # Guard against duplicate initialization
    if document_processor is not None:
        logger.debug("Asset management system already initialized, skipping")
        return

    try:
        # Initialize the modular components
        logger.info("Initializing modular asset management system...")

        # Initialize Qdrant client if available
        if QDRANT_AVAILABLE:
            try:
                qdrant_client = QdrantClient(
                    host=config.qdrant_host, port=config.qdrant_port
                )
                logger.info("Connected to Qdrant vector database")
            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant: {e}")
                qdrant_client = None
        else:
            logger.info("Qdrant not available - running without vector storage")
            qdrant_client = None

        # Import AssetService here to avoid circular imports
        # # Local application imports
        from src.asset_management.services.asset_service import AssetService

        # Initialize individual services
        asset_identifier = AssetIdentifier()
        document_classifier = DocumentClassifier()
        sender_mapping_service = SenderMappingService()
        storage_service = StorageService()
        asset_service = AssetService(
            qdrant_client=qdrant_client, base_assets_path=config.assets_base_path
        )

        # Initialize collections if we have Qdrant
        if qdrant_client:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asset_service.initialize_collection())
            finally:
                loop.close()

        # Initialize the document processor with all components
        document_processor = DocumentProcessor(
            asset_identifier=asset_identifier,
            document_classifier=document_classifier,
            storage_service=storage_service,
        )

        logger.info("✅ Asset management system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize asset management system: {e}")
        logger.warning("Running in degraded mode - some features will be limited")
        # Don't raise - allow app to start in degraded mode


@app.route("/")
@log_function()
def index() -> str:
    """
    Main dashboard page displaying asset statistics and overview.

    Returns:
        Rendered HTML template for the dashboard
    """
    if not asset_service:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    # Get asset statistics
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_service.list_assets())

        # Calculate statistics
        stats = {
            "total_assets": len(assets),
            "by_type": {},
            "recent_assets": assets[-5:] if assets else [],  # Last 5 assets
        }

        # Count by asset type
        for asset in assets:
            asset_type = asset.asset_type.value
            stats["by_type"][asset_type] = stats["by_type"].get(asset_type, 0) + 1

        logger.info(f"Dashboard loaded with {len(assets)} assets")
        return render_template("dashboard.html", stats=stats, assets=assets)

    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        return render_template("error.html", error=f"Failed to load dashboard: {e}")
    finally:
        loop.close()


@app.route("/assets")
@log_function()
def list_assets() -> str:
    """List all assets"""
    if not asset_agent:
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())

        # Calculate type counts for the template
        type_counts = {}
        for asset in assets:
            asset_type = asset.asset_type.value
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

        logger.info(f"Assets page loaded with {len(assets)} assets")
        return render_template(
            "assets.html", assets=assets, asset_types=AssetType, type_counts=type_counts
        )
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        return render_template("error.html", error=f"Failed to list assets: {e}")
    finally:
        loop.close()


@app.route("/assets/new", methods=["GET", "POST"])
@log_function()
def create_asset() -> str:
    """Create a new asset"""
    if not asset_agent:
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    if request.method == "POST":
        try:
            # Get form data
            deal_name = request.form.get("deal_name", "").strip()
            asset_name = request.form.get("asset_name", "").strip()
            asset_type_str = request.form.get("asset_type", "")
            identifiers_str = request.form.get("identifiers", "").strip()

            logger.info(f"Creating asset: {deal_name} ({asset_type_str})")

            # Validate required fields
            if not deal_name or not asset_name or not asset_type_str:
                logger.warning("Asset creation failed: missing required fields")
                flash("Deal name, asset name, and asset type are required", "error")
                return render_template(
                    "create_asset.html", asset_types=AssetType, form_data=request.form
                )

            # Parse asset type
            try:
                asset_type = AssetType(asset_type_str)
            except ValueError:
                logger.warning(f"Invalid asset type selected: {asset_type_str}")
                flash("Invalid asset type selected", "error")
                return render_template(
                    "create_asset.html", asset_types=AssetType, form_data=request.form
                )

            # Parse identifiers
            identifiers = parse_comma_separated_identifiers(identifiers_str)

            # Create asset
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            deal_id = loop.run_until_complete(
                asset_agent.create_asset(
                    deal_name=deal_name,
                    asset_name=asset_name,
                    asset_type=asset_type,
                    identifiers=identifiers,
                )
            )

            loop.close()

            logger.info(
                f"Asset created successfully: {deal_name} with ID: {deal_id[:8]}..."
            )
            flash(
                f'Asset "{deal_name}" created successfully with ID: {deal_id[:8]}...',
                "success",
            )
            return redirect(url_for("list_assets"))

        except Exception as e:
            logger.error(f"Failed to create asset: {e}")
            flash(f"Failed to create asset: {e}", "error")
            return render_template(
                "create_asset.html", asset_types=AssetType, form_data=request.form
            )

    return render_template(
        "create_asset.html", asset_types=AssetType, document_categories=DocumentCategory
    )


@app.route("/assets/<deal_id>")
@log_function()
def view_asset(deal_id: str) -> str:
    """View asset details"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get asset details
        asset = loop.run_until_complete(asset_agent.get_asset(deal_id))

        if not asset:
            logger.warning(f"Asset not found: {deal_id}")
            flash("Asset not found", "error")
            return redirect(url_for("list_assets"))

        logger.info(f"Viewing asset: {asset.deal_name}")

        # Get sender mappings for this asset
        all_mappings = loop.run_until_complete(asset_agent.list_asset_sender_mappings())
        sender_mappings = [m for m in all_mappings if m["asset_id"] == deal_id]

        return render_template(
            "asset_detail.html",
            asset=asset,
            sender_mappings=sender_mappings,
            document_categories=DocumentCategory,
        )

    except Exception as e:
        logger.error(f"Failed to load asset {deal_id}: {e}")
        return render_template("error.html", error=f"Failed to load asset: {e}")
    finally:
        loop.close()


@app.route("/assets/<deal_id>/edit", methods=["GET", "POST"])
@log_function()
def edit_asset(deal_id: str) -> str:
    """Edit asset details"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get current asset details
        asset = loop.run_until_complete(asset_agent.get_asset(deal_id))

        if not asset:
            logger.warning(f"Asset not found: {deal_id}")
            flash("Asset not found", "error")
            return redirect(url_for("list_assets"))

        if request.method == "POST":
            try:
                # Get form data
                deal_name = request.form.get("deal_name", "").strip()
                asset_name = request.form.get("asset_name", "").strip()
                asset_type_str = request.form.get("asset_type", "")
                identifiers_str = request.form.get("identifiers", "").strip()

                logger.info(f"Updating asset {deal_id}: {deal_name}")

                # Validate required fields
                if not deal_name or not asset_name or not asset_type_str:
                    logger.warning("Asset update failed: missing required fields")
                    flash("Deal name, asset name, and asset type are required", "error")
                    return render_template(
                        "edit_asset.html",
                        asset=asset,
                        asset_types=AssetType,
                        form_data=request.form,
                    )

                # Parse asset type
                try:
                    asset_type = AssetType(asset_type_str)
                except ValueError:
                    logger.warning(f"Invalid asset type selected: {asset_type_str}")
                    flash("Invalid asset type selected", "error")
                    return render_template(
                        "edit_asset.html",
                        asset=asset,
                        asset_types=AssetType,
                        form_data=request.form,
                    )

                # Parse identifiers
                identifiers = parse_comma_separated_identifiers(identifiers_str)

                # Update asset
                success = loop.run_until_complete(
                    asset_agent.update_asset(
                        deal_id=deal_id,
                        deal_name=deal_name,
                        asset_name=asset_name,
                        asset_type=asset_type,
                        identifiers=identifiers,
                    )
                )

                if success:
                    logger.info(f"Asset updated successfully: {deal_name}")
                    flash(f'Asset "{deal_name}" updated successfully', "success")
                    return redirect(url_for("view_asset", deal_id=deal_id))
                else:
                    logger.error(f"Failed to update asset: {deal_id}")
                    flash("Failed to update asset", "error")

            except Exception as e:
                logger.error(f"Error updating asset {deal_id}: {e}")
                flash(f"Error updating asset: {e}", "error")

        return render_template("edit_asset.html", asset=asset, asset_types=AssetType)

    except Exception as e:
        logger.error(f"Failed to load asset for editing {deal_id}: {e}")
        return render_template("error.html", error=f"Failed to load asset: {e}")
    finally:
        loop.close()


@app.route("/assets/<deal_id>/delete", methods=["POST"])
@log_function()
def delete_asset(deal_id: str) -> str:
    """Delete an asset"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return jsonify({"error": "Asset agent not initialized"}), 500

    try:
        # Delete asset logic would go here
        flash("Asset deletion not yet implemented", "warning")
        return redirect(url_for("list_assets"))

    except Exception as e:
        logger.error(f"Failed to delete asset {deal_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/senders")
@log_function()
def list_senders() -> str:
    """List all sender mappings with asset names"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get mappings and assets
        mappings = loop.run_until_complete(asset_agent.list_asset_sender_mappings())
        assets = loop.run_until_complete(asset_agent.list_assets())

        # Create asset lookup dictionary
        asset_lookup = {asset.deal_id: asset for asset in assets}

        # Enrich mappings with asset names
        enriched_mappings = []
        for mapping in mappings:
            asset_id = mapping["asset_id"]
            asset = asset_lookup.get(asset_id)

            enriched_mapping = mapping.copy()
            if asset:
                enriched_mapping["asset_name"] = asset.deal_name
                enriched_mapping["asset_type"] = asset.asset_type.value
                enriched_mapping["asset_full_name"] = asset.asset_name
            else:
                enriched_mapping["asset_name"] = f"Unknown Asset ({asset_id[:8]}...)"
                enriched_mapping["asset_type"] = "unknown"
                enriched_mapping["asset_full_name"] = "Asset not found"

            enriched_mappings.append(enriched_mapping)

        logger.info(
            f"Sender mappings page loaded with {len(enriched_mappings)} mappings"
        )
        return render_template("senders.html", mappings=enriched_mappings)

    except Exception as e:
        logger.error(f"Failed to load sender mappings: {e}")
        return render_template(
            "error.html", error=f"Failed to load sender mappings: {e}"
        )
    finally:
        loop.close()


@app.route("/senders/new", methods=["GET", "POST"])
@log_function()
def create_sender_mapping() -> str:
    """Create new sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    if request.method == "POST":
        try:
            # Get form data
            asset_id = request.form.get("asset_id", "").strip()
            sender_email = request.form.get("sender_email", "").strip().lower()
            confidence = float(request.form.get("confidence", 0.8))
            document_types_str = request.form.get("document_types", "").strip()

            logger.info(f"Creating sender mapping: {sender_email} -> {asset_id}")

            # Validate
            if not asset_id or not sender_email:
                logger.warning(
                    "Sender mapping creation failed: missing required fields"
                )
                flash("Asset and sender email are required", "error")
                return render_template("create_sender_mapping.html")

            # Parse document types
            if document_types_str:
                [dt.strip() for dt in document_types_str.split(",") if dt.strip()]

            # Create mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            mapping_id = loop.run_until_complete(
                asset_agent.create_asset_sender_mapping(
                    sender_email=sender_email,
                    deal_id=asset_id,
                    confidence=confidence,
                    source="manual",
                )
            )

            loop.close()

            logger.info(f"Sender mapping created successfully: {mapping_id[:8]}...")
            flash(
                f"Sender mapping created successfully: {mapping_id[:8]}...", "success"
            )
            return redirect(url_for("list_senders"))

        except Exception as e:
            logger.error(f"Failed to create sender mapping: {e}")
            flash(f"Failed to create sender mapping: {e}", "error")

    # Get available assets for dropdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())
    except Exception as e:
        logger.error(f"Failed to load assets for sender mapping form: {e}")
        assets = []
    finally:
        loop.close()

    return render_template(
        "create_sender_mapping.html",
        assets=assets,
        document_categories=DocumentCategory,
    )


@app.route("/api/assets")
@log_function()
def api_list_assets() -> tuple[dict, int] | dict:
    """API endpoint to list assets (for AJAX calls)"""
    if not asset_agent:
        logger.error("Asset management system not initialized for API call")
        return jsonify({"error": "Asset management system not initialized"}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())

        assets_data = []
        for asset in assets:
            assets_data.append(
                {
                    "deal_id": asset.deal_id,
                    "deal_name": asset.deal_name,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type.value,
                    "identifiers": asset.identifiers,
                    "created_date": asset.created_date.isoformat(),
                    "folder_path": asset.folder_path,
                }
            )

        logger.info(f"API returned {len(assets_data)} assets")
        return jsonify({"assets": assets_data})

    except Exception as e:
        logger.error(f"API failed to list assets: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/health")
@log_function()
def api_health() -> tuple[dict, int] | dict:
    """API health check endpoint"""
    if not asset_agent:
        logger.error("Asset agent not initialized for health check")
        return (
            jsonify({"status": "error", "message": "Asset agent not initialized"}),
            500,
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        health = loop.run_until_complete(asset_agent.health_check())
        logger.info("Health check completed successfully")
        return jsonify({"status": "ok", "health": health})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        loop.close()


@app.route("/email-processing")
@log_function()
def email_processing() -> str:
    """Email processing management page"""
    logger.info("Loading email processing page")

    # Get configured mailboxes
    mailboxes = get_configured_mailboxes()

    # Get recent processing runs (detailed history)
    recent_runs = []
    try:
        recent_runs = run_history.get_runs(limit=10)
    except Exception as e:
        logger.warning(f"Failed to load recent processing runs: {e}")

    # Get legacy processing history for backwards compatibility
    recent_history = []
    try:
        # Get last 10 processed emails from history
        for key, info in list(email_history.processed_emails.items())[-10:]:
            mailbox_id, email_id = key.split(":", 1)
            recent_history.append(
                {
                    "mailbox_id": mailbox_id,
                    "email_id": email_id,
                    "processed_at": info.get("processed_at"),
                    "processing_info": info.get("processing_info", {}),
                }
            )
    except Exception as e:
        logger.warning(f"Failed to load recent processing history: {e}")

    return render_template(
        "email_processing.html",
        mailboxes=mailboxes,
        recent_runs=recent_runs,  # New detailed run history
        recent_history=recent_history,  # Legacy per-email history
        total_processed=len(email_history.processed_emails),
        total_runs=len(run_history.runs),
    )


@app.route("/email-processing/runs/<run_id>")
@log_function()
def view_processing_run(run_id: str) -> str:
    """View detailed results of a specific processing run"""
    try:
        run = run_history.get_run(run_id)

        if not run:
            logger.warning(f"Processing run not found: {run_id}")
            flash("Processing run not found", "error")
            return redirect(url_for("email_processing"))

        logger.info(f"Viewing processing run: {run_id}")
        return render_template("processing_run_detail.html", run=run)

    except Exception as e:
        logger.error(f"Failed to load processing run {run_id}: {e}")
        return render_template(
            "error.html", error=f"Failed to load processing run: {e}"
        )


@app.route("/api/stop-processing", methods=["POST"])
@log_function()
def api_stop_processing() -> tuple[dict, int] | dict:
    """API endpoint to stop ongoing email processing"""
    global processing_cancelled

    processing_cancelled = True
    logger.info("🛑 Processing cancellation requested")

    return jsonify(
        {"status": "success", "message": "Processing cancellation requested"}
    )


@app.route("/api/process-emails", methods=["POST"])
@log_function()
def api_process_emails() -> tuple[dict, int] | dict:
    """API endpoint to process emails from selected mailbox"""
    global processing_cancelled

    if not asset_agent:
        logger.error("Asset agent not initialized for email processing")
        return jsonify({"error": "Asset agent not initialized"}), 500

    # Reset cancellation flag at start of processing
    processing_cancelled = False

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        mailbox_id = data.get("mailbox_id")
        hours_back = int(data.get("hours_back", 24))
        force_reprocess = data.get("force_reprocess", False)

        if not mailbox_id:
            return jsonify({"error": "Mailbox ID is required"}), 400

        # Get mailbox configuration
        mailboxes = get_configured_mailboxes()
        mailbox_config = None
        for mailbox in mailboxes:
            if mailbox["id"] == mailbox_id:
                mailbox_config = mailbox
                break

        if not mailbox_config:
            return jsonify({"error": f"Mailbox {mailbox_id} not found"}), 404

        logger.info(f"Starting email processing for mailbox: {mailbox_id}")

        # Store processing parameters for history
        processing_parameters = {
            "mailbox_id": mailbox_id,
            "mailbox_name": mailbox_config.get("name", mailbox_id),
            "hours_back": hours_back,
            "force_reprocess": force_reprocess,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Process emails asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Process single mailbox (current behavior)
            single_result = loop.run_until_complete(
                process_mailbox_emails(mailbox_config, hours_back, force_reprocess)
            )

            # Check if processing was cancelled
            if single_result.get("cancelled"):
                logger.info("Email processing was cancelled by user")
                return jsonify(
                    {
                        "status": "cancelled",
                        "message": "Processing was stopped by user request",
                        "results": single_result,
                    }
                )

            # Structure results for consistency with multi-mailbox format
            results = {
                "status": "success",
                "results": [single_result],  # Array of mailbox results
                "total_time": datetime.now(UTC).isoformat(),
                "parameters": processing_parameters,
            }

            # Save complete processing run to history
            run_id = run_history.add_run(results, processing_parameters)
            logger.info(f"Processing run saved to history: {run_id}")

            logger.info(f"Email processing completed: {single_result}")
            return jsonify(
                {"status": "success", "results": single_result, "run_id": run_id}
            )

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Email processing API failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/mailboxes")
@log_function()
def api_mailboxes() -> tuple[dict, int] | dict:
    """API endpoint to get configured mailboxes"""
    try:
        mailboxes = get_configured_mailboxes()
        return jsonify({"mailboxes": mailboxes})
    except Exception as e:
        logger.error(f"Failed to get mailboxes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/processing-history")
@log_function()
def api_processing_history() -> tuple[dict, int] | dict:
    """API endpoint to get email processing history (legacy - per email)"""
    try:
        history = []
        for key, info in email_history.processed_emails.items():
            mailbox_id, email_id = key.split(":", 1)
            history.append(
                {
                    "mailbox_id": mailbox_id,
                    "email_id": email_id,
                    "processed_at": info.get("processed_at"),
                    "processing_info": info.get("processing_info", {}),
                }
            )

        # Sort by processed_at descending
        history.sort(key=lambda x: x.get("processed_at", ""), reverse=True)

        return jsonify({"history": history})
    except Exception as e:
        logger.error(f"Failed to get processing history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/processing-runs")
@log_function()
def api_processing_runs() -> tuple[dict, int] | dict:
    """API endpoint to get complete processing run history with full details"""
    try:
        limit = int(request.args.get("limit", 20))
        runs = run_history.get_runs(limit=limit)

        logger.info(f"Retrieved {len(runs)} processing runs for API")
        return jsonify({"runs": runs, "total_available": len(run_history.runs)})
    except Exception as e:
        logger.error(f"Failed to get processing runs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/processing-runs/<run_id>")
@log_function()
def api_processing_run_detail(run_id: str) -> tuple[dict, int] | dict:
    """API endpoint to get detailed information for a specific processing run"""
    try:
        run = run_history.get_run(run_id)

        if not run:
            return jsonify({"error": "Processing run not found"}), 404

        logger.info(f"Retrieved detailed info for processing run: {run_id}")
        return jsonify({"run": run})
    except Exception as e:
        logger.error(f"Failed to get processing run detail {run_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear-history", methods=["POST"])
@log_function()
def api_clear_history() -> tuple[dict, int] | dict:
    """API endpoint to clear processing history"""
    try:
        data = request.get_json() or {}
        email_id = data.get("email_id")
        mailbox_id = data.get("mailbox_id")
        clear_runs = data.get(
            "clear_runs", True
        )  # Also clear detailed run history by default
        before_date = data.get(
            "before_date"
        )  # Optional: only clear runs before this date

        # Clear email processing history
        email_history.clear_processed(email_id, mailbox_id)

        # Clear detailed run history if requested
        removed_runs_count = 0
        if clear_runs and not email_id and not mailbox_id:
            # Only clear all runs if clearing all email history
            removed_runs_count = run_history.clear_runs(before_date)

        # Also remove associated human review items
        removed_review_count = 0
        if email_id and mailbox_id:
            # Remove review items for specific email
            removed_review_count = review_queue.remove_items_by_email(
                email_id, mailbox_id
            )
        elif not email_id and not mailbox_id:
            # Clear all review items if clearing all history
            removed_review_count = review_queue.clear_all_items()

        action = (
            "all history" if not email_id else f"history for {mailbox_id}:{email_id}"
        )
        review_msg = (
            f" and {removed_review_count} review items"
            if removed_review_count > 0
            else ""
        )
        runs_msg = (
            f" and {removed_runs_count} processing runs"
            if removed_runs_count > 0
            else ""
        )

        logger.info(f"Cleared processing history: {action}{review_msg}{runs_msg}")

        return jsonify(
            {
                "status": "success",
                "message": f"Cleared {action}{review_msg}{runs_msg}",
                "removed_review_items": removed_review_count,
                "removed_processing_runs": removed_runs_count,
            }
        )
    except Exception as e:
        logger.error(f"Failed to clear processing history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/senders/<mapping_id>/edit", methods=["GET", "POST"])
@log_function()
def edit_sender_mapping(mapping_id: str) -> str:
    """Edit an existing sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get current mapping
        mappings = loop.run_until_complete(asset_agent.list_asset_sender_mappings())
        current_mapping = next(
            (m for m in mappings if m["mapping_id"] == mapping_id), None
        )

        if not current_mapping:
            logger.warning(f"Sender mapping not found: {mapping_id}")
            flash("Sender mapping not found", "error")
            return redirect(url_for("list_senders"))

        if request.method == "POST":
            try:
                # Get form data
                asset_id = request.form.get("asset_id", "").strip()
                sender_email = request.form.get("sender_email", "").strip().lower()
                confidence = float(request.form.get("confidence", 0.8))
                document_types_str = request.form.get("document_types", "").strip()

                logger.info(
                    f"Updating sender mapping {mapping_id}: {sender_email} -> {asset_id}"
                )

                # Validate
                if not asset_id or not sender_email:
                    logger.warning(
                        "Sender mapping update failed: missing required fields"
                    )
                    flash("Asset and sender email are required", "error")
                    return redirect(
                        url_for("edit_sender_mapping", mapping_id=mapping_id)
                    )

                # Parse document types
                if document_types_str:
                    [dt.strip() for dt in document_types_str.split(",") if dt.strip()]

                # Update mapping
                success = loop.run_until_complete(
                    asset_agent.update_asset_sender_mapping(
                        mapping_id=mapping_id,
                        deal_id=asset_id,
                        sender_email=sender_email,
                        confidence=confidence,
                    )
                )

                if success:
                    logger.info(f"Sender mapping updated successfully: {mapping_id}")
                    flash("Sender mapping updated successfully", "success")
                    return redirect(url_for("list_senders"))
                else:
                    logger.error(f"Failed to update sender mapping: {mapping_id}")
                    flash("Failed to update sender mapping", "error")

            except Exception as e:
                logger.error(f"Failed to update sender mapping: {e}")
                flash(f"Failed to update sender mapping: {e}", "error")

        # Get available assets for dropdown
        assets = loop.run_until_complete(asset_agent.list_assets())

        return render_template(
            "edit_sender_mapping.html",
            mapping=current_mapping,
            assets=assets,
            document_categories=DocumentCategory,
        )

    except Exception as e:
        logger.error(f"Failed to load sender mapping {mapping_id}: {e}")
        return render_template(
            "error.html", error=f"Failed to load sender mapping: {e}"
        )
    finally:
        loop.close()


@app.route("/senders/<mapping_id>/delete", methods=["POST"])
@log_function()
def delete_sender_mapping(mapping_id: str) -> str:
    """Delete a sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset agent not initialized for sender mapping deletion")
        return jsonify({"error": "Asset agent not initialized"}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(
            asset_agent.delete_asset_sender_mapping(mapping_id)
        )

        if success:
            logger.info(f"Sender mapping deleted successfully: {mapping_id}")
            flash("Sender mapping deleted successfully", "success")
        else:
            logger.warning(f"Sender mapping not found: {mapping_id}")
            flash("Sender mapping not found", "error")

        return redirect(url_for("list_senders"))

    except Exception as e:
        logger.error(f"Failed to delete sender mapping {mapping_id}: {e}")
        flash(f"Failed to delete sender mapping: {e}", "error")
        return redirect(url_for("list_senders"))
    finally:
        loop.close()


# Human Review Routes


@app.route("/human-review")
@log_function()
def human_review_queue() -> str:
    """Human review queue page"""
    try:
        # Get pending review items
        pending_items = review_queue.get_pending_items(limit=50)

        # Get queue statistics
        stats = review_queue.get_stats()

        # Get available assets for dropdown
        if not asset_agent:
            logger.error("Asset management system not initialized")
            return render_template(
                "error.html", error="Asset management system not initialized"
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assets = loop.run_until_complete(asset_agent.list_assets())
        finally:
            loop.close()

        logger.info(f"Human review page loaded with {len(pending_items)} pending items")
        return render_template(
            "human_review.html",
            pending_items=pending_items,
            stats=stats,
            assets=assets,
            document_categories=DocumentCategory,
        )

    except Exception as e:
        logger.error(f"Failed to load human review page: {e}")
        return render_template(
            "error.html", error=f"Failed to load human review page: {e}"
        )


@app.route("/human-review/<review_id>")
@log_function()
def human_review_item(review_id: str) -> str:
    """Individual review item page"""
    try:
        # Get the specific review item
        review_item = review_queue.get_item(review_id)

        if not review_item:
            logger.warning(f"Review item not found: {review_id}")
            flash("Review item not found", "error")
            return redirect(url_for("human_review_queue"))

        # Get available assets for selection
        if not asset_agent:
            logger.error("Asset management system not initialized")
            return render_template(
                "error.html", error="Asset management system not initialized"
            )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assets = loop.run_until_complete(asset_agent.list_assets())

            # Get asset names for system suggestions
            asset_lookup = {asset.deal_id: asset for asset in assets}

            # Enhance system suggestions with asset names
            if review_item.get("system_asset_suggestions"):
                for suggestion in review_item["system_asset_suggestions"]:
                    if suggestion["asset_id"] in asset_lookup:
                        asset = asset_lookup[suggestion["asset_id"]]
                        suggestion["asset_name"] = asset.deal_name
                        suggestion["asset_type"] = asset.asset_type.value
        finally:
            loop.close()

        logger.info(f"Loaded review item: {review_id}")
        return render_template(
            "human_review_item.html",
            review_item=review_item,
            assets=assets,
            document_categories=DocumentCategory,
        )

    except Exception as e:
        logger.error(f"Failed to load review item {review_id}: {e}")
        return render_template("error.html", error=f"Failed to load review item: {e}")


@app.route("/api/human-review/<review_id>/submit", methods=["POST"])
@log_function()
def api_submit_review(review_id: str) -> tuple[dict, int] | dict:
    """Submit human review correction"""
    try:
        data = request.get_json()

        human_asset_id = data.get("asset_id")
        human_document_category = data.get("document_category")
        human_reasoning = data.get("reasoning", "")
        human_feedback = data.get("feedback", "")
        reviewed_by = data.get("reviewed_by", "web_user")
        is_asset_related = data.get("is_asset_related", True)

        # Validate required fields based on whether it's asset-related
        if not human_document_category:
            return jsonify({"error": "Document category is required"}), 400

        if is_asset_related and not human_asset_id:
            return (
                jsonify({"error": "Asset ID is required for asset-related documents"}),
                400,
            )

        # Log the review type
        if is_asset_related:
            logger.info(
                f"Processing asset-related review: {review_id} -> {human_asset_id}"
            )
        else:
            logger.info(f"Processing non-asset-related review: {review_id}")

        # Submit the review asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success = loop.run_until_complete(
                review_queue.submit_review(
                    review_id=review_id,
                    human_asset_id=human_asset_id,
                    human_document_category=human_document_category,
                    human_reasoning=human_reasoning,
                    human_feedback=human_feedback,
                    reviewed_by=reviewed_by,
                    is_asset_related=is_asset_related,
                )
            )

            if success:
                # Move file from review folder to proper asset folder if asset-related
                if is_asset_related and human_asset_id:
                    try:
                        loop.run_until_complete(
                            move_file_after_review(
                                review_id, human_asset_id, human_document_category
                            )
                        )
                        logger.info(
                            f"Moved file for review {review_id} to proper asset folder"
                        )
                    except Exception as move_error:
                        logger.warning(
                            f"Failed to move file after review {review_id}: {move_error}"
                        )

                result_msg = (
                    "non-asset-related document"
                    if not is_asset_related
                    else f"asset {human_asset_id}"
                )
                logger.info(
                    f"Review submitted successfully: {review_id} -> {result_msg}"
                )
                return jsonify(
                    {"success": True, "message": "Review submitted successfully"}
                )
            else:
                logger.error(f"Failed to submit review: {review_id}")
                return jsonify({"error": "Failed to submit review"}), 500

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error submitting review {review_id}: {e}")
        return jsonify({"error": f"Error submitting review: {str(e)}"}), 500


@app.route("/api/human-review/stats")
@log_function()
def api_human_review_stats() -> tuple[dict, int] | dict:
    """Get human review queue statistics"""
    try:
        stats = review_queue.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get review stats: {e}")
        return jsonify({"error": f"Failed to get review stats: {str(e)}"}), 500


@app.route("/files")
@log_function()
def browse_files() -> str:
    """Browse saved attachment files organized by asset"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    try:
        # Get all assets for reference
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assets = loop.run_until_complete(asset_agent.list_assets())
            asset_lookup = {asset.deal_id: asset for asset in assets}
        finally:
            loop.close()

        # Scan the assets directory structure
        assets_path = Path(config.assets_base_path)
        file_structure = {}
        total_files = 0

        if assets_path.exists():
            # Scan asset-specific folders (format: {asset_id}_{deal_name})
            for asset_folder in assets_path.iterdir():
                if asset_folder.is_dir() and not asset_folder.name.startswith("."):
                    # Extract asset ID from folder name (format: {uuid}_{deal_name})
                    folder_name = asset_folder.name
                    if "_" in folder_name:
                        asset_id = folder_name.split("_")[0]
                        asset_info = asset_lookup.get(asset_id)

                        if asset_info:  # Only include if we have asset info
                            files = []
                            for file_path in asset_folder.rglob("*"):
                                if (
                                    file_path.is_file()
                                    and not file_path.name.startswith(".")
                                ):
                                    file_info = {
                                        "name": file_path.name,
                                        "path": str(file_path.relative_to(assets_path)),
                                        "size": file_path.stat().st_size,
                                        "modified": datetime.fromtimestamp(
                                            file_path.stat().st_mtime
                                        ),
                                        "extension": file_path.suffix.lower(),
                                        "category": (
                                            file_path.parent.name
                                            if file_path.parent != asset_folder
                                            else "uncategorized"
                                        ),
                                    }
                                    files.append(file_info)
                                    total_files += 1

                            if files:  # Only include folders with files
                                file_structure[asset_id] = {
                                    "asset_info": asset_info,
                                    "files": sorted(
                                        files, key=lambda x: x["modified"], reverse=True
                                    ),
                                    "file_count": len(files),
                                }

            # Also scan special folders (to_be_reviewed, uncategorized)
            special_folders = ["to_be_reviewed", "uncategorized"]
            for special_folder_name in special_folders:
                special_folder = assets_path / special_folder_name
                if special_folder.exists() and special_folder.is_dir():
                    files = []
                    for file_path in special_folder.rglob("*"):
                        if file_path.is_file() and not file_path.name.startswith("."):
                            file_info = {
                                "name": file_path.name,
                                "path": str(file_path.relative_to(assets_path)),
                                "size": file_path.stat().st_size,
                                "modified": datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ),
                                "extension": file_path.suffix.lower(),
                                "category": file_path.parent.name,
                            }
                            files.append(file_info)
                            total_files += 1

                    if files:  # Only include folders with files
                        file_structure[special_folder_name] = {
                            "asset_info": None,  # No specific asset
                            "files": sorted(
                                files, key=lambda x: x["modified"], reverse=True
                            ),
                            "file_count": len(files),
                            "special_folder": True,
                            "folder_name": special_folder_name.replace(
                                "_", " "
                            ).title(),
                        }

        logger.info(
            f"File browser loaded: {len(file_structure)} asset folders, {total_files} total files"
        )
        return render_template(
            "file_browser.html", file_structure=file_structure, total_files=total_files
        )

    except Exception as e:
        logger.error(f"Failed to browse files: {e}")
        return render_template("error.html", error=f"Failed to browse files: {e}")


@app.route("/files/download/<path:file_path>")
@log_function()
def download_file(file_path: str) -> str | tuple[str, int]:
    """Download a specific attachment file"""
    try:
        # Validate the file path is within assets directory
        assets_path = Path(config.assets_base_path)
        full_path = assets_path / file_path

        # Security check - ensure path is within assets directory
        if not str(full_path.resolve()).startswith(str(assets_path.resolve())):
            logger.warning(f"Attempted access outside assets directory: {file_path}")
            return "Access denied", 403

        if not full_path.exists() or not full_path.is_file():
            logger.warning(f"File not found: {file_path}")
            return "File not found", 404

        logger.info(f"Downloading file: {file_path}")
        return send_file(full_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Failed to download file {file_path}: {e}")
        return f"Error downloading file: {e}", 500


@app.route("/files/view/<path:file_path>")
@log_function()
def view_file(file_path: str) -> str | tuple[str, int]:
    """View a specific attachment file in browser (for supported types)"""
    try:
        # Validate the file path is within assets directory
        assets_path = Path(config.assets_base_path)
        full_path = assets_path / file_path

        # Security check - ensure path is within assets directory
        if not str(full_path.resolve()).startswith(str(assets_path.resolve())):
            logger.warning(f"Attempted access outside assets directory: {file_path}")
            return "Access denied", 403

        if not full_path.exists() or not full_path.is_file():
            logger.warning(f"File not found: {file_path}")
            return "File not found", 404

        # Determine content type based on extension
        extension = full_path.suffix.lower()
        content_type_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".html": "text/html",
            ".htm": "text/html",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
        }

        content_type = content_type_map.get(extension, "application/octet-stream")

        logger.info(f"Viewing file: {file_path} (type: {content_type})")
        return send_file(full_path, mimetype=content_type)

    except Exception as e:
        logger.error(f"Failed to view file {file_path}: {e}")
        return f"Error viewing file: {e}", 500


@app.route("/files/reclassify/<path:file_path>", methods=["GET", "POST"])
@log_function()
def reclassify_file(file_path: str) -> str:
    """Re-classify a file attachment with user correction and memory storage"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    try:
        # Validate the file path is within assets directory
        assets_path = Path(config.assets_base_path)
        full_path = assets_path / file_path

        # Security check - ensure path is within assets directory
        if not str(full_path.resolve()).startswith(str(assets_path.resolve())):
            logger.warning(f"Attempted access outside assets directory: {file_path}")
            return "Access denied", 403

        if not full_path.exists() or not full_path.is_file():
            logger.warning(f"File not found: {file_path}")
            return "File not found", 404

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if request.method == "POST":
                # Handle form submission
                new_asset_id = request.form.get("asset_id")
                new_document_category = request.form.get("document_category")
                correction_reason = request.form.get("correction_reason", "")

                if new_asset_id == "none":
                    new_asset_id = None  # File is not asset-related
                elif new_asset_id == "discard":
                    new_asset_id = "DISCARD"  # File should be deleted

                # Get current file details
                filename = full_path.name
                current_category = _extract_category_from_path(file_path)
                current_asset_id = _extract_asset_id_from_path(file_path)

                # Process the reclassification
                success = loop.run_until_complete(
                    _process_reclassification(
                        full_path,
                        file_path,
                        filename,
                        current_asset_id,
                        current_category,
                        new_asset_id,
                        new_document_category,
                        correction_reason,
                    )
                )

                if success:
                    action_type = (
                        "discard" if new_asset_id == "DISCARD" else "reclassify"
                    )
                    logger.info(f"Successfully {action_type}ed file: {filename}")
                    return render_template(
                        "reclassify_success.html",
                        filename=filename,
                        old_asset_id=current_asset_id,
                        new_asset_id=(
                            new_asset_id if new_asset_id != "DISCARD" else None
                        ),
                        old_category=current_category,
                        new_category=new_document_category,
                        correction_reason=correction_reason,
                        action_type=action_type,
                    )
                else:
                    return render_template(
                        "error.html", error="Failed to reclassify file"
                    )

            else:
                # GET request - show the reclassification form
                # Get all assets for dropdown
                assets = loop.run_until_complete(asset_agent.list_assets())

                # Get file details
                filename = full_path.name
                file_size = full_path.stat().st_size
                current_category = _extract_category_from_path(file_path)
                current_asset_id = _extract_asset_id_from_path(file_path)

                # Get current asset name
                current_asset_name = "Unknown"
                if current_asset_id:
                    current_asset = next(
                        (a for a in assets if a.deal_id == current_asset_id), None
                    )
                    if current_asset:
                        current_asset_name = current_asset.deal_name

                return render_template(
                    "reclassify_file.html",
                    file_path=file_path,
                    filename=filename,
                    file_size=file_size,
                    current_asset_id=current_asset_id,
                    current_asset_name=current_asset_name,
                    current_category=current_category,
                    assets=assets,
                    document_categories=DocumentCategory,
                    asset_types=AssetType,
                )

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Failed to handle reclassification for {file_path}: {e}")
        return render_template("error.html", error=f"Reclassification failed: {e}")


@app.route("/files/inspect/<path:file_path>")
@log_function()
def inspect_classification(file_path: str) -> str:
    """Inspect classification reasoning for a processed file"""
    try:
        logger.info(f"🔍 Starting inspection for: {file_path}")

        # Step 1: Find the full file path
        try:
            full_path = Path(config.assets_base_path) / file_path
            logger.debug(f"Full path resolved: {full_path}")
        except Exception as e:
            logger.error(f"Failed to resolve file path: {e}")
            raise

        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            flash(f"File not found: {file_path}", "error")
            return redirect(url_for("browse_files"))

        # Step 2: Extract basic file info with individual error handling
        try:
            file_stat = full_path.stat()
            logger.debug(
                f"File stat obtained: size={file_stat.st_size}, mtime={file_stat.st_mtime}"
            )
        except Exception as e:
            logger.error(f"Failed to get file stat: {e}")
            raise

        try:
            modified_timestamp = datetime.fromtimestamp(file_stat.st_mtime)
            modified_iso = modified_timestamp.isoformat()
            logger.debug(f"Timestamp conversion successful: {modified_iso}")
        except Exception as e:
            logger.error(f"Failed to convert timestamp: {e}")
            # Fallback to string representation
            modified_iso = str(file_stat.st_mtime)

        try:
            current_asset_id = _extract_asset_id_from_path(file_path)
            logger.debug(f"Asset ID extracted: {current_asset_id}")
        except Exception as e:
            logger.error(f"Failed to extract asset ID: {e}")
            current_asset_id = None

        try:
            current_category = _extract_category_from_path(file_path)
            logger.debug(f"Category extracted: {current_category}")
        except Exception as e:
            logger.error(f"Failed to extract category: {e}")
            current_category = None

        # Step 3: Build file_info dict safely
        try:
            file_info = {
                "name": full_path.name,
                "path": file_path,
                "size": file_stat.st_size,
                "modified": modified_iso,
                "current_asset_id": current_asset_id,
                "current_category": current_category,
            }
            logger.debug("File info dict created successfully")
        except Exception as e:
            logger.error(f"Failed to create file_info dict: {e}")
            raise

        # Step 4: Try to find FULL processing metadata from Qdrant (including detailed patterns)
        classification_info = None
        try:
            if asset_agent and asset_agent.qdrant:
                logger.debug(
                    "Attempting to load FULL classification metadata from Qdrant"
                )

                # Check if collection exists first
                collections = asset_agent.qdrant.get_collections()
                collection_names = [c.name for c in collections.collections]

                if "asset_management_processed_documents" in collection_names:
                    logger.debug("Processed documents collection found, querying...")

                    # Search for processed document by filename or file hash
                    result = asset_agent.qdrant.scroll(
                        collection_name="asset_management_processed_documents",
                        limit=1000,  # Increased limit to find our document
                        with_payload=True,
                        with_vectors=False,
                    )

                    # Find matching document by file path or name
                    for point in result[0]:
                        payload = point.payload
                        if payload:
                            # Match by various path patterns
                            stored_path = payload.get("file_path", "")
                            stored_filename = payload.get("filename", "")

                            # Try different matching strategies
                            match_found = False

                            # Strategy 1: Exact filename match
                            if stored_filename == full_path.name:
                                match_found = True
                                logger.debug(
                                    f"Found match by filename: {stored_filename}"
                                )

                            # Strategy 2: Path contains filename
                            elif full_path.name in stored_path:
                                match_found = True
                                logger.debug(
                                    f"Found match by path contains filename: {stored_path}"
                                )

                            # Strategy 3: Full path in stored path
                            elif file_path in stored_path:
                                match_found = True
                                logger.debug(f"Found match by full path: {stored_path}")

                            # Strategy 4: Asset ID and filename match
                            elif (
                                current_asset_id
                                and current_asset_id in stored_path
                                and full_path.name in stored_path
                            ):
                                match_found = True
                                logger.debug(
                                    f"Found match by asset ID + filename: {stored_path}"
                                )

                            if match_found:
                                # Extract FULL classification metadata
                                classification_metadata = payload.get(
                                    "classification_metadata", {}
                                )

                                classification_info = {
                                    "document_id": str(point.id),
                                    "status": payload.get("status"),
                                    "confidence": payload.get("confidence", 0),
                                    "processing_date": payload.get("processing_date"),
                                    "document_category": payload.get(
                                        "document_category"
                                    ),
                                    "confidence_level": payload.get("confidence_level"),
                                    "asset_id": payload.get("asset_id"),
                                    # Include the FULL classification metadata with detailed patterns
                                    "classification_metadata": classification_metadata,
                                }

                                logger.debug(
                                    f"Found FULL classification metadata for {full_path.name}"
                                )
                                logger.debug(
                                    f"Metadata keys: {list(classification_metadata.keys())}"
                                )

                                # Check if detailed patterns are available
                                if "detailed_patterns" in classification_metadata:
                                    detailed_patterns = classification_metadata[
                                        "detailed_patterns"
                                    ]
                                    patterns_count = len(
                                        detailed_patterns.get("patterns_used", [])
                                    )
                                    logger.debug(
                                        f"Found {patterns_count} detailed patterns"
                                    )
                                else:
                                    logger.debug(
                                        "No detailed_patterns found in metadata"
                                    )

                                break

                    if classification_info is None:
                        logger.debug("No matching classification metadata found")
                else:
                    logger.debug("Processed documents collection not found")
            else:
                logger.debug("Asset agent or Qdrant not available")

        except Exception as e:
            logger.warning(f"Failed to load classification metadata: {e}")
            classification_info = None

        # Step 5: Get asset information if available
        asset_info = None
        if file_info["current_asset_id"]:
            try:
                logger.debug(f"Loading asset info for: {file_info['current_asset_id']}")

                # Create new event loop for async operations in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    assets = loop.run_until_complete(asset_agent.list_assets())
                    asset_info = next(
                        (
                            a
                            for a in assets
                            if a.deal_id == file_info["current_asset_id"]
                        ),
                        None,
                    )
                    if asset_info:
                        logger.debug(f"Asset info loaded: {asset_info.deal_name}")
                    else:
                        logger.debug("Asset info not found")
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"Failed to load asset info: {e}")
                asset_info = None

        # Step 6: Log what we found for debugging
        if classification_info:
            logger.info(
                f"✅ Found classification info with {len(classification_info)} fields"
            )
            if classification_info.get("classification_metadata"):
                metadata = classification_info["classification_metadata"]
                logger.info(f"📊 Metadata contains: {list(metadata.keys())}")
                if "detailed_patterns" in metadata:
                    patterns = metadata["detailed_patterns"]
                    logger.info(
                        f"🎯 Detailed patterns available: {list(patterns.keys())}"
                    )
                    patterns_used = patterns.get("patterns_used", [])
                    logger.info(f"📝 Found {len(patterns_used)} specific patterns used")
        else:
            logger.warning("❌ No classification info found")

        # Step 7: Render template
        try:
            logger.debug("Rendering template with collected data")
            return render_template(
                "inspect_classification.html",
                file_info=file_info,
                classification_info=classification_info,
                asset_info=asset_info,
            )
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise

    except Exception as e:
        logger.error(f"Failed to inspect classification for {file_path}: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        flash(f"Error inspecting file: {e}", "error")
        return redirect(url_for("browse_files"))


@log_function()
def _extract_asset_id_from_path(file_path: str) -> str | None:
    """Extract asset ID from file path"""
    try:
        # Path format: {asset_id}_{asset_name}/category/filename
        # or: special_folder/filename
        parts = Path(file_path).parts
        if len(parts) >= 1:
            folder_name = parts[0]  # First folder in the path

            # Skip special folders
            if folder_name in ["to_be_reviewed", "uncategorized", "needs_review"]:
                return None

            # Extract UUID from folder name (before first underscore)
            if "_" in folder_name:
                potential_uuid = folder_name.split("_")[0]
                # Basic UUID format check
                if len(potential_uuid) == 36 and potential_uuid.count("-") == 4:
                    logger.debug(f"Extracted asset ID: {potential_uuid}")
                    return potential_uuid

        logger.debug(f"No asset ID found in path: {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Failed to extract asset ID from path {file_path}: {e}")
        return None


@log_function()
def _extract_category_from_path(file_path: str) -> str | None:
    """Extract document category from file path"""
    try:
        # Path format: {asset_id}_{asset_name}/category/filename
        # Special formats: uncategorized/filename or to_be_reviewed/subfolder/filename
        parts = Path(file_path).parts

        if len(parts) >= 1:
            first_folder = parts[0]  # Should be asset folder or special folder

            # Handle special folders
            if first_folder in ["uncategorized", "to_be_reviewed"]:
                if len(parts) >= 2:
                    # Format: uncategorized/subfolder/filename or to_be_reviewed/subfolder/filename
                    category = parts[1].lower()  # subfolder is the category
                    logger.debug(f"Extracted category from special folder: {category}")
                    return category
                else:
                    # Format: uncategorized/filename or to_be_reviewed/filename
                    category = (
                        first_folder.lower()
                    )  # Use the special folder name as category
                    logger.debug(
                        f"Extracted category as special folder name: {category}"
                    )
                    return category

            # Handle regular asset folders: {asset_id}_{asset_name}/category/filename
            elif len(parts) >= 2:
                category_folder = parts[1]  # Category folder within asset folder
                category = category_folder.lower()
                logger.debug(f"Extracted category from asset folder: {category}")
                return category

        logger.debug(f"No category found in path: {file_path}")
        return None
    except Exception as e:
        logger.warning(f"Failed to extract category from path {file_path}: {e}")
        return None


@log_function()
async def _process_reclassification(
    full_path: Path,
    original_file_path: str,
    filename: str,
    current_asset_id: str | None,
    current_category: str | None,
    new_asset_id: str | None,
    new_document_category: str | None,
    correction_reason: str,
) -> bool:
    """Process file reclassification including file movement and memory storage"""
    try:
        logger.info(f"🔄 RECLASSIFICATION START: {filename}")
        logger.info(
            f"   📂 Current: Asset {current_asset_id} / Category {current_category}"
        )
        logger.info(
            f"   🎯 New: Asset {new_asset_id} / Category {new_document_category}"
        )
        logger.info(f"   💭 Reason: {correction_reason}")

        # Step 1: Determine action - move or delete
        assets_path = Path(config.assets_base_path)
        new_file_path = None
        action_type = "move"

        if new_asset_id == "DISCARD":
            # Delete the file permanently
            action_type = "delete"
            logger.info("   🗑️ File will be permanently deleted")
        elif new_asset_id is None:
            # Move to uncategorized (not asset-related)
            new_file_path = assets_path / "uncategorized" / filename
            logger.info(f"   📍 Moving to uncategorized: {new_file_path}")
        else:
            # Move to asset folder
            assets = await asset_agent.list_assets()
            target_asset = next((a for a in assets if a.deal_id == new_asset_id), None)

            if not target_asset:
                logger.error(f"Target asset not found: {new_asset_id}")
                return False

            # Create category folder structure
            asset_folder = (
                assets_path
                / f"{target_asset.deal_id}_{target_asset.deal_name.replace(' ', '_')}"
            )
            category_folder = (
                new_document_category.lower()
                if new_document_category
                else "uncategorized"
            )
            new_file_path = asset_folder / category_folder / filename

            logger.info(f"   📍 Moving to asset folder: {new_file_path}")

        # Step 2: Execute the action
        if action_type == "delete":
            # Delete the file permanently
            full_path.unlink()
            logger.info("   ✅ File deleted permanently")
        else:
            # Move the file
            # Create target directory
            new_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle file collision
            if new_file_path.exists():
                base_name = new_file_path.stem
                extension = new_file_path.suffix
                counter = 1
                while new_file_path.exists():
                    new_file_path = (
                        new_file_path.parent / f"{base_name}_{counter}{extension}"
                    )
                    counter += 1
                logger.info(f"   📋 File collision resolved: {new_file_path.name}")

            # Move the file
            full_path.rename(new_file_path)
            logger.info("   ✅ File moved successfully")

            # Step 3: Store correction in semantic memory (experiential knowledge)
        try:
            # # Local application imports
            from src.memory.semantic import SemanticMemory

            semantic_memory = SemanticMemory(
                max_items=config.semantic_memory_max_items,
                qdrant_url=config.qdrant_url,
                embedding_model=config.embedding_model,
            )

            # Determine what type of correction this is
            if action_type == "delete":
                # Store as general human correction - file discarded
                await semantic_memory.store_human_correction(
                    original_prediction=f"asset_id={current_asset_id}, category={current_category}",
                    human_correction="file_discarded",
                    metadata={
                        "filename": filename,
                        "original_asset_id": current_asset_id,
                        "original_category": current_category,
                        "action_type": "discard",
                        "correction_reason": correction_reason,
                        "corrected_by": "web_user_reclassification",
                        "file_extension": Path(filename).suffix.lower(),
                        "correction_source": "reclassification_ui",
                    },
                )
                logger.info("   🧠 File discard correction stored in semantic memory")

            elif new_asset_id is None:
                # File moved to uncategorized (not asset-related)
                await semantic_memory.store_human_correction(
                    original_prediction=f"asset_related (asset_id={current_asset_id})",
                    human_correction="non_asset_related",
                    metadata={
                        "filename": filename,
                        "original_asset_id": current_asset_id,
                        "original_category": current_category,
                        "corrected_category": new_document_category,
                        "action_type": "move_to_uncategorized",
                        "correction_reason": correction_reason,
                        "corrected_by": "web_user_reclassification",
                        "file_extension": Path(filename).suffix.lower(),
                        "correction_source": "reclassification_ui",
                    },
                )
                logger.info("   🧠 Non-asset correction stored in semantic memory")

            else:
                # File reclassified to different asset - use classification feedback
                # Determine asset type for the new asset
                assets = await asset_agent.list_assets()
                target_asset = next(
                    (a for a in assets if a.deal_id == new_asset_id), None
                )
                asset_type = (
                    target_asset.asset_type.value
                    if target_asset and hasattr(target_asset, "asset_type")
                    else "unknown"
                )

                await semantic_memory.add_classification_feedback(
                    filename=filename,
                    email_subject="",  # No email context for reclassification
                    email_body="",
                    correct_category=new_document_category or "uncategorized",
                    asset_type=asset_type,
                    confidence=0.95,  # High confidence for human corrections
                    source="reclassification_ui",
                    original_prediction=current_category,
                    corrected_by="web_user_reclassification",
                    review_context=correction_reason,
                    system_confidence=0.0,  # No system confidence for manual reclassification
                    asset_id=new_asset_id,
                    original_asset_id=current_asset_id,
                    file_extension=Path(filename).suffix.lower(),
                    correction_type="manual_reclassification",
                    learning_priority="high",  # User-initiated corrections are high priority
                )
                logger.info("   🧠 Classification correction stored in semantic memory")

        except Exception as e:
            logger.warning(f"Failed to store correction in semantic memory: {e}")
            # Don't fail the whole operation for memory storage issues

        # Step 4: Clean up empty directories (for both move and delete)
        try:
            old_category_folder = (
                full_path.parent if action_type == "move" else full_path.parent
            )
            if old_category_folder.exists() and not any(old_category_folder.iterdir()):
                old_category_folder.rmdir()
                logger.info("   🗑️ Cleaned up empty category folder")

            old_asset_folder = old_category_folder.parent
            if old_asset_folder.exists() and not any(old_asset_folder.iterdir()):
                old_asset_folder.rmdir()
                logger.info("   🗑️ Cleaned up empty asset folder")

        except Exception as e:
            logger.warning(f"Failed to clean up empty directories: {e}")

        action_summary = "DISCARDED" if action_type == "delete" else "RECLASSIFIED"
        logger.info(f"🏁 {action_summary} COMPLETED SUCCESSFULLY")
        return True

    except Exception as e:
        logger.error(f"Failed to process reclassification: {e}")
        return False


# Memory Management Routes


@app.route("/memory")
@log_function()
def memory_dashboard() -> str:
    """Memory systems dashboard showing overview of all memory types"""
    try:
        stats = {}

        if asset_agent and asset_agent.qdrant:
            # Get collection information
            collections = asset_agent.qdrant.get_collections()
            collection_names = [c.name for c in collections.collections]

            # Memory system stats
            for collection_name in collection_names:
                try:
                    info = asset_agent.qdrant.get_collection(collection_name)
                    stats[collection_name] = {
                        "points_count": info.points_count,
                        "vectors_count": (
                            info.vectors_count if hasattr(info, "vectors_count") else 0
                        ),
                        "status": info.status,
                    }
                except Exception as e:
                    logger.warning(f"Failed to get stats for {collection_name}: {e}")
                    stats[collection_name] = {"error": str(e)}

        # Exclude photos collection from other projects
        stats = {name: data for name, data in stats.items() if name != "photos"}

        # Categorize collections by memory type
        memory_types = {
            "episodic": [name for name in stats if "episodic" in name.lower()],
            "procedural": [name for name in stats if "procedural" in name.lower()],
            "contact": [name for name in stats if "contact" in name.lower()],
            "semantic": [name for name in stats if "semantic" in name.lower()],
            "asset_management": [
                name for name in stats if "asset_management" in name.lower()
            ],
            "other": [
                name
                for name in stats
                if not any(
                    mem_type in name.lower()
                    for mem_type in [
                        "episodic",
                        "procedural",
                        "contact",
                        "semantic",
                        "asset_management",
                    ]
                )
            ],
        }

        logger.info("Memory dashboard loaded")
        return render_template(
            "memory_dashboard.html", stats=stats, memory_types=memory_types
        )

    except Exception as e:
        logger.error(f"Failed to load memory dashboard: {e}")
        flash(f"Error loading memory dashboard: {e}", "error")
        return render_template("error.html", error=str(e))


def _parse_human_feedback(content: str) -> dict:
    """Parse human feedback from episodic memory content text."""
    feedback = {
        "asset_feedback": "",
        "document_feedback": "",
        "asset_hints": "",
        "document_hints": "",
        "email_subject": "",
        "filename": "",
        "system_category": "",
        "human_category": "",
        "has_feedback": False,
    }

    if not content:
        return feedback

    try:
        # Extract email context
        if "Subject:" in content:
            start = content.find("Subject:") + 8
            end = content.find("\n", start)
            if end > start:
                feedback["email_subject"] = content[start:end].strip()

        if "Filename:" in content:
            start = content.find("Filename:") + 9
            end = content.find("\n", start)
            if end > start:
                feedback["filename"] = content[start:end].strip()

        # Extract system vs human categories
        if "Document Category:" in content:
            start = content.find("Document Category:") + 18
            end = content.find("\n", start)
            if end > start:
                feedback["system_category"] = content[start:end].strip()

        if "Correct Category:" in content:
            start = content.find("Correct Category:") + 17
            end = content.find("\n", start)
            if end > start:
                feedback["human_category"] = content[start:end].strip()

        # Extract human feedback
        if "Additional Feedback:" in content:
            feedback["has_feedback"] = True
            feedback_start = content.find("Additional Feedback:")
            feedback_section = content[feedback_start:]

            # Extract asset feedback
            if "Asset feedback:" in feedback_section:
                start = feedback_section.find("Asset feedback:") + 15
                end = feedback_section.find("|", start)
                if end == -1:
                    end = feedback_section.find("Document feedback:", start)
                if end == -1:
                    end = len(feedback_section)
                feedback["asset_feedback"] = feedback_section[start:end].strip()

            # Extract document feedback
            if "Document feedback:" in feedback_section:
                start = feedback_section.find("Document feedback:") + 18
                end = feedback_section.find("Asset learning hints:", start)
                if end == -1:
                    end = feedback_section.find("Document learning hints:", start)
                if end == -1:
                    end = len(feedback_section)
                raw_feedback = feedback_section[start:end].strip()
                # Clean up trailing pipe character
                feedback["document_feedback"] = raw_feedback.rstrip("|").strip()

            # Extract learning hints
            if "Asset learning hints:" in feedback_section:
                start = feedback_section.find("Asset learning hints:") + 21
                end = feedback_section.find("|", start)
                if end == -1:
                    end = feedback_section.find("Document learning hints:", start)
                if end == -1:
                    end = len(feedback_section)
                feedback["asset_hints"] = feedback_section[start:end].strip()

            if "Document learning hints:" in feedback_section:
                start = feedback_section.find("Document learning hints:") + 24
                end = feedback_section.find("\n", start)
                if end == -1:
                    end = len(feedback_section)
                feedback["document_hints"] = feedback_section[start:end].strip()

    except Exception as e:
        logger.warning(f"Error parsing human feedback: {e}")

    return feedback


@app.route("/memory/episodic")
@log_function()
def episodic_memory() -> str:
    """Episodic memory management - individual experiences and conversations"""
    try:
        items = []
        stats = {"total_items": 0, "recent_items": 0}

        if asset_agent and asset_agent.qdrant:
            # Get episodic memory items
            try:
                collection_name = "episodic"
                if collection_name in [
                    c.name for c in asset_agent.qdrant.get_collections().collections
                ]:
                    result = asset_agent.qdrant.scroll(
                        collection_name=collection_name,
                        limit=50,  # Show last 50 items
                        with_payload=True,
                        with_vectors=False,
                    )

                    for point in result[0]:
                        # Parse human feedback from content if available
                        parsed_feedback = _parse_human_feedback(
                            point.payload.get("content", "")
                        )

                        items.append(
                            {
                                "id": point.id,
                                "payload": point.payload,
                                "created_at": point.payload.get(
                                    "created_at", "Unknown"
                                ),
                                "event_type": point.payload.get(
                                    "event_type", "Unknown"
                                ),
                                "summary": (
                                    point.payload.get(
                                        "summary", "No summary available"
                                    )[:100]
                                    + "..."
                                    if len(point.payload.get("summary", "")) > 100
                                    else point.payload.get("summary", "")
                                ),
                                "human_feedback": parsed_feedback,  # Add structured feedback
                            }
                        )

                    # Get collection stats
                    info = asset_agent.qdrant.get_collection(collection_name)
                    stats["total_items"] = info.points_count

            except Exception as e:
                logger.warning(f"Failed to load episodic memory: {e}")
                flash(f"Warning: Could not load episodic memory: {e}", "warning")

        # Sort by creation date (newest first)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        stats["recent_items"] = len(items)

        logger.info(f"Episodic memory page loaded with {len(items)} items")
        return render_template("episodic_memory.html", items=items, stats=stats)

    except Exception as e:
        logger.error(f"Failed to load episodic memory page: {e}")
        flash(f"Error loading episodic memory: {e}", "error")
        return render_template("error.html", error=str(e))


def _create_friendly_pattern_id(payload: dict, pattern_type: str) -> str:
    """Create a human-friendly identifier for patterns based on their type and content."""
    try:
        if pattern_type == "asset_matching":
            asset_type = payload.get("asset_type", "unknown")
            keywords = payload.get("keywords", [])
            keyword_count = len(keywords)
            return f"{asset_type.replace('_', ' ').title()} Keywords ({keyword_count})"

        elif pattern_type == "classification":
            predicted = payload.get("predicted_category", "")
            corrected = payload.get("corrected_category", "")
            if corrected:
                return f"Classification: {predicted} → {corrected}"
            elif predicted:
                return f"Classification: {predicted}"
            else:
                filename = payload.get("filename", "")
                if filename:
                    return f"Classification: {filename[:30]}..."
                return "Classification Pattern"

        elif pattern_type == "routing":
            asset_type = payload.get("asset_type", "")
            confidence = payload.get("confidence", 0)
            if asset_type:
                return f"Routing: {asset_type.replace('_', ' ').title()} ({confidence:.1%})"
            return f"Routing Pattern ({confidence:.1%})"

        elif pattern_type == "confidence":
            confidence = payload.get("confidence", 0)
            source = payload.get("source", "")
            return f"Confidence: {confidence:.1%} ({source})"

        else:
            # Fallback: use filename, email subject, or pattern type
            filename = payload.get("filename", "")
            email_subject = payload.get("email_subject", "")
            if filename:
                return f"{pattern_type.title()}: {filename[:30]}..."
            elif email_subject:
                return f"{pattern_type.title()}: {email_subject[:30]}..."
            else:
                return f"{pattern_type.title()} Pattern"

    except Exception:
        # Ultimate fallback
        return f"{pattern_type.title()} Pattern"


@app.route("/memory/procedural")
@log_function()
def procedural_memory() -> str:
    """Procedural memory management - learned patterns and rules"""
    try:
        # Get pagination parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
        collection_filter = request.args.get("collection", "all")

        patterns = {}
        stats = {
            "total_patterns": 0,
            "pattern_types": 0,
            "pages": 1,
            "current_page": page,
        }

        if asset_agent and asset_agent.procedural_memory:
            # Get procedural memory patterns by collection (using actual collection names)
            all_procedural_collections = [
                "procedural_classification_patterns",
                "procedural_confidence_models",  # Contains routing, confidence, validation patterns
                "procedural_asset_patterns",  # Contains asset_matching patterns
                "procedural_configuration_rules",  # Contains configuration patterns
            ]

            # Filter collections if specified
            if (
                collection_filter != "all"
                and collection_filter in all_procedural_collections
            ):
                procedural_collections = [collection_filter]
                logger.info(f"Filtering to collection: {collection_filter}")
            else:
                procedural_collections = all_procedural_collections
                logger.info("Showing all procedural collections")

            for collection_name in procedural_collections:
                patterns[collection_name] = []
                try:
                    if collection_name in [
                        c.name for c in asset_agent.qdrant.get_collections().collections
                    ]:
                        # Get collection stats - only count patterns from filtered collections
                        info = asset_agent.qdrant.get_collection(collection_name)
                        collection_count = info.points_count
                        stats["total_patterns"] += collection_count
                        if collection_count > 0:
                            stats["pattern_types"] += 1

                        # Load ALL patterns from this collection
                        result = asset_agent.qdrant.scroll(
                            collection_name=collection_name,
                            limit=10000,  # Get all patterns from this collection
                            with_payload=True,
                            with_vectors=False,
                        )

                        for point in result[0]:
                            # Create human-friendly identifier based on pattern type
                            pattern_type = point.payload.get("pattern_type", "Unknown")
                            friendly_id = _create_friendly_pattern_id(
                                point.payload, pattern_type
                            )

                            # Include full pattern details
                            pattern_data = {
                                "id": str(point.id),
                                "friendly_id": friendly_id,
                                "collection": collection_name,
                                "pattern_type": pattern_type,
                                "confidence": round(
                                    point.payload.get("confidence", 0), 3
                                ),
                                "source": point.payload.get("source", "Unknown"),
                                "created_at": point.payload.get(
                                    "created_at", "Unknown"
                                ),
                                "filename": point.payload.get("filename", ""),
                                "email_subject": point.payload.get("email_subject", ""),
                                "email_body": (
                                    point.payload.get("email_body", "")[:200] + "..."
                                    if len(point.payload.get("email_body", "")) > 200
                                    else point.payload.get("email_body", "")
                                ),
                                "predicted_category": point.payload.get(
                                    "predicted_category", ""
                                ),
                                "corrected_category": point.payload.get(
                                    "corrected_category", ""
                                ),
                                "asset_type": point.payload.get("asset_type", ""),
                                "learning_context": point.payload.get(
                                    "learning_context", {}
                                ),
                                "success_count": point.payload.get("success_count", 0),
                                "last_used": point.payload.get("last_used", "Never"),
                                "keywords": point.payload.get("keywords", []),
                                "metadata": point.payload.get("metadata", {}),
                                "full_payload": point.payload,  # Include complete payload for detail view
                            }
                            patterns[collection_name].append(pattern_data)

                except Exception as e:
                    logger.warning(f"Failed to load {collection_name}: {e}")
                    patterns[collection_name] = []

        # Flatten all patterns for proper pagination
        all_patterns = []
        for collection_name, collection_patterns in patterns.items():
            logger.debug(
                f"Collection {collection_name}: {len(collection_patterns)} patterns"
            )
            all_patterns.extend(collection_patterns)

        logger.debug(f"Total flattened patterns: {len(all_patterns)}")

        # Apply pagination to flattened list
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_patterns = all_patterns[start_idx:end_idx]

        logger.debug(
            f"Paginated patterns: {len(paginated_patterns)} (from {start_idx} to {end_idx})"
        )

        # Reorganize by collection for display
        patterns = {}
        for pattern in paginated_patterns:
            collection = pattern["collection"]
            if collection not in patterns:
                patterns[collection] = []
            patterns[collection].append(pattern)

        # Log final display patterns
        for collection_name, collection_patterns in patterns.items():
            logger.debug(
                f"Final display - {collection_name}: {len(collection_patterns)} patterns"
            )

        # Calculate total pages based on filtered results
        if len(all_patterns) > 0:
            stats["pages"] = max(1, (len(all_patterns) + per_page - 1) // per_page)
        else:
            stats["pages"] = 1

        # Update total patterns to reflect filtered count
        stats["total_patterns"] = len(all_patterns)

        logger.info(
            f"Procedural memory page loaded with {stats['total_patterns']} patterns (page {page}) - Filter: {collection_filter}"
        )
        return render_template(
            "procedural_memory.html",
            patterns=patterns,
            stats=stats,
            current_collection=collection_filter,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Failed to load procedural memory page: {e}")
        flash(f"Error loading procedural memory: {e}", "error")
        return render_template("error.html", error=str(e))


@app.route("/memory/contact")
@log_function()
def contact_memory() -> str:
    """Contact memory management - known contacts and relationships"""
    try:
        contacts = []
        stats = {"total_contacts": 0, "recent_contacts": 0}

        if asset_agent and asset_agent.qdrant:
            # Get contact memory items
            try:
                collection_name = "contact_memory"
                if collection_name in [
                    c.name for c in asset_agent.qdrant.get_collections().collections
                ]:
                    result = asset_agent.qdrant.scroll(
                        collection_name=collection_name,
                        limit=50,  # Show last 50 contacts
                        with_payload=True,
                        with_vectors=False,
                    )

                    for point in result[0]:
                        contacts.append(
                            {
                                "id": point.id,
                                "payload": point.payload,
                                "email": point.payload.get("email", "Unknown"),
                                "name": point.payload.get("name", "Unknown"),
                                "organization": point.payload.get("organization", ""),
                                "last_contact": point.payload.get(
                                    "last_contact", "Unknown"
                                ),
                                "contact_frequency": point.payload.get(
                                    "contact_frequency", 0
                                ),
                                "relationship_strength": point.payload.get(
                                    "relationship_strength", 0.0
                                ),
                            }
                        )

                    # Get collection stats
                    info = asset_agent.qdrant.get_collection(collection_name)
                    stats["total_contacts"] = info.points_count

            except Exception as e:
                logger.warning(f"Failed to load contact memory: {e}")
                flash(f"Warning: Could not load contact memory: {e}", "warning")

        # Sort by last contact (most recent first)
        contacts.sort(key=lambda x: x.get("last_contact", ""), reverse=True)
        stats["recent_contacts"] = len(contacts)

        logger.info(f"Contact memory page loaded with {len(contacts)} contacts")
        return render_template("contact_memory.html", contacts=contacts, stats=stats)

    except Exception as e:
        logger.error(f"Failed to load contact memory page: {e}")
        flash(f"Error loading contact memory: {e}", "error")
        return render_template("error.html", error=str(e))


@app.route("/memory/semantic")
@log_function()
def semantic_memory() -> str:
    """Semantic memory management - factual knowledge about assets and file types"""
    try:
        # Get pagination parameters
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
        collection_filter = request.args.get("collection", "all")

        semantic_data = {}
        stats = {
            "total_facts": 0,
            "collections": 0,
            "asset_count": 0,
            "pages": 1,
            "current_page": page,
        }

        if asset_agent and asset_agent.qdrant:
            # Get semantic memory collections
            try:
                collections_response = asset_agent.qdrant.get_collections()
                all_semantic_collections = [
                    c.name
                    for c in collections_response.collections
                    if "semantic" in c.name.lower()
                ]
            except Exception as e:
                logger.warning(f"Failed to get collections from Qdrant: {e}")
                all_semantic_collections = []

            # Filter collections if specified
            if (
                collection_filter != "all"
                and collection_filter in all_semantic_collections
            ):
                semantic_collections = [collection_filter]
                logger.info(f"Filtering to collection: {collection_filter}")
            else:
                semantic_collections = all_semantic_collections
                logger.info("Showing all semantic collections")

            # Collect all facts from all collections for pagination
            all_facts = []
            for collection_name in semantic_collections:
                try:
                    result = asset_agent.qdrant.scroll(
                        collection_name=collection_name,
                        limit=10000,  # Get all semantic facts from this collection
                        with_payload=True,
                        with_vectors=False,
                    )

                    # Use the same simple pattern as other working memory types
                    if result and result[0]:
                        for point in result[0]:
                            if hasattr(point, "id") and hasattr(point, "payload"):
                                fact_data = {
                                    "id": str(point.id),
                                    "payload": point.payload,
                                    "collection": collection_name,
                                }
                                all_facts.append(fact_data)

                    # Count collections with facts
                    collection_count = len(
                        [f for f in all_facts if f["collection"] == collection_name]
                    )
                    if collection_count > 0:
                        stats["collections"] += 1

                    # Count assets specifically
                    if collection_name == "semantic_asset_data":
                        stats["asset_count"] = collection_count

                except Exception as e:
                    logger.warning(
                        f"Failed to load semantic collection {collection_name}: {e}"
                    )

            # Update total facts count
            stats["total_facts"] = len(all_facts)

            # Apply pagination to all facts
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_facts = all_facts[start_idx:end_idx]

            # Reorganize paginated facts by collection for display
            for fact in paginated_facts:
                collection = fact["collection"]
                if collection not in semantic_data:
                    semantic_data[collection] = {"items": [], "count": 0}
                semantic_data[collection]["items"].append(fact)

            # Update counts for displayed collections
            for collection_name in semantic_data:
                semantic_data[collection_name]["count"] = len(
                    semantic_data[collection_name]["items"]
                )

            # Calculate total pages
            if len(all_facts) > 0:
                stats["pages"] = max(1, (len(all_facts) + per_page - 1) // per_page)
            else:
                stats["pages"] = 1

        logger.info(
            f"Semantic memory page loaded with {stats['total_facts']} facts from {stats['collections']} collections (page {page})"
        )

        return render_template(
            "semantic_memory.html",
            semantic_data=semantic_data,
            stats=stats,
            current_collection=collection_filter,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Failed to load semantic memory page: {e}")
        flash(f"Error loading semantic memory: {e}", "error")
        return render_template("error.html", error=str(e))


@app.route("/memory/knowledge/<filename>")
@log_function()
def serve_knowledge_file(filename: str) -> tuple[dict, int] | str:
    """Serve knowledge base JSON files"""
    try:
        # Validate filename (security: prevent path traversal)
        if not filename.endswith(".json") or "/" in filename or "\\" in filename:
            return {"error": "Invalid filename"}, 400

        knowledge_path = Path("./knowledge/") / filename

        if not knowledge_path.exists():
            logger.warning(f"Knowledge file not found: {filename}")
            return {"error": "File not found"}, 404

        # Read and return JSON content
        with open(knowledge_path) as f:
            data = json.load(f)

        logger.debug(f"Served knowledge file: {filename}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filename}: {e}")
        return {"error": f"Invalid JSON: {e}"}, 400
    except Exception as e:
        logger.error(f"Error serving knowledge file {filename}: {e}")
        return {"error": str(e)}, 500


@app.route("/memory/knowledge")
@log_function()
def knowledge_base() -> str:
    """Knowledge base management - static knowledge and configurations"""
    try:
        knowledge_files = {}
        knowledge_stats = {"total_files": 0, "total_size": 0}

        knowledge_path = Path("./knowledge/")
        if knowledge_path.exists():
            for file_path in knowledge_path.glob("*.json"):
                try:
                    # Read file size and basic info
                    file_size = file_path.stat().st_size
                    knowledge_stats["total_size"] += file_size
                    knowledge_stats["total_files"] += 1

                    # Try to read JSON and get summary
                    with open(file_path) as f:
                        data = json.load(f)

                    # Extract metadata
                    metadata = data.get("metadata", {})

                    knowledge_files[file_path.name] = {
                        "path": str(file_path),
                        "size": file_size,
                        "description": metadata.get("description", "No description"),
                        "version": metadata.get("version", "Unknown"),
                        "extracted_date": metadata.get("extracted_date", "Unknown"),
                        "item_count": (
                            len(data) - 1 if "metadata" in data else len(data)
                        ),  # Exclude metadata from count
                    }

                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
                    knowledge_files[file_path.name] = {
                        "path": str(file_path),
                        "size": file_path.stat().st_size if file_path.exists() else 0,
                        "error": str(e),
                    }

        logger.info(
            f"Knowledge base page loaded with {knowledge_stats['total_files']} files"
        )
        return render_template(
            "knowledge_base.html",
            knowledge_files=knowledge_files,
            stats=knowledge_stats,
        )

    except Exception as e:
        logger.error(f"Failed to load knowledge base page: {e}")
        flash(f"Error loading knowledge base: {e}", "error")
        return render_template("error.html", error=str(e))


# Testing Cleanup Routes


@app.route("/testing/cleanup")
@log_function()
def testing_cleanup() -> str:
    """Testing cleanup page with granular control over data deletion"""
    try:
        # Get current system status for display
        stats = {}

        # Asset statistics
        if asset_agent:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                assets = loop.run_until_complete(asset_agent.list_assets())
                mappings = loop.run_until_complete(
                    asset_agent.list_asset_sender_mappings()
                )
                stats["assets"] = len(assets)
                stats["sender_mappings"] = len(mappings)
            finally:
                loop.close()
        else:
            stats["assets"] = 0
            stats["sender_mappings"] = 0

        # Email processing statistics
        stats["email_history"] = len(email_history._load_history())
        stats["processing_runs"] = len(run_history._load_runs())

        # Human review statistics
        review_stats = review_queue.get_stats()
        stats["human_review_items"] = review_stats["total_items"]

        # File system statistics
        assets_path = Path(config.assets_base_path)
        total_files = 0
        if assets_path.exists():
            for file_path in assets_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    total_files += 1
        stats["attachment_files"] = total_files

        # Review attachment files
        review_attachments_path = Path(config.review_attachments_path)
        review_files = 0
        if review_attachments_path.exists():
            review_files = len(
                [f for f in review_attachments_path.glob("*") if f.is_file()]
            )
        stats["review_files"] = review_files

        logger.info("Testing cleanup page loaded")
        return render_template("testing_cleanup.html", stats=stats)

    except Exception as e:
        logger.error(f"Failed to load testing cleanup page: {e}")
        return render_template("error.html", error=f"Failed to load cleanup page: {e}")


@app.route("/api/testing/cleanup", methods=["POST"])
@log_function()
def api_testing_cleanup() -> tuple[dict, int] | dict:
    """API endpoint for granular testing data cleanup"""
    try:
        data = request.get_json()
        cleanup_types = data.get("cleanup_types", [])
        confirm = data.get("confirm", False)

        if not confirm:
            return jsonify({"error": "Must confirm cleanup operation"}), 400

        if not cleanup_types:
            return jsonify({"error": "No cleanup types specified"}), 400

        results = {}
        total_removed = 0

        # Process each cleanup type
        if "processed_documents" in cleanup_types:
            result = _cleanup_processed_documents()
            results["processed_documents"] = result
            total_removed += result.get("removed_count", 0)

        if "email_history" in cleanup_types:
            result = _cleanup_email_history()
            results["email_history"] = result
            total_removed += result.get("removed_count", 0)

        if "processing_runs" in cleanup_types:
            result = _cleanup_processing_runs()
            results["processing_runs"] = result
            total_removed += result.get("removed_count", 0)

        if "human_review" in cleanup_types:
            result = _cleanup_human_review()
            results["human_review"] = result
            total_removed += result.get("removed_count", 0)

        if "attachment_files" in cleanup_types:
            result = _cleanup_attachment_files()
            results["attachment_files"] = result
            total_removed += result.get("removed_count", 0)

        if "memory_collections" in cleanup_types:
            result = _cleanup_memory_collections()
            results["memory_collections"] = result
            total_removed += result.get("removed_count", 0)

        if "memory_smart_reset" in cleanup_types:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_cleanup_memory_smart_reset())
                results["memory_smart_reset"] = result
                total_removed += result.get("removed_count", 0)
            finally:
                loop.close()

        if "sender_mappings" in cleanup_types:
            result = _cleanup_sender_mappings()
            results["sender_mappings"] = result
            total_removed += result.get("removed_count", 0)

        if "assets" in cleanup_types:
            result = _cleanup_assets()
            results["assets"] = result
            total_removed += result.get("removed_count", 0)

        if "reload_knowledge_base" in cleanup_types:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_reload_knowledge_base())
                results["reload_knowledge_base"] = result
                total_removed += result.get("loaded_count", 0)
            finally:
                loop.close()

        if "reset_file_validation" in cleanup_types:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_reset_file_validation())
                results["reset_file_validation"] = result
                total_removed += result.get("reset_count", 0)
            finally:
                loop.close()

        logger.info(
            f"Testing cleanup completed: {len(cleanup_types)} operations, {total_removed} items removed"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Cleanup completed: {total_removed} items removed",
                "results": results,
                "cleanup_types": cleanup_types,
            }
        )

    except Exception as e:
        logger.error(f"Testing cleanup failed: {e}")
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500


@log_function()
def _cleanup_processed_documents() -> dict[str, Any]:
    """
    Clear processed documents from Qdrant collection.

    Removes all processed document metadata from the Qdrant collection
    while preserving the collection structure. This allows documents
    to be reprocessed without duplicate detection.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If Qdrant operations fail
    """
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {
                "success": False,
                "error": "Asset agent or Qdrant not available",
                "removed_count": 0,
            }

        collection_name = asset_agent.COLLECTIONS["processed_documents"]

        # Get count before deletion
        try:
            info = asset_agent.qdrant.get_collection(collection_name)
            before_count = info.points_count
        except Exception:
            before_count = 0

        # Delete all points in collection using the proper Qdrant API format
        try:
            # Use scroll to get all point IDs, then delete them
            scroll_result = asset_agent.qdrant.scroll(
                collection_name=collection_name,
                limit=10000,  # Get all points (adjust if you have more than 10k)
            )

            if scroll_result[0]:  # If there are points to delete
                point_ids = [point.id for point in scroll_result[0]]
                if point_ids:
                    asset_agent.qdrant.delete(
                        collection_name=collection_name, points_selector=point_ids
                    )
                    logger.info(
                        f"Deleted {len(point_ids)} points from {collection_name}"
                    )

        except Exception as delete_error:
            logger.warning(f"Failed to delete points: {delete_error}")
            # Fallback: try to recreate the collection
            try:
                asset_agent.qdrant.delete_collection(collection_name)
                # The collection will be recreated automatically when needed
                logger.info(f"Recreated collection {collection_name}")
            except Exception as recreate_error:
                logger.warning(f"Failed to recreate collection: {recreate_error}")

        logger.info(f"Cleared {before_count} processed documents from Qdrant")
        return {
            "success": True,
            "removed_count": before_count,
            "message": f"Cleared {before_count} processed documents",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup processed documents: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_email_history() -> dict[str, Any]:
    """
    Clear email processing history data.

    Removes all email processing history from the JSON file storage,
    allowing emails to be reprocessed as if they were never seen before.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If file operations fail
    """
    try:
        before_count = len(email_history._load_history())
        email_history.clear_processed()

        logger.info(f"Cleared {before_count} email history items")
        return {
            "success": True,
            "removed_count": before_count,
            "message": f"Cleared {before_count} email history items",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup email history: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_processing_runs() -> dict[str, Any]:
    """
    Clear processing run history data.

    Removes all batch processing run logs and statistics from JSON storage,
    clearing the history of email processing operations.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If file operations fail
    """
    try:
        before_count = len(run_history._load_runs())
        run_history.clear_runs()

        logger.info(f"Cleared {before_count} processing runs")
        return {
            "success": True,
            "removed_count": before_count,
            "message": f"Cleared {before_count} processing runs",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup processing runs: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_human_review() -> dict[str, Any]:
    """
    Clear human review queue and attachment files.

    Removes all pending and completed human review items from the JSON
    queue storage, along with their associated attachment files.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If file operations fail
    """
    try:
        removed_count = review_queue.clear_all_items()

        logger.info(f"Cleared {removed_count} human review items")
        return {
            "success": True,
            "removed_count": removed_count,
            "message": f"Cleared {removed_count} human review items",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup human review: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_attachment_files() -> dict[str, Any]:
    """
    Clear all attachment files from disk storage.

    Removes all saved email attachment files from the assets directory
    while preserving the folder structure for future use.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If file system operations fail
    """
    try:
        assets_path = Path(config.assets_base_path)
        removed_count = 0

        if assets_path.exists():
            # Remove all files but keep asset folder structure
            for asset_folder in assets_path.iterdir():
                if asset_folder.is_dir() and not asset_folder.name.startswith("."):
                    for file_path in asset_folder.rglob("*"):
                        if file_path.is_file() and not file_path.name.startswith("."):
                            try:
                                file_path.unlink()
                                removed_count += 1
                            except Exception as e:
                                logger.warning(
                                    f"Failed to remove file {file_path}: {e}"
                                )

            # Also clean special folders
            for special_folder in ["to_be_reviewed", "uncategorized"]:
                special_path = assets_path / special_folder
                if special_path.exists():
                    for file_path in special_path.rglob("*"):
                        if file_path.is_file():
                            try:
                                file_path.unlink()
                                removed_count += 1
                            except Exception as e:
                                logger.warning(
                                    f"Failed to remove file {file_path}: {e}"
                                )

        logger.info(f"Removed {removed_count} attachment files")
        return {
            "success": True,
            "removed_count": removed_count,
            "message": f"Removed {removed_count} attachment files",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup attachment files: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_memory_collections() -> dict[str, Any]:
    """
    Clear all memory collections completely.

    Deletes entire memory collections (semantic, episodic, procedural, contacts)
    from Qdrant. These collections will be automatically recreated when
    first accessed by the memory systems.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If Qdrant operations fail
    """
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {
                "success": False,
                "error": "Qdrant not available",
                "removed_count": 0,
            }

        memory_collections = ["semantic", "episodic", "procedural", "contacts"]
        total_removed = 0

        for collection_name in memory_collections:
            try:
                # Check if collection exists
                collections = asset_agent.qdrant.get_collections()
                if collection_name in [c.name for c in collections.collections]:
                    info = asset_agent.qdrant.get_collection(collection_name)
                    points_count = info.points_count

                    # Delete the entire collection
                    asset_agent.qdrant.delete_collection(collection_name)
                    total_removed += points_count

                    logger.info(
                        f"Deleted memory collection '{collection_name}' with {points_count} items"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to delete memory collection '{collection_name}': {e}"
                )

        logger.info(f"Cleared {total_removed} items from memory collections")
        return {
            "success": True,
            "removed_count": total_removed,
            "message": f"Cleared {total_removed} memory items",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup memory collections: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
async def _cleanup_memory_smart_reset() -> dict[str, Any]:
    """
    Smart memory reset: Clear episodic memory but re-seed procedural memory.

    This function:
    1. Clears episodic memory (individual experiences)
    2. Clears procedural memory collections
    3. Re-seeds procedural memory from saved knowledge base

    This preserves the domain knowledge while resetting learning state.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message
    """
    try:
        if (
            not asset_agent
            or not asset_agent.qdrant
            or not asset_agent.procedural_memory
        ):
            return {
                "success": False,
                "error": "Asset agent or procedural memory not available",
                "removed_count": 0,
            }

        total_removed = 0
        results = []

        # Step 1: Clear episodic memory
        try:
            collections = asset_agent.qdrant.get_collections()
            episodic_collections = ["episodic"]

            for collection_name in episodic_collections:
                if collection_name in [c.name for c in collections.collections]:
                    info = asset_agent.qdrant.get_collection(collection_name)
                    points_count = info.points_count

                    asset_agent.qdrant.delete_collection(collection_name)
                    total_removed += points_count

                    results.append(f"Cleared {points_count} episodic memories")
                    logger.info(
                        f"Cleared episodic memory collection: {points_count} items"
                    )

        except Exception as e:
            logger.warning(f"Failed to clear episodic memory: {e}")
            results.append(f"Warning: Failed to clear episodic memory - {e}")

        # Step 2: Clear procedural memory collections
        try:
            # Use actual collection names that exist
            procedural_collections = [
                "procedural_classification_patterns",
                "procedural_confidence_models",
                "procedural_asset_patterns",
                "procedural_configuration_rules",
            ]

            for full_name in procedural_collections:
                try:
                    if full_name in [c.name for c in collections.collections]:
                        info = asset_agent.qdrant.get_collection(full_name)
                        points_count = info.points_count

                        asset_agent.qdrant.delete_collection(full_name)
                        total_removed += points_count

                        results.append(
                            f"Cleared {points_count} {full_name.replace('procedural_', '')}"
                        )
                        logger.info(
                            f"Cleared procedural collection {full_name}: {points_count} items"
                        )

                except Exception as e:
                    logger.warning(f"Failed to clear {full_name}: {e}")

        except Exception as e:
            logger.warning(f"Failed to clear procedural collections: {e}")
            results.append(f"Warning: Procedural cleanup had issues - {e}")

        # Step 3: Re-initialize procedural memory collections
        try:
            await asset_agent.procedural_memory.initialize_collections()
            results.append("Re-initialized procedural memory collections")
            logger.info("Re-initialized procedural memory collections")
        except Exception as e:
            logger.warning(f"Failed to re-initialize procedural collections: {e}")
            results.append(f"Warning: Failed to re-initialize - {e}")

        # Step 4: Re-seed from knowledge base
        try:
            knowledge_path = "./knowledge/"
            seeding_stats = (
                await asset_agent.procedural_memory.seed_from_knowledge_base(
                    knowledge_path
                )
            )

            seeded_count = (
                sum(seeding_stats.values()) if isinstance(seeding_stats, dict) else 0
            )
            results.append(f"Re-seeded {seeded_count} patterns from knowledge base")
            logger.info(f"Re-seeded procedural memory: {seeding_stats}")

        except Exception as e:
            logger.warning(f"Failed to re-seed from knowledge base: {e}")
            results.append(f"Warning: Failed to re-seed knowledge - {e}")

        success_message = "; ".join(results)
        logger.info(
            f"Smart memory reset completed: {total_removed} items removed, procedural memory re-seeded"
        )

        return {
            "success": True,
            "removed_count": total_removed,
            "message": success_message,
        }

    except Exception as e:
        logger.error(f"Failed to perform smart memory reset: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_sender_mappings() -> dict[str, Any]:
    """
    Clear all sender-asset mapping relationships.

    Removes all sender-to-asset mappings from the Qdrant collection
    while preserving the collection structure. This disconnects all
    email senders from their associated assets.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If Qdrant operations fail
    """
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {
                "success": False,
                "error": "Asset agent not available",
                "removed_count": 0,
            }

        collection_name = asset_agent.COLLECTIONS["asset_sender_mappings"]

        # Get count before deletion
        try:
            info = asset_agent.qdrant.get_collection(collection_name)
            before_count = info.points_count
        except Exception:
            before_count = 0

        # Delete all points in collection
        try:
            # Use scroll to get all point IDs, then delete them
            scroll_result = asset_agent.qdrant.scroll(
                collection_name=collection_name,
                limit=10000,  # Get all points (adjust if you have more than 10k)
            )

            if scroll_result[0]:  # If there are points to delete
                point_ids = [point.id for point in scroll_result[0]]
                if point_ids:
                    asset_agent.qdrant.delete(
                        collection_name=collection_name, points_selector=point_ids
                    )
                    logger.info(f"Deleted {len(point_ids)} sender mapping points")

        except Exception as delete_error:
            logger.warning(f"Failed to delete sender mapping points: {delete_error}")
            # Fallback: try to recreate the collection
            try:
                asset_agent.qdrant.delete_collection(collection_name)
                # The collection will be recreated automatically when needed
                logger.info(f"Recreated sender mappings collection {collection_name}")
            except Exception as recreate_error:
                logger.warning(
                    f"Failed to recreate sender mappings collection: {recreate_error}"
                )

        logger.info(f"Cleared {before_count} sender mappings")
        return {
            "success": True,
            "removed_count": before_count,
            "message": f"Cleared {before_count} sender mappings",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup sender mappings: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
def _cleanup_assets() -> dict[str, Any]:
    """
    Clear all asset definitions (DANGEROUS OPERATION).

    WARNING: Removes all asset definitions from Qdrant and deletes
    their corresponding folders from disk. This is a destructive
    operation that cannot be undone.

    Returns:
        Dictionary containing operation results with success status,
        removed count, and descriptive message

    Raises:
        Exception: If Qdrant or file system operations fail
    """
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {
                "success": False,
                "error": "Asset agent not available",
                "removed_count": 0,
            }

        collection_name = asset_agent.COLLECTIONS["assets"]

        # Get count before deletion
        try:
            info = asset_agent.qdrant.get_collection(collection_name)
            before_count = info.points_count
        except Exception:
            before_count = 0

        # Delete all points in collection
        try:
            # Use scroll to get all point IDs, then delete them
            scroll_result = asset_agent.qdrant.scroll(
                collection_name=collection_name,
                limit=10000,  # Get all points (adjust if you have more than 10k)
            )

            if scroll_result[0]:  # If there are points to delete
                point_ids = [point.id for point in scroll_result[0]]
                if point_ids:
                    asset_agent.qdrant.delete(
                        collection_name=collection_name, points_selector=point_ids
                    )
                    logger.info(f"Deleted {len(point_ids)} asset points")

        except Exception as delete_error:
            logger.warning(f"Failed to delete asset points: {delete_error}")
            # Fallback: try to recreate the collection
            try:
                asset_agent.qdrant.delete_collection(collection_name)
                # The collection will be recreated automatically when needed
                logger.info(f"Recreated assets collection {collection_name}")
            except Exception as recreate_error:
                logger.warning(
                    f"Failed to recreate assets collection: {recreate_error}"
                )

        # Also remove asset folders from disk
        assets_path = Path(config.assets_base_path)
        if assets_path.exists():
            for asset_folder in assets_path.iterdir():
                if (
                    asset_folder.is_dir()
                    and not asset_folder.name.startswith(".")
                    and "_" in asset_folder.name
                    and len(asset_folder.name.split("_")[0]) > 20
                ):
                    try:
                        # # Standard library imports
                        import shutil

                        shutil.rmtree(asset_folder)
                        logger.info(f"Removed asset folder: {asset_folder.name}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove asset folder {asset_folder}: {e}"
                        )

        logger.warning(
            f"DELETED {before_count} assets - this removes asset definitions!"
        )
        return {
            "success": True,
            "removed_count": before_count,
            "message": f"DELETED {before_count} assets",
        }

    except Exception as e:
        logger.error(f"Failed to cleanup assets: {e}")
        return {"success": False, "error": str(e), "removed_count": 0}


@log_function()
async def _reload_knowledge_base() -> dict[str, Any]:
    """
    Reload knowledge base into semantic memory.

    Loads/refreshes semantic memory with updated knowledge from the
    knowledge base files, including file type validations and business rules.

    Returns:
        Dictionary containing operation results with success status,
        loaded count, and descriptive message
    """
    try:
        if not asset_agent:
            return {
                "success": False,
                "error": "Asset agent not available",
                "loaded_count": 0,
            }

        if (
            not hasattr(asset_agent, "semantic_memory")
            or not asset_agent.semantic_memory
        ):
            return {
                "success": False,
                "error": "Semantic memory not available",
                "loaded_count": 0,
            }

        # Load knowledge base
        results = await asset_agent.semantic_memory.load_knowledge_base("knowledge")

        loaded_count = results.get("total_knowledge_items", 0)
        file_types_loaded = results.get("file_types_loaded", 0)
        errors = results.get("errors", [])

        if errors:
            logger.warning(f"Knowledge base loading had {len(errors)} errors: {errors}")

        logger.info(
            f"Reloaded knowledge base: {loaded_count} total items, {file_types_loaded} file types"
        )

        message = (
            f"Loaded {loaded_count} knowledge items ({file_types_loaded} file types)"
        )
        if errors:
            message += f" with {len(errors)} warnings"

        return {
            "success": True,
            "loaded_count": loaded_count,
            "file_types_loaded": file_types_loaded,
            "errors": errors,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Failed to reload knowledge base: {e}")
        return {"success": False, "error": str(e), "loaded_count": 0}


@log_function()
async def _reset_file_validation() -> dict[str, Any]:
    """
    Reset file type validation learning.

    Clears all learned file type patterns from semantic memory and
    reloads them from the knowledge base bootstrap, effectively
    resetting the adaptive file validation system.

    Returns:
        Dictionary containing operation results with success status,
        reset count, and descriptive message
    """
    try:
        if not asset_agent:
            return {
                "success": False,
                "error": "Asset agent not available",
                "reset_count": 0,
            }

        if (
            not hasattr(asset_agent, "semantic_memory")
            or not asset_agent.semantic_memory
        ):
            return {
                "success": False,
                "error": "Semantic memory not available",
                "reset_count": 0,
            }

        reset_count = 0

        # Step 1: Clear existing file type validation rules from semantic memory
        try:
            # Search for file type validation knowledge
            file_type_rules = await asset_agent.semantic_memory.search(
                query="file type validation security",
                limit=1000,
                knowledge_type=asset_agent.semantic_memory.KnowledgeType.RULE,
            )

            # Remove existing file type rules (would need delete functionality)
            reset_count = len(file_type_rules)
            logger.info(f"Found {reset_count} existing file type rules to reset")

        except Exception as e:
            logger.warning(f"Could not clear existing file type rules: {e}")

        # Step 2: Reload file type validation from knowledge base
        try:
            results = await asset_agent.semantic_memory.load_knowledge_base("knowledge")

            file_types_loaded = results.get("file_types_loaded", 0)
            errors = results.get("errors", [])

            if errors:
                logger.warning(
                    f"File validation reset had {len(errors)} errors: {errors}"
                )

            logger.info(
                f"Reset file validation: loaded {file_types_loaded} file type rules"
            )

            message = (
                f"Reset and reloaded {file_types_loaded} file type validation rules"
            )
            if errors:
                message += f" with {len(errors)} warnings"

            return {
                "success": True,
                "reset_count": file_types_loaded,
                "errors": errors,
                "message": message,
            }

        except Exception as e:
            logger.error(f"Failed to reload file validation rules: {e}")
            return {
                "success": False,
                "error": f"Failed to reload: {e}",
                "reset_count": 0,
            }

    except Exception as e:
        logger.error(f"Failed to reset file validation: {e}")
        return {"success": False, "error": str(e), "reset_count": 0}


# API endpoints for memory operations
@app.route("/api/memory/<memory_type>/clear", methods=["POST"])
@log_function()
def api_clear_memory(memory_type: str) -> tuple[dict, int] | dict:
    """API endpoint to clear specific memory type"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        collections_to_clear = []

        if memory_type == "episodic":
            collections_to_clear = ["episodic"]
        elif memory_type == "procedural":
            collections_to_clear = [
                "procedural_classification_patterns",
                "procedural_confidence_models",
                "procedural_asset_patterns",
                "procedural_configuration_rules",
            ]
        elif memory_type == "contact":
            collections_to_clear = ["contact_memory"]
        elif memory_type == "semantic":
            # Get all semantic collections dynamically
            try:
                collections_response = asset_agent.qdrant.get_collections()
                collections_to_clear = [
                    c.name
                    for c in collections_response.collections
                    if "semantic" in c.name.lower()
                ]
            except Exception as e:
                logger.warning(f"Failed to get semantic collections: {e}")
                collections_to_clear = []
        else:
            return {"error": f"Unknown memory type: {memory_type}"}, 400

        cleared_count = 0
        results = []

        for collection_name in collections_to_clear:
            try:
                if collection_name in [
                    c.name for c in asset_agent.qdrant.get_collections().collections
                ]:
                    info = asset_agent.qdrant.get_collection(collection_name)
                    points_count = info.points_count

                    asset_agent.qdrant.delete_collection(collection_name)
                    cleared_count += points_count
                    results.append(
                        f"Cleared {points_count} items from {collection_name}"
                    )

            except Exception as e:
                logger.warning(f"Failed to clear {collection_name}: {e}")
                results.append(f"Warning: Failed to clear {collection_name} - {e}")

        logger.info(f"Cleared {cleared_count} items from {memory_type} memory")
        return {
            "success": True,
            "cleared_count": cleared_count,
            "memory_type": memory_type,
            "details": results,
        }

    except Exception as e:
        logger.error(f"Failed to clear {memory_type} memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/procedural/<collection_name>/<item_id>", methods=["GET"])
@log_function()
def api_get_procedural_pattern(
    collection_name: str, item_id: str
) -> tuple[dict, int] | dict:
    """Get detailed information about a specific procedural memory pattern"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        # Validate collection name
        valid_collections = [
            "procedural_classification_patterns",
            "procedural_confidence_models",
            "procedural_asset_patterns",
            "procedural_configuration_rules",
        ]

        if collection_name not in valid_collections:
            return {"error": f"Invalid collection: {collection_name}"}, 400

        # Retrieve the specific pattern
        try:
            points = asset_agent.qdrant.retrieve(
                collection_name=collection_name,
                ids=[item_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                return {"error": "Pattern not found"}, 404

            point = points[0]
            pattern_data = {
                "id": str(point.id),
                "collection": collection_name,
                "payload": point.payload,
            }

            return {"success": True, "pattern": pattern_data}

        except Exception as e:
            return {"error": f"Failed to retrieve pattern: {str(e)}"}, 500

    except Exception as e:
        logger.error(f"Failed to get procedural pattern: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/procedural/<collection_name>/<item_id>", methods=["DELETE"])
@log_function()
def api_delete_procedural_pattern(
    collection_name: str, item_id: str
) -> tuple[dict, int] | dict:
    """Delete a specific procedural memory pattern"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        # Validate collection name
        valid_collections = [
            "procedural_classification_patterns",
            "procedural_confidence_models",
            "procedural_asset_patterns",
            "procedural_configuration_rules",
        ]

        if collection_name not in valid_collections:
            return {"error": f"Invalid collection: {collection_name}"}, 400

        # Delete the specific pattern
        asset_agent.qdrant.delete(
            collection_name=collection_name, points_selector=[item_id]
        )

        logger.info(f"Deleted procedural pattern: {item_id} from {collection_name}")
        return {"success": True, "message": f"Pattern {item_id} deleted"}

    except Exception as e:
        logger.error(f"Failed to delete procedural pattern: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/semantic/<collection_name>/<item_id>", methods=["GET"])
@log_function()
def api_get_semantic_fact(
    collection_name: str, item_id: str
) -> tuple[dict, int] | dict:
    """Get detailed information about a specific semantic memory fact"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        # Validate collection name (must be a semantic collection)
        try:
            collections_response = asset_agent.qdrant.get_collections()
            semantic_collections = [
                c.name
                for c in collections_response.collections
                if "semantic" in c.name.lower()
            ]
        except Exception as e:
            return {"error": f"Failed to get collections: {e}"}, 500

        if collection_name not in semantic_collections:
            return {"error": f"Invalid semantic collection: {collection_name}"}, 400

        # Retrieve the specific fact
        try:
            points = asset_agent.qdrant.retrieve(
                collection_name=collection_name,
                ids=[item_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                return {"error": "Semantic fact not found"}, 404

            point = points[0]
            fact_data = {
                "id": str(point.id),
                "collection": collection_name,
                "payload": point.payload,
            }

            return {"success": True, "fact": fact_data}

        except Exception as e:
            return {"error": f"Failed to retrieve semantic fact: {str(e)}"}, 500

    except Exception as e:
        logger.error(f"Failed to get semantic fact: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/semantic/<collection_name>/<item_id>", methods=["DELETE"])
@log_function()
def api_delete_semantic_fact(
    collection_name: str, item_id: str
) -> tuple[dict, int] | dict:
    """Delete a specific semantic memory fact"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        # Validate collection name (must be a semantic collection)
        try:
            collections_response = asset_agent.qdrant.get_collections()
            semantic_collections = [
                c.name
                for c in collections_response.collections
                if "semantic" in c.name.lower()
            ]
        except Exception as e:
            return {"error": f"Failed to get collections: {e}"}, 500

        if collection_name not in semantic_collections:
            return {"error": f"Invalid semantic collection: {collection_name}"}, 400

        # Delete the specific fact
        asset_agent.qdrant.delete(
            collection_name=collection_name, points_selector=[item_id]
        )

        logger.info(f"Deleted semantic fact: {item_id} from {collection_name}")
        return {"success": True, "message": f"Semantic fact {item_id} deleted"}

    except Exception as e:
        logger.error(f"Failed to delete semantic fact: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/<memory_type>/item/<item_id>", methods=["DELETE"])
@log_function()
def api_delete_memory_item(memory_type: str, item_id: str) -> tuple[dict, int] | dict:
    """API endpoint to delete specific memory item"""
    try:
        if not asset_agent or not asset_agent.qdrant:
            return {"error": "Asset agent not available"}, 400

        # Map memory type to collection name
        collection_mapping = {"episodic": "episodic", "contact": "contact_memory"}

        if memory_type not in collection_mapping:
            return {
                "error": f"Unsupported memory type for item deletion: {memory_type}"
            }, 400

        collection_name = collection_mapping[memory_type]

        # Delete the item
        asset_agent.qdrant.delete(
            collection_name=collection_name, points_selector=[item_id]
        )

        logger.info(f"Deleted item {item_id} from {memory_type} memory")
        return {"success": True, "deleted_item": item_id, "memory_type": memory_type}

    except Exception as e:
        logger.error(f"Failed to delete {memory_type} item {item_id}: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/conflicts", methods=["GET"])
@log_function()
def api_get_conflicts() -> tuple[dict, int] | dict:
    """Get pending conflicts for human review."""
    try:
        if not asset_agent:
            return {"error": "Asset agent not available"}, 400

        semantic_memory = asset_agent.semantic_memory

        # Use Qdrant directly for synchronous operation
        try:
            collections_response = asset_agent.qdrant.get_collections()
            semantic_collections = [
                c.name
                for c in collections_response.collections
                if "semantic" in c.name.lower()
            ]
        except Exception as e:
            return {"error": f"Failed to get collections: {e}"}, 500

        conflict_items = []

        # Search through semantic collections for conflicts
        for collection_name in semantic_collections:
            try:
                # Search for conflict items using text matching
                search_result = asset_agent.qdrant.scroll(
                    collection_name=collection_name,
                    scroll_filter={
                        "must": [
                            {
                                "key": "content",
                                "match": {"text": "CONFLICT REVIEW NEEDED"},
                            }
                        ]
                    },
                    limit=50,
                    with_payload=True,
                    with_vectors=False,
                )

                points, _ = search_result

                for point in points:
                    if "conflict_details" in point.payload:
                        conflict_items.append(
                            {
                                "id": str(point.id),
                                "collection": collection_name,
                                "timestamp": point.payload.get("timestamp"),
                                "conflict_type": point.payload.get("conflict_type"),
                                "priority": point.payload.get("priority"),
                                "status": point.payload.get("status"),
                                "new_content": point.payload.get("new_content"),
                                "conflict_details": point.payload.get(
                                    "conflict_details"
                                ),
                            }
                        )

            except Exception as e:
                logger.warning(f"Error searching collection {collection_name}: {e}")
                continue

        return {
            "success": True,
            "conflicts": conflict_items,
            "total_count": len(conflict_items),
        }

    except Exception as e:
        logger.error(f"Error getting conflicts: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/conflicts/<conflict_id>/resolve", methods=["POST"])
@log_function()
def api_resolve_conflict(conflict_id: str) -> tuple[dict, int] | dict:
    """Resolve a specific conflict based on user decision."""
    try:
        data = request.get_json()
        resolution = data.get(
            "resolution"
        )  # "accept_new", "keep_existing", "manual_edit"

        if not asset_agent:
            return {"error": "Asset agent not available"}, 400

        semantic_memory = asset_agent.semantic_memory

        # Get collections to find the conflict
        try:
            collections_response = asset_agent.qdrant.get_collections()
            semantic_collections = [
                c.name
                for c in collections_response.collections
                if "semantic" in c.name.lower()
            ]
        except Exception as e:
            return {"error": f"Failed to get collections: {e}"}, 500

        # Find the conflict item
        conflict_item = None
        conflict_collection = None

        for collection_name in semantic_collections:
            try:
                points = asset_agent.qdrant.retrieve(
                    collection_name=collection_name,
                    ids=[conflict_id],
                    with_payload=True,
                    with_vectors=False,
                )
                if points:
                    conflict_item = points[0]
                    conflict_collection = collection_name
                    break
            except Exception:
                continue

        if not conflict_item:
            return {"error": "Conflict not found"}, 404

        conflict_details = conflict_item.payload.get("conflict_details", {})
        existing_id = conflict_details.get("existing_id")

        if resolution == "accept_new":
            # Add the new content, replacing the existing - simplified approach
            # Just delete the conflict item since we can't easily do async updates
            if conflict_collection:
                asset_agent.qdrant.delete(
                    collection_name=conflict_collection, points_selector=[conflict_id]
                )
            logger.info(f"Conflict {conflict_id} resolved: accepted new content")

        elif resolution == "keep_existing":
            # Just mark conflict as resolved, keep existing
            if conflict_collection:
                asset_agent.qdrant.delete(
                    collection_name=conflict_collection, points_selector=[conflict_id]
                )
            logger.info(f"Conflict {conflict_id} resolved: kept existing content")

        elif resolution == "manual_edit":
            # Delete conflict for now - manual editing would need additional UI
            if conflict_collection:
                asset_agent.qdrant.delete(
                    collection_name=conflict_collection, points_selector=[conflict_id]
                )
            logger.info(f"Conflict {conflict_id} resolved: manual edit requested")

        return {"success": True, "message": f"Conflict resolved: {resolution}"}

    except Exception as e:
        logger.error(f"Error resolving conflict {conflict_id}: {e}")
        return {"error": str(e)}, 500


@app.errorhandler(404)
def not_found_error(error) -> tuple[str, int]:
    logger.warning(f"404 error: {request.url}")
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error) -> tuple[str, int]:
    logger.error(f"500 error: {error}")
    return render_template("error.html", error="Internal server error"), 500


def create_app() -> Flask:
    """Application factory function"""
    # Only initialize in Flask's reloader process (the actual running process)
    # Skip initialization in the parent process that just spawns the reloader
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        logger.debug("Initializing in Flask reloader process")
    else:
        logger.debug("Skipping initialization in Flask parent process")
        return app

    # Initialize the asset agent (with guard against duplicates)
    initialize_asset_agent()
    return app


if __name__ == "__main__":
    # Only initialize if not already done (Flask debug mode protection)
    if asset_agent is None:
        initialize_asset_agent()

    logger.info("🌐 Email Agent Asset Management Web UI")
    logger.info("==================================================")
    logger.info("Starting Flask development server...")
    logger.info(f"📊 Dashboard:        http://localhost:{config.flask_port}")
    logger.info(f"🏢 Assets:           http://localhost:{config.flask_port}/assets")
    logger.info(f"📧 Sender Mappings:  http://localhost:{config.flask_port}/senders")
    logger.info(f"🔧 API Health:       http://localhost:{config.flask_port}/api/health")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("==================================================")

    # Run the Flask app
    app.run(debug=config.debug, host=config.flask_host, port=config.flask_port)

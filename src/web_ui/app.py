#!/usr/bin/env python3
"""
Flask Web Application for Email Agent Asset Management

A user-friendly web interface for setting up and managing assets,
sender mappings, and document classification rules.
"""

# # Standard library imports
# Standard library imports
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# # Third-party imports
# Third-party imports
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

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
# Local imports
from agents.asset_document_agent import (
    AssetDocumentAgent,
    AssetType,
    DocumentCategory,
    ProcessingStatus,
)
from email_interface import (
    BaseEmailInterface,
    EmailSearchCriteria,
    create_email_interface,
)
from utils.config import config
from utils.logging_system import LogConfig, configure_logging, get_logger, log_function

from .human_review import review_queue

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

# Global asset agent instance
asset_agent: AssetDocumentAgent | None = None

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
    """Process emails from a specific mailbox"""
    mailbox_id = mailbox_config["id"]
    mailbox_type = mailbox_config["type"]

    logger.info(
        f"Processing emails from mailbox: {mailbox_id} ({hours_back} hours back)"
    )

    results = {
        "mailbox_id": mailbox_id,
        "total_emails": 0,
        "processed_emails": 0,
        "skipped_emails": 0,
        "errors": 0,
        "processing_details": [],
    }

    try:
        # Create email interface based on type
        if mailbox_type == "microsoft_graph":
            # Microsoft Graph uses credentials_path in constructor
            # # Local application imports
            from email_interface.msgraph import MicrosoftGraphInterface

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

        # Define search criteria for last 24 hours
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

        for email in emails:
            try:
                # Check if already processed
                if not force_reprocess and email_history.is_processed(
                    email.id, mailbox_id
                ):
                    results["skipped_emails"] += 1
                    logger.debug(f"Skipping already processed email: {email.id}")
                    continue

                # Process email and attachments
                processing_info = await process_single_email(
                    email, email_interface, mailbox_id
                )

                # Mark as processed
                email_history.mark_processed(email.id, mailbox_id, processing_info)

                results["processed_emails"] += 1
                results["processing_details"].append(
                    {
                        "email_id": email.id,
                        "subject": email.subject,
                        "sender": email.sender.address if email.sender else "Unknown",
                        "attachments_count": (
                            len(email.attachments) if email.attachments else 0
                        ),
                        "processing_info": processing_info,
                    }
                )

                logger.info(f"Successfully processed email: {email.subject[:50]}...")

            except Exception as e:
                results["errors"] += 1
                logger.error(f"Failed to process email {email.id}: {e}")
                results["processing_details"].append(
                    {"email_id": email.id, "subject": email.subject, "error": str(e)}
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
        f"Mailbox processing complete: {results['processed_emails']} processed, {results['skipped_emails']} skipped, {results['errors']} errors"
    )
    return results


@log_function()
async def process_single_email(
    email, email_interface: BaseEmailInterface, mailbox_id: str = "unknown"
) -> dict[str, Any]:
    """
    Process a single email and its attachments through the asset document agent.

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
    }

    logger.info(
        f"Processing email '{email.subject}' with {len(email.attachments) if email.attachments else 0} attachments"
    )

    if not email.attachments:
        logger.warning(f"Email '{email.subject}' has no attachments to process")
        return processing_info

    for attachment in email.attachments:
        # Initialize attachment_data early to avoid scoping issues
        attachment_data = {
            "filename": attachment.filename,
            "content": None,
        }

        try:
            logger.info(
                f"Processing attachment: {attachment.filename} (size: {attachment.size}, content loaded: {attachment.content is not None})"
            )

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
                    continue

            # Update attachment data with content
            attachment_data["content"] = attachment_content

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

            # Process with asset document agent (enhanced with asset matching)
            result = await asset_agent.enhanced_process_attachment(
                attachment_data=attachment_data, email_data=email_data
            )

            # Save file to disk if processing was successful OR if it's a duplicate with matched asset
            should_save = result.status == ProcessingStatus.SUCCESS or (
                result.status == ProcessingStatus.DUPLICATE and result.matched_asset_id
            )

            if should_save:
                content = attachment_data.get("content", b"")
                filename = attachment_data.get("filename", "unknown_attachment")

                if content:
                    file_path = await asset_agent.save_attachment_to_asset_folder(
                        content, filename, result, result.matched_asset_id
                    )

                    if file_path:
                        logger.info(f"File saved successfully to: {file_path}")

                        # Store document metadata in Qdrant (only for non-duplicates to avoid duplicate entries)
                        if (
                            result.status == ProcessingStatus.SUCCESS
                            and asset_agent.qdrant
                            and result.file_hash
                        ):
                            document_id = await asset_agent.store_processed_document(
                                result.file_hash, result, result.matched_asset_id
                            )
                            if document_id:
                                logger.info(
                                    f"Document metadata stored with ID: {document_id[:8]}..."
                                )
                    else:
                        logger.warning("Failed to save file to disk")

            processing_info["attachments_processed"] += 1

            # Log processing result
            logger.info(
                f"Attachment processing result: status={result.status.value}, validation_confidence={result.confidence}"
            )

            # Log detailed confidence breakdown if available
            if result.classification_metadata:
                meta = result.classification_metadata
                logger.info(
                    f"Confidence breakdown - Document: {meta.get('document_confidence', 0):.2f}, Asset: {meta.get('asset_confidence', 0):.2f}, Sender: {'Known' if meta.get('sender_known', False) else 'Unknown'}"
                )
                logger.info(
                    f"Overall routing decision: {result.confidence_level.value if result.confidence_level else 'unknown'}"
                )

            # Handle different processing statuses
            if result.status.value == "quarantined":
                logger.warning(f"Attachment quarantined: {result.quarantine_reason}")
                processing_info["quarantined"] = (
                    processing_info.get("quarantined", 0) + 1
                )
            elif result.status.value == "duplicate":
                logger.info(f"Attachment is duplicate of: {result.duplicate_of}")
                processing_info["duplicates"] = processing_info.get("duplicates", 0) + 1
            elif result.status.value == "error":
                logger.error(f"Attachment processing error: {result.error_message}")
                processing_info["errors"] = processing_info.get("errors", 0) + 1

            if result.matched_asset_id:
                processing_info["attachments_classified"] += 1
                processing_info["assets_matched"].append(
                    {
                        "asset_id": result.matched_asset_id,
                        "confidence": result.asset_confidence,
                        "attachment_name": attachment.filename,
                        "file_path": (
                            str(result.file_path) if result.file_path else None
                        ),
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
                )
                logger.info(
                    f"Attachment matched to asset: {result.matched_asset_id} (confidence: {result.asset_confidence})"
                )
            else:
                logger.info("Attachment processed but no asset match found")

            # Check if attachment needs human review (low confidence or no match)
            needs_review = False
            review_reason = None

            if not result.matched_asset_id:
                # No asset match at all - needs review
                needs_review = True
                review_reason = "no_asset_match"
                logger.info("Adding to human review: no asset match found")
            elif result.asset_confidence < config.low_confidence_threshold:
                # Low confidence match - needs review
                needs_review = True
                review_reason = "low_asset_confidence"
                logger.info(
                    f"Adding to human review: low asset confidence ({result.asset_confidence:.2f})"
                )
            elif (
                hasattr(result, "confidence_level")
                and result.confidence_level
                and result.confidence_level.value in ["very_low", "low"]
            ):
                # System flagged as needing review based on overall confidence
                needs_review = True
                review_reason = f"overall_confidence_{result.confidence_level.value}"

                # Provide detailed explanation
                if result.classification_metadata:
                    meta = result.classification_metadata
                    doc_conf = meta.get("document_confidence", 0)
                    asset_conf = meta.get("asset_confidence", 0)
                    sender_known = meta.get("sender_known", False)

                    explanation_parts = []
                    if doc_conf < config.low_confidence_threshold:
                        explanation_parts.append(
                            f"low document classification confidence ({doc_conf:.2f})"
                        )
                    if asset_conf < config.requires_review_threshold:
                        explanation_parts.append(
                            f"uncertain asset match ({asset_conf:.2f})"
                        )
                    if not sender_known:
                        explanation_parts.append("unknown sender")

                    explanation = (
                        " + ".join(explanation_parts)
                        if explanation_parts
                        else "overall low confidence"
                    )
                    logger.info(f"Adding to human review: {explanation}")
                else:
                    logger.info(
                        f"Adding to human review: system flagged as {result.confidence_level.value}"
                    )

            if needs_review:
                try:
                    review_id = review_queue.add_for_review(
                        email_id=email.id,
                        mailbox_id=mailbox_id,
                        attachment_data=attachment_data,
                        email_data=email_data,
                        processing_result=result,
                    )
                    logger.info(f"Added attachment to human review queue: {review_id}")

                    # Track in processing info
                    processing_info.setdefault("needs_human_review", []).append(
                        {
                            "review_id": review_id,
                            "attachment_name": attachment.filename,
                            "reason": review_reason,
                        }
                    )

                except Exception as review_error:
                    logger.error(
                        f"Failed to add attachment to review queue: {review_error}"
                    )

        except Exception as e:
            logger.error(f"Failed to process attachment {attachment.filename}: {e}")

    return processing_info


@log_function()
def initialize_asset_agent() -> None:
    """
    Initialize the AssetDocumentAgent with Qdrant vector database if available.

    Creates a global asset_agent instance with either Qdrant integration
    or standalone file-based operation depending on availability.

    Raises:
        Exception: If initialization fails critically
    """
    global asset_agent

    # Guard against duplicate initialization
    if asset_agent is not None:
        logger.debug("AssetDocumentAgent already initialized, skipping")
        return

    if QDRANT_AVAILABLE:
        try:
            # Try to connect to local Qdrant instance
            qdrant_client = QdrantClient(
                host=config.qdrant_host, port=config.qdrant_port
            )
            asset_agent = AssetDocumentAgent(
                qdrant_client=qdrant_client, base_assets_path=config.assets_base_path
            )
            # Initialize collections asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asset_agent.initialize_collections())
            loop.close()

            logger.info("AssetDocumentAgent initialized with Qdrant")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            asset_agent = AssetDocumentAgent(base_assets_path=config.assets_base_path)
            logger.info("AssetDocumentAgent initialized without Qdrant")
    else:
        asset_agent = AssetDocumentAgent(base_assets_path=config.assets_base_path)
        logger.info("AssetDocumentAgent initialized without Qdrant (not installed)")


@app.route("/")
@log_function()
def index() -> str:
    """
    Main dashboard page displaying asset statistics and overview.

    Returns:
        Rendered HTML template for the dashboard
    """
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template(
            "error.html", error="Asset management system not initialized"
        )

    # Get asset statistics
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())

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
            document_types = []
            if document_types_str:
                document_types = [
                    dt.strip() for dt in document_types_str.split(",") if dt.strip()
                ]

            # Create mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            mapping_id = loop.run_until_complete(
                asset_agent.create_asset_sender_mapping(
                    asset_id=asset_id,
                    sender_email=sender_email,
                    confidence=confidence,
                    document_types=document_types,
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


@app.route("/api/process-emails", methods=["POST"])
@log_function()
def api_process_emails() -> tuple[dict, int] | dict:
    """API endpoint to process emails from selected mailbox"""
    if not asset_agent:
        logger.error("Asset agent not initialized for email processing")
        return jsonify({"error": "Asset agent not initialized"}), 500

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

        if "sender_mappings" in cleanup_types:
            result = _cleanup_sender_mappings()
            results["sender_mappings"] = result
            total_removed += result.get("removed_count", 0)

        if "assets" in cleanup_types:
            result = _cleanup_assets()
            results["assets"] = result
            total_removed += result.get("removed_count", 0)

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
        # # Third-party imports
        from qdrant_client.models import FieldCondition, Filter, Range

        # Delete all points that have a document_id field (which should be all of them)
        # Use a range filter that matches all possible UUIDs (starts with any character)
        asset_agent.qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        range=Range(
                            gte=""
                        ),  # Greater than or equal to empty string (matches all)
                    )
                ]
            ),
        )

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
        # # Third-party imports
        from qdrant_client.models import FieldCondition, Filter, Range

        asset_agent.qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="mapping_id",
                        range=Range(
                            gte=""
                        ),  # Greater than or equal to empty string (matches all)
                    )
                ]
            ),
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
        # # Third-party imports
        from qdrant_client.models import FieldCondition, Filter, Range

        asset_agent.qdrant.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="deal_id",
                        range=Range(
                            gte=""
                        ),  # Greater than or equal to empty string (matches all)
                    )
                ]
            ),
        )

        # Also remove asset folders from disk
        assets_path = Path(config.assets_base_path)
        if assets_path.exists():
            for asset_folder in assets_path.iterdir():
                if asset_folder.is_dir() and not asset_folder.name.startswith("."):
                    # Only remove folders that look like asset folders (uuid_name format)
                    if (
                        "_" in asset_folder.name
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

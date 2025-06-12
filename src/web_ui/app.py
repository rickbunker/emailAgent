#!/usr/bin/env python3
"""
Flask Web Application for Email Agent Asset Management

A user-friendly web interface for setting up and managing assets,
sender mappings, and document classification rules.
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from agents.asset_document_agent import (
    AssetDocumentAgent,
    AssetType,
    DocumentCategory,
)

# Email interface imports
from email_interface import (
    BaseEmailInterface,
    EmailSearchCriteria,
    create_email_interface,
)
from utils.logging_system import LogConfig, configure_logging, get_logger, log_function

from .human_review import review_queue

# Try to import Qdrant client
try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# Configure logging for the web UI
web_config = LogConfig(
    level="DEBUG",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/web_ui.log",
    log_arguments=True,
    log_return_values=False,  # Don't log return values for web routes (can be large)
    log_execution_time=True,
    max_arg_length=200
)
configure_logging(web_config)

# Get logger for this module
logger = get_logger("web_ui")

app = Flask(__name__)
app.secret_key = 'email-agent-asset-management-2024'  # Change in production

# Global asset agent instance
asset_agent: AssetDocumentAgent | None = None

# Email processing history to track processed emails
PROCESSED_EMAILS_FILE = "data/processed_emails.json"

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
            with open(self.file_path, 'w') as f:
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
            'processed_at': datetime.now(UTC).isoformat(),
            'processing_info': processing_info
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

# Global email processing history
email_history = EmailProcessingHistory()

@log_function()
def get_configured_mailboxes() -> list[dict[str, str]]:
    """Get list of configured mailboxes from existing credential files"""
    mailboxes = []

    # Check for Gmail configuration files
    gmail_credentials_file = 'config/gmail_credentials.json'
    gmail_token_file = 'config/gmail_token.json'

    if os.path.exists(gmail_credentials_file):
        mailboxes.append({
            'id': 'gmail_primary',
            'name': 'Gmail (Primary Account)',
            'type': 'gmail',
            'config': {
                'credentials_file': gmail_credentials_file,
                'token_file': gmail_token_file
            }
        })
        logger.info(f"Found Gmail configuration: {gmail_credentials_file}")

    # Check for Microsoft Graph configuration file
    msgraph_credentials_file = 'config/msgraph_credentials.json'

    if os.path.exists(msgraph_credentials_file):
        mailboxes.append({
            'id': 'msgraph_primary',
            'name': 'Microsoft 365 (Primary Account)',
            'type': 'microsoft_graph',
            'config': {
                'credentials_path': msgraph_credentials_file
            }
        })
        logger.info(f"Found Microsoft Graph configuration: {msgraph_credentials_file}")

    logger.info(f"Found {len(mailboxes)} configured mailboxes")
    return mailboxes

@log_function()
async def process_mailbox_emails(mailbox_config: dict, hours_back: int = 24, force_reprocess: bool = False) -> dict[str, Any]:
    """Process emails from a specific mailbox"""
    mailbox_id = mailbox_config['id']
    mailbox_type = mailbox_config['type']

    logger.info(f"Processing emails from mailbox: {mailbox_id} ({hours_back} hours back)")

    results = {
        'mailbox_id': mailbox_id,
        'total_emails': 0,
        'processed_emails': 0,
        'skipped_emails': 0,
        'errors': 0,
        'processing_details': []
    }

    try:
        # Create email interface based on type
        if mailbox_type == 'microsoft_graph':
            # Microsoft Graph uses credentials_path in constructor
            from email_interface.msgraph import MicrosoftGraphInterface
            email_interface = MicrosoftGraphInterface(credentials_path=mailbox_config['config']['credentials_path'])
            # Connect (credentials loaded in constructor)
            await email_interface.connect()
        else:
            # Gmail and others use the factory pattern
            email_interface = create_email_interface(mailbox_type, **mailbox_config['config'])
            # Connect with credentials
            await email_interface.connect(mailbox_config['config'])

        # Define search criteria for last 24 hours
        start_date = datetime.now(UTC) - timedelta(hours=hours_back)
        search_criteria = EmailSearchCriteria(
            has_attachments=True,  # Only process emails with attachments
            date_after=start_date
        )

        # Search for emails - try list_emails first, fallback if needed
        try:
            emails = await email_interface.list_emails(search_criteria)
        except Exception as list_error:
            # Fallback to basic search if advanced criteria not supported
            logger.warning(f"list_emails with criteria failed ({list_error}), trying basic search")
            basic_criteria = EmailSearchCriteria(has_attachments=True, max_results=100)
            all_emails = await email_interface.list_emails(basic_criteria)

            # Filter manually by date
            emails = []
            for email in all_emails:
                if email.received_date and email.received_date >= start_date:
                    emails.append(email)
        results['total_emails'] = len(emails)

        logger.info(f"Found {len(emails)} emails with attachments in the last {hours_back} hours")

        for email in emails:
            try:
                # Check if already processed
                if not force_reprocess and email_history.is_processed(email.id, mailbox_id):
                    results['skipped_emails'] += 1
                    logger.debug(f"Skipping already processed email: {email.id}")
                    continue

                # Process email and attachments
                processing_info = await process_single_email(email, email_interface, mailbox_id)

                # Mark as processed
                email_history.mark_processed(email.id, mailbox_id, processing_info)

                results['processed_emails'] += 1
                results['processing_details'].append({
                    'email_id': email.id,
                    'subject': email.subject,
                    'sender': email.sender.address if email.sender else 'Unknown',
                    'attachments_count': len(email.attachments) if email.attachments else 0,
                    'processing_info': processing_info
                })

                logger.info(f"Successfully processed email: {email.subject[:50]}...")

            except Exception as e:
                results['errors'] += 1
                logger.error(f"Failed to process email {email.id}: {e}")
                results['processing_details'].append({
                    'email_id': email.id,
                    'subject': email.subject,
                    'error': str(e)
                })

    except Exception as e:
        logger.error(f"Failed to process mailbox {mailbox_id}: {e}")
        results['error'] = str(e)

    finally:
        # Clean up email interface connection
        try:
            await email_interface.disconnect()
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up email interface: {cleanup_error}")

    logger.info(f"Mailbox processing complete: {results['processed_emails']} processed, {results['skipped_emails']} skipped, {results['errors']} errors")
    return results

@log_function()
async def process_single_email(email, email_interface: BaseEmailInterface, mailbox_id: str = 'unknown') -> dict[str, Any]:
    """Process a single email and its attachments"""
    if not asset_agent:
        raise Exception("Asset agent not initialized")

    processing_info = {
        'attachments_processed': 0,
        'attachments_classified': 0,
        'assets_matched': [],
        'processing_time': datetime.now(UTC).isoformat(),
        'quarantined': 0,
        'duplicates': 0,
        'errors': 0
    }

    logger.info(f"Processing email '{email.subject}' with {len(email.attachments) if email.attachments else 0} attachments")

    if not email.attachments:
        logger.warning(f"Email '{email.subject}' has no attachments to process")
        return processing_info

    for attachment in email.attachments:
        try:
            logger.info(f"Processing attachment: {attachment.filename} (size: {attachment.size}, content loaded: {attachment.content is not None})")

            # Get attachment content (may already be loaded)
            attachment_content = attachment.content

            if not attachment_content:
                # Try to download if not already loaded
                try:
                    attachment_content = await email_interface.download_attachment(email.id, attachment.id)
                except Exception as download_error:
                    logger.warning(f"Could not download attachment {attachment.filename}: {download_error}")
                    continue

            # Prepare attachment data for processing
            attachment_data = {
                'filename': attachment.filename,
                'content': attachment_content
            }

            email_data = {
                'sender_email': email.sender.address if email.sender else None,
                'sender_name': email.sender.name if email.sender else None,
                'subject': email.subject,
                'date': email.received_date.isoformat() if email.received_date else datetime.now(UTC).isoformat(),
                'body': email.body_text or email.body_html or ''
            }

            # Process with asset document agent (enhanced with asset matching)
            result = await asset_agent.enhanced_process_attachment(
                attachment_data=attachment_data,
                email_data=email_data
            )

            processing_info['attachments_processed'] += 1

            # Log processing result
            logger.info(f"Attachment processing result: status={result.status.value}, confidence={result.confidence}")

            # Handle different processing statuses
            if result.status.value == 'quarantined':
                logger.warning(f"Attachment quarantined: {result.quarantine_reason}")
                processing_info['quarantined'] = processing_info.get('quarantined', 0) + 1
            elif result.status.value == 'duplicate':
                logger.info(f"Attachment is duplicate of: {result.duplicate_of}")
                processing_info['duplicates'] = processing_info.get('duplicates', 0) + 1
            elif result.status.value == 'error':
                logger.error(f"Attachment processing error: {result.error_message}")
                processing_info['errors'] = processing_info.get('errors', 0) + 1

            if result.matched_asset_id:
                processing_info['attachments_classified'] += 1
                processing_info['assets_matched'].append({
                    'asset_id': result.matched_asset_id,
                    'confidence': result.asset_confidence,
                    'attachment_name': attachment.filename,
                    'file_path': str(result.file_path) if result.file_path else None,
                    'document_category': result.document_category.value if result.document_category else None,
                    'confidence_level': result.confidence_level.value if result.confidence_level else None,
                    'classification_metadata': result.classification_metadata or {}
                })
                logger.info(f"Attachment matched to asset: {result.matched_asset_id} (confidence: {result.asset_confidence})")
            else:
                logger.info("Attachment processed but no asset match found")

            # Check if attachment needs human review (low confidence or no match)
            needs_review = False
            if not result.matched_asset_id:
                # No asset match at all - needs review
                needs_review = True
                logger.info("Adding to human review: no asset match found")
            elif result.asset_confidence < 0.7:  # Low confidence threshold
                # Low confidence match - needs review
                needs_review = True
                logger.info(f"Adding to human review: low confidence ({result.asset_confidence:.2f})")
            elif hasattr(result, 'confidence_level') and result.confidence_level and result.confidence_level.value in ['very_low', 'low']:
                # System flagged as needing review
                needs_review = True
                logger.info(f"Adding to human review: system flagged as {result.confidence_level.value}")

            if needs_review:
                try:
                    review_id = review_queue.add_for_review(
                        email_id=email.id,
                        mailbox_id=mailbox_id,
                        attachment_data=attachment_data,
                        email_data=email_data,
                        processing_result=result
                    )
                    logger.info(f"Added attachment to human review queue: {review_id}")

                    # Track in processing info
                    processing_info.setdefault('needs_human_review', []).append({
                        'review_id': review_id,
                        'attachment_name': attachment.filename,
                        'reason': 'low_confidence' if result.matched_asset_id else 'no_match'
                    })

                except Exception as review_error:
                    logger.error(f"Failed to add attachment to review queue: {review_error}")

        except Exception as e:
            logger.error(f"Failed to process attachment {attachment.filename}: {e}")

    return processing_info

@log_function()
def initialize_asset_agent():
    """Initialize the AssetDocumentAgent with Qdrant if available"""
    global asset_agent
    
    # Guard against duplicate initialization
    if asset_agent is not None:
        logger.debug("AssetDocumentAgent already initialized, skipping")
        return

    if QDRANT_AVAILABLE:
        try:
            # Try to connect to local Qdrant instance
            qdrant_client = QdrantClient(host="localhost", port=6333)
            asset_agent = AssetDocumentAgent(
                qdrant_client=qdrant_client,
                base_assets_path="./assets"
            )
            # Initialize collections asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asset_agent.initialize_collections())
            loop.close()

            logger.info("AssetDocumentAgent initialized with Qdrant")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            asset_agent = AssetDocumentAgent(base_assets_path="./assets")
            logger.info("AssetDocumentAgent initialized without Qdrant")
    else:
        asset_agent = AssetDocumentAgent(base_assets_path="./assets")
        logger.info("AssetDocumentAgent initialized without Qdrant (not installed)")

@app.route('/')
@log_function()
def index():
    """Main dashboard page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

    # Get asset statistics
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())

        # Calculate statistics
        stats = {
            'total_assets': len(assets),
            'by_type': {},
            'recent_assets': assets[-5:] if assets else []  # Last 5 assets
        }

        # Count by asset type
        for asset in assets:
            asset_type = asset.asset_type.value
            stats['by_type'][asset_type] = stats['by_type'].get(asset_type, 0) + 1

        logger.info(f"Dashboard loaded with {len(assets)} assets")
        return render_template('dashboard.html', stats=stats, assets=assets)

    except Exception as e:
        logger.error(f"Failed to load dashboard: {e}")
        return render_template('error.html', error=f"Failed to load dashboard: {e}")
    finally:
        loop.close()

@app.route('/assets')
@log_function()
def list_assets():
    """List all assets page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

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
        return render_template('assets.html', assets=assets, asset_types=AssetType, type_counts=type_counts)

    except Exception as e:
        logger.error(f"Failed to load assets: {e}")
        return render_template('error.html', error=f"Failed to load assets: {e}")
    finally:
        loop.close()

@app.route('/assets/new', methods=['GET', 'POST'])
@log_function()
def create_asset():
    """Create new asset page"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

    if request.method == 'POST':
        try:
            # Get form data
            deal_name = request.form.get('deal_name', '').strip()
            asset_name = request.form.get('asset_name', '').strip()
            asset_type_str = request.form.get('asset_type', '')
            identifiers_str = request.form.get('identifiers', '').strip()

            logger.info(f"Creating asset: {deal_name} ({asset_type_str})")

            # Validate required fields
            if not deal_name or not asset_name or not asset_type_str:
                logger.warning("Asset creation failed: missing required fields")
                flash('Deal name, asset name, and asset type are required', 'error')
                return render_template('create_asset.html',
                                     asset_types=AssetType,
                                     form_data=request.form)

            # Parse asset type
            try:
                asset_type = AssetType(asset_type_str)
            except ValueError:
                logger.warning(f"Invalid asset type selected: {asset_type_str}")
                flash('Invalid asset type selected', 'error')
                return render_template('create_asset.html',
                                     asset_types=AssetType,
                                     form_data=request.form)

            # Parse identifiers
            identifiers = []
            if identifiers_str:
                identifiers = [id_.strip() for id_ in identifiers_str.split(',') if id_.strip()]

            # Create asset
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            deal_id = loop.run_until_complete(asset_agent.create_asset(
                deal_name=deal_name,
                asset_name=asset_name,
                asset_type=asset_type,
                identifiers=identifiers
            ))

            loop.close()

            logger.info(f"Asset created successfully: {deal_name} with ID: {deal_id[:8]}...")
            flash(f'Asset "{deal_name}" created successfully with ID: {deal_id[:8]}...', 'success')
            return redirect(url_for('list_assets'))

        except Exception as e:
            logger.error(f"Failed to create asset: {e}")
            flash(f'Failed to create asset: {e}', 'error')
            return render_template('create_asset.html',
                                 asset_types=AssetType,
                                 form_data=request.form)

    return render_template('create_asset.html',
                         asset_types=AssetType,
                         document_categories=DocumentCategory)

@app.route('/assets/<deal_id>')
@log_function()
def view_asset(deal_id: str):
    """View specific asset details"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get asset details
        asset = loop.run_until_complete(asset_agent.get_asset(deal_id))

        if not asset:
            logger.warning(f"Asset not found: {deal_id}")
            flash('Asset not found', 'error')
            return redirect(url_for('list_assets'))

        logger.info(f"Viewing asset: {asset.deal_name}")

        # Get sender mappings for this asset
        all_mappings = loop.run_until_complete(asset_agent.list_asset_sender_mappings())
        sender_mappings = [m for m in all_mappings if m['asset_id'] == deal_id]

        return render_template('asset_detail.html',
                             asset=asset,
                             sender_mappings=sender_mappings,
                             document_categories=DocumentCategory)

    except Exception as e:
        logger.error(f"Failed to load asset {deal_id}: {e}")
        return render_template('error.html', error=f"Failed to load asset: {e}")
    finally:
        loop.close()

@app.route('/assets/<deal_id>/edit', methods=['GET', 'POST'])
@log_function()
def edit_asset(deal_id: str):
    """Edit asset details"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get current asset details
        asset = loop.run_until_complete(asset_agent.get_asset(deal_id))

        if not asset:
            logger.warning(f"Asset not found: {deal_id}")
            flash('Asset not found', 'error')
            return redirect(url_for('list_assets'))

        if request.method == 'POST':
            # Update asset logic would go here
            flash('Asset editing not yet implemented', 'warning')
            return redirect(url_for('view_asset', deal_id=deal_id))

        return render_template('edit_asset.html',
                             asset=asset,
                             asset_types=AssetType)

    except Exception as e:
        logger.error(f"Failed to load asset for editing {deal_id}: {e}")
        return render_template('error.html', error=f"Failed to load asset: {e}")
    finally:
        loop.close()

@app.route('/assets/<deal_id>/delete', methods=['POST'])
@log_function()
def delete_asset(deal_id: str):
    """Delete an asset"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return jsonify({'error': 'Asset agent not initialized'}), 500

    try:
        # Delete asset logic would go here
        flash('Asset deletion not yet implemented', 'warning')
        return redirect(url_for('list_assets'))

    except Exception as e:
        logger.error(f"Failed to delete asset {deal_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/senders')
@log_function()
def list_senders():
    """List all sender mappings with asset names"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

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
            asset_id = mapping['asset_id']
            asset = asset_lookup.get(asset_id)

            enriched_mapping = mapping.copy()
            if asset:
                enriched_mapping['asset_name'] = asset.deal_name
                enriched_mapping['asset_type'] = asset.asset_type.value
                enriched_mapping['asset_full_name'] = asset.asset_name
            else:
                enriched_mapping['asset_name'] = f"Unknown Asset ({asset_id[:8]}...)"
                enriched_mapping['asset_type'] = "unknown"
                enriched_mapping['asset_full_name'] = "Asset not found"

            enriched_mappings.append(enriched_mapping)

        logger.info(f"Sender mappings page loaded with {len(enriched_mappings)} mappings")
        return render_template('senders.html', mappings=enriched_mappings)

    except Exception as e:
        logger.error(f"Failed to load sender mappings: {e}")
        return render_template('error.html', error=f"Failed to load sender mappings: {e}")
    finally:
        loop.close()

@app.route('/senders/new', methods=['GET', 'POST'])
@log_function()
def create_sender_mapping():
    """Create new sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset management system not initialized")
        return render_template('error.html',
                             error="Asset management system not initialized")

    if request.method == 'POST':
        try:
            # Get form data
            asset_id = request.form.get('asset_id', '').strip()
            sender_email = request.form.get('sender_email', '').strip().lower()
            confidence = float(request.form.get('confidence', 0.8))
            document_types_str = request.form.get('document_types', '').strip()

            logger.info(f"Creating sender mapping: {sender_email} -> {asset_id}")

            # Validate
            if not asset_id or not sender_email:
                logger.warning("Sender mapping creation failed: missing required fields")
                flash('Asset and sender email are required', 'error')
                return render_template('create_sender_mapping.html')

            # Parse document types
            document_types = []
            if document_types_str:
                document_types = [dt.strip() for dt in document_types_str.split(',') if dt.strip()]

            # Create mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            mapping_id = loop.run_until_complete(asset_agent.create_asset_sender_mapping(
                asset_id=asset_id,
                sender_email=sender_email,
                confidence=confidence,
                document_types=document_types
            ))

            loop.close()

            logger.info(f"Sender mapping created successfully: {mapping_id[:8]}...")
            flash(f'Sender mapping created successfully: {mapping_id[:8]}...', 'success')
            return redirect(url_for('list_senders'))

        except Exception as e:
            logger.error(f"Failed to create sender mapping: {e}")
            flash(f'Failed to create sender mapping: {e}', 'error')

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

    return render_template('create_sender_mapping.html',
                         assets=assets,
                         document_categories=DocumentCategory)

@app.route('/api/assets')
@log_function()
def api_list_assets():
    """API endpoint to list assets (for AJAX calls)"""
    if not asset_agent:
        logger.error("Asset management system not initialized for API call")
        return jsonify({'error': 'Asset management system not initialized'}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        assets = loop.run_until_complete(asset_agent.list_assets())

        assets_data = []
        for asset in assets:
            assets_data.append({
                'deal_id': asset.deal_id,
                'deal_name': asset.deal_name,
                'asset_name': asset.asset_name,
                'asset_type': asset.asset_type.value,
                'identifiers': asset.identifiers,
                'created_date': asset.created_date.isoformat(),
                'folder_path': asset.folder_path
            })

        logger.info(f"API returned {len(assets_data)} assets")
        return jsonify({'assets': assets_data})

    except Exception as e:
        logger.error(f"API failed to list assets: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        loop.close()

@app.route('/api/health')
@log_function()
def api_health():
    """API health check endpoint"""
    if not asset_agent:
        logger.error("Asset agent not initialized for health check")
        return jsonify({'status': 'error', 'message': 'Asset agent not initialized'}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        health = loop.run_until_complete(asset_agent.health_check())
        logger.info("Health check completed successfully")
        return jsonify({'status': 'ok', 'health': health})
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        loop.close()

@app.route('/email-processing')
@log_function()
def email_processing():
    """Email processing management page"""
    logger.info("Loading email processing page")

    # Get configured mailboxes
    mailboxes = get_configured_mailboxes()

    # Get recent processing history
    recent_history = []
    try:
        # Get last 10 processed emails from history
        for key, info in list(email_history.processed_emails.items())[-10:]:
            mailbox_id, email_id = key.split(':', 1)
            recent_history.append({
                'mailbox_id': mailbox_id,
                'email_id': email_id,
                'processed_at': info.get('processed_at'),
                'processing_info': info.get('processing_info', {})
            })
    except Exception as e:
        logger.warning(f"Failed to load recent processing history: {e}")

    return render_template('email_processing.html',
                         mailboxes=mailboxes,
                         recent_history=recent_history,
                         total_processed=len(email_history.processed_emails))

@app.route('/api/process-emails', methods=['POST'])
@log_function()
def api_process_emails():
    """API endpoint to process emails from selected mailbox"""
    if not asset_agent:
        logger.error("Asset agent not initialized for email processing")
        return jsonify({'error': 'Asset agent not initialized'}), 500

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        mailbox_id = data.get('mailbox_id')
        hours_back = int(data.get('hours_back', 24))
        force_reprocess = data.get('force_reprocess', False)

        if not mailbox_id:
            return jsonify({'error': 'Mailbox ID is required'}), 400

        # Get mailbox configuration
        mailboxes = get_configured_mailboxes()
        mailbox_config = None
        for mailbox in mailboxes:
            if mailbox['id'] == mailbox_id:
                mailbox_config = mailbox
                break

        if not mailbox_config:
            return jsonify({'error': f'Mailbox {mailbox_id} not found'}), 404

        logger.info(f"Starting email processing for mailbox: {mailbox_id}")

        # Process emails asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            results = loop.run_until_complete(
                process_mailbox_emails(mailbox_config, hours_back, force_reprocess)
            )

            logger.info(f"Email processing completed: {results}")
            return jsonify({'status': 'success', 'results': results})

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Email processing API failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mailboxes')
@log_function()
def api_mailboxes():
    """API endpoint to get configured mailboxes"""
    try:
        mailboxes = get_configured_mailboxes()
        return jsonify({'mailboxes': mailboxes})
    except Exception as e:
        logger.error(f"Failed to get mailboxes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/processing-history')
@log_function()
def api_processing_history():
    """API endpoint to get email processing history"""
    try:
        history = []
        for key, info in email_history.processed_emails.items():
            mailbox_id, email_id = key.split(':', 1)
            history.append({
                'mailbox_id': mailbox_id,
                'email_id': email_id,
                'processed_at': info.get('processed_at'),
                'processing_info': info.get('processing_info', {})
            })

        # Sort by processed_at descending
        history.sort(key=lambda x: x.get('processed_at', ''), reverse=True)

        return jsonify({'history': history})
    except Exception as e:
        logger.error(f"Failed to get processing history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
@log_function()
def api_clear_history():
    """API endpoint to clear processing history"""
    try:
        data = request.get_json() or {}
        email_id = data.get('email_id')
        mailbox_id = data.get('mailbox_id')

        email_history.clear_processed(email_id, mailbox_id)

        action = "all history" if not email_id else f"history for {mailbox_id}:{email_id}"
        logger.info(f"Cleared processing history: {action}")

        return jsonify({'status': 'success', 'message': f'Cleared {action}'})
    except Exception as e:
        logger.error(f"Failed to clear processing history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/senders/<mapping_id>/delete', methods=['POST'])
@log_function()
def delete_sender_mapping(mapping_id: str):
    """Delete a sender-asset mapping"""
    if not asset_agent:
        logger.error("Asset agent not initialized for sender mapping deletion")
        return jsonify({'error': 'Asset agent not initialized'}), 500

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(asset_agent.delete_asset_sender_mapping(mapping_id))

        if success:
            logger.info(f"Sender mapping deleted successfully: {mapping_id}")
            flash('Sender mapping deleted successfully', 'success')
        else:
            logger.warning(f"Sender mapping not found: {mapping_id}")
            flash('Sender mapping not found', 'error')

        return redirect(url_for('list_senders'))

    except Exception as e:
        logger.error(f"Failed to delete sender mapping {mapping_id}: {e}")
        flash(f'Failed to delete sender mapping: {e}', 'error')
        return redirect(url_for('list_senders'))
    finally:
        loop.close()

# Human Review Routes

@app.route('/human-review')
@log_function()
def human_review_queue():
    """Human review queue page"""
    try:
        # Get pending review items
        pending_items = review_queue.get_pending_items(limit=50)

        # Get queue statistics
        stats = review_queue.get_stats()

        # Get available assets for dropdown
        if not asset_agent:
            logger.error("Asset management system not initialized")
            return render_template('error.html',
                                 error="Asset management system not initialized")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assets = loop.run_until_complete(asset_agent.list_assets())
        finally:
            loop.close()

        logger.info(f"Human review page loaded with {len(pending_items)} pending items")
        return render_template('human_review.html',
                             pending_items=pending_items,
                             stats=stats,
                             assets=assets,
                             document_categories=DocumentCategory)

    except Exception as e:
        logger.error(f"Failed to load human review page: {e}")
        return render_template('error.html', error=f"Failed to load human review page: {e}")

@app.route('/human-review/<review_id>')
@log_function()
def human_review_item(review_id: str):
    """Individual review item page"""
    try:
        # Get the specific review item
        review_item = review_queue.get_item(review_id)

        if not review_item:
            logger.warning(f"Review item not found: {review_id}")
            flash('Review item not found', 'error')
            return redirect(url_for('human_review_queue'))

        # Get available assets for selection
        if not asset_agent:
            logger.error("Asset management system not initialized")
            return render_template('error.html',
                                 error="Asset management system not initialized")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            assets = loop.run_until_complete(asset_agent.list_assets())

            # Get asset names for system suggestions
            asset_lookup = {asset.deal_id: asset for asset in assets}

            # Enhance system suggestions with asset names
            if review_item.get('system_asset_suggestions'):
                for suggestion in review_item['system_asset_suggestions']:
                    if suggestion['asset_id'] in asset_lookup:
                        asset = asset_lookup[suggestion['asset_id']]
                        suggestion['asset_name'] = asset.deal_name
                        suggestion['asset_type'] = asset.asset_type.value
        finally:
            loop.close()

        logger.info(f"Loaded review item: {review_id}")
        return render_template('human_review_item.html',
                             review_item=review_item,
                             assets=assets,
                             document_categories=DocumentCategory)

    except Exception as e:
        logger.error(f"Failed to load review item {review_id}: {e}")
        return render_template('error.html', error=f"Failed to load review item: {e}")

@app.route('/api/human-review/<review_id>/submit', methods=['POST'])
@log_function()
def api_submit_review(review_id: str):
    """Submit human review correction"""
    try:
        data = request.get_json()

        human_asset_id = data.get('asset_id')
        human_document_category = data.get('document_category')
        human_reasoning = data.get('reasoning', '')
        human_feedback = data.get('feedback', '')
        reviewed_by = data.get('reviewed_by', 'web_user')

        if not human_asset_id or not human_document_category:
            return jsonify({'error': 'Asset ID and document category are required'}), 400

        # Submit the review asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success = loop.run_until_complete(review_queue.submit_review(
                review_id=review_id,
                human_asset_id=human_asset_id,
                human_document_category=human_document_category,
                human_reasoning=human_reasoning,
                human_feedback=human_feedback,
                reviewed_by=reviewed_by
            ))

            if success:
                logger.info(f"Review submitted successfully: {review_id}")
                return jsonify({'success': True, 'message': 'Review submitted successfully'})
            else:
                logger.error(f"Failed to submit review: {review_id}")
                return jsonify({'error': 'Failed to submit review'}), 500

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error submitting review {review_id}: {e}")
        return jsonify({'error': f'Error submitting review: {str(e)}'}), 500

@app.route('/api/human-review/stats')
@log_function()
def api_human_review_stats():
    """Get human review queue statistics"""
    try:
        stats = review_queue.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get review stats: {e}")
        return jsonify({'error': f'Failed to get review stats: {str(e)}'}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {request.url}")
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return render_template('error.html', error='Internal server error'), 500

def create_app():
    """Application factory function"""
    # Only initialize in Flask's reloader process (the actual running process)
    # Skip initialization in the parent process that just spawns the reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        logger.debug("Initializing in Flask reloader process")
    else:
        logger.debug("Skipping initialization in Flask parent process")
        return app
        
    # Initialize the asset agent (with guard against duplicates)
    initialize_asset_agent()
    return app

if __name__ == '__main__':
    # Only initialize if not already done (Flask debug mode protection)
    if asset_agent is None:
        initialize_asset_agent()

    logger.info("🌐 Starting Email Agent Asset Management Web UI")
    logger.info("📊 Dashboard: http://localhost:5000")
    logger.info("🏢 Assets: http://localhost:5000/assets")
    logger.info("📧 Senders: http://localhost:5000/senders")

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

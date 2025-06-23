#!/usr/bin/env python3
"""
Inveniam E-mail Agent - Simple Flask Frontend for Testing

A basic web interface for testing email processing functionality
with human feedback integration and learning capabilities.
"""

# # Standard library imports
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# # Standard library imports
from datetime import datetime

# # Third-party imports
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

# # Local application imports
from src.agents.email_graph import EmailProcessingGraph
from src.email_interface.base import EmailSearchCriteria

# Import our email processing system
from src.email_interface.factory import EmailInterfaceFactory, EmailSystemType
from src.memory import create_memory_systems
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.flask_secret_key

# Initialize logger
logger = get_logger(__name__)

# Global variables for the email processing system
email_graph = None
memory_systems = None
gmail_interface = None
msgraph_interface = None


def _clean_bytes_from_dict(obj: Any) -> Any:
    """Recursively clean bytes objects from dictionaries for JSON serialization."""
    if isinstance(obj, bytes):
        return f"<bytes: {len(obj)} bytes>"
    elif isinstance(obj, dict):
        return {key: _clean_bytes_from_dict(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_clean_bytes_from_dict(item) for item in obj]
    else:
        return obj


@log_function()
def initialize_system() -> bool:
    """
    Initialize the email processing system.

    Returns:
        True if initialization successful, False otherwise
    """
    global email_graph, memory_systems, gmail_interface, msgraph_interface

    try:
        logger.info("Initializing Inveniam E-mail Agent system...")

        # Create memory systems
        memory_systems = create_memory_systems()
        logger.info("Memory systems initialized")

        # Create email processing graph
        email_graph = EmailProcessingGraph()
        logger.info("Email processing graph initialized")

        # Initialize email interfaces
        try:
            gmail_interface = EmailInterfaceFactory.create(EmailSystemType.GMAIL.value)
            logger.info("Gmail interface created")
        except Exception as e:
            logger.warning(f"Gmail interface not available: {e}")

        try:
            msgraph_interface = EmailInterfaceFactory.create(
                EmailSystemType.MICROSOFT_GRAPH.value
            )
            logger.info("Microsoft Graph interface created")
        except Exception as e:
            logger.warning(f"Microsoft Graph interface not available: {e}")

        logger.info("System initialization complete")
        return True

    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        return False


@app.route("/")
def index() -> str:
    """
    Main dashboard page.

    Returns:
        Rendered HTML template
    """
    return render_template("index.html")


@app.route("/api/system/status")
def system_status() -> dict[str, Any]:
    """
    Get system status information.

    Returns:
        JSON response with system status
    """
    return jsonify(
        {
            "memory_systems": memory_systems is not None,
            "email_graph": email_graph is not None,
            "gmail_available": gmail_interface is not None,
            "msgraph_available": msgraph_interface is not None,
        }
    )


@app.route("/api/system/diagnostics")
def system_diagnostics() -> dict[str, Any]:
    """
    Get detailed system diagnostics for troubleshooting.

    Returns:
        JSON response with diagnostic information
    """
    diagnostics = {
        "memory_systems": {
            "available": memory_systems is not None,
            "types": list(memory_systems.keys()) if memory_systems else [],
        },
        "email_graph": {
            "available": email_graph is not None,
            "class": email_graph.__class__.__name__ if email_graph else None,
        },
        "email_interfaces": {
            "gmail": {
                "interface_created": gmail_interface is not None,
                "credentials_file_exists": Path(config.gmail_credentials_path).exists(),
                "token_file_exists": Path(config.gmail_token_path).exists(),
                "error": None,
            },
            "msgraph": {
                "interface_created": msgraph_interface is not None,
                "credentials_file_exists": Path(
                    config.msgraph_credentials_path
                ).exists(),
                "error": None,
            },
        },
        "configuration": {
            "flask_port": config.flask_port,
            "flask_host": config.flask_host,
            "debug_mode": config.debug,
            "development_mode": config.development_mode,
        },
    }

    # Add error details if interfaces failed to create
    if gmail_interface is None:
        try:
            EmailInterfaceFactory.create(EmailSystemType.GMAIL.value)
        except Exception as e:
            diagnostics["email_interfaces"]["gmail"]["error"] = str(e)

    if msgraph_interface is None:
        try:
            EmailInterfaceFactory.create(EmailSystemType.MICROSOFT_GRAPH.value)
        except Exception as e:
            diagnostics["email_interfaces"]["msgraph"]["error"] = str(e)

    return jsonify(diagnostics)


@app.route("/api/process_emails", methods=["POST"])
def process_emails() -> tuple[dict[str, Any], int] | dict[str, Any]:
    """
    Process emails from selected account.

    Returns:
        JSON response with processing results or error
    """
    try:
        data = request.json
        email_system = data.get("email_system")  # 'gmail' or 'msgraph'
        max_emails = data.get("max_emails", 5)

        if not email_system:
            return jsonify({"error": "Email system not specified"}), 400

        # Select the appropriate interface
        if email_system == "gmail" and gmail_interface:
            interface = gmail_interface
        elif email_system == "msgraph" and msgraph_interface:
            interface = msgraph_interface
        else:
            return jsonify({"error": f"Email system {email_system} not available"}), 400

        # Process emails asynchronously
        results = asyncio.run(process_emails_async(interface, max_emails))

        return jsonify(results)

    except Exception as e:
        logger.error(f"Email processing error: {e}")
        return jsonify({"error": str(e)}), 500


@log_function()
async def process_emails_async(interface: Any, max_emails: int) -> dict[str, Any]:
    """
    Process emails asynchronously.

    Args:
        interface: Email interface instance (Gmail or Microsoft Graph)
        max_emails: Maximum number of emails to process

    Returns:
        Dictionary with processing results
    """
    try:
        # Connect to email system
        logger.info(f"Connecting to {interface.__class__.__name__}...")

        if hasattr(interface, "connect"):
            if interface.__class__.__name__ == "GmailInterface":
                # Gmail needs credentials
                await interface.connect(
                    {
                        "credentials_file": "config/gmail_credentials.json",
                        "token_file": "config/gmail_token.json",
                    }
                )
            else:
                # Microsoft Graph
                await interface.connect()

        # Get recent emails with attachments
        criteria = EmailSearchCriteria(
            max_results=max_emails, has_attachments=None
        )  # None means include both
        emails = await interface.list_emails(criteria)

        logger.info(f"Retrieved {len(emails)} emails for processing")

        # Process each email through the graph
        processed_results = []

        for i, email in enumerate(emails, 1):
            logger.info(f"Processing email {i}/{len(emails)}: {email.subject[:50]}...")

            # Convert email to processing format
            logger.info(f"Email has {len(email.attachments)} attachments")
            for j, att in enumerate(email.attachments):
                logger.info(
                    f"  Attachment {j+1}: {att.filename} ({att.size} bytes, {att.content_type})"
                )

            email_data = {
                "subject": email.subject,
                "sender": email.sender.address,
                "body": email.body_text or email.body_html or "",
                "attachments": [
                    {
                        "filename": att.filename,
                        "content": (
                            att.content if att.content else b"placeholder"
                        ),  # Use actual content if available
                        "content_type": att.content_type,
                        "size": att.size,
                    }
                    for att in email.attachments
                ],
            }

            # Process through the graph
            result = await email_graph.process_email(email_data)

            # Log processing results for debugging
            logger.info(f"=== PROCESSING RESULT FOR: {email.subject[:60]} ===")
            logger.info(f"Sender: {email.sender.address}")
            logger.info(f"Attachments: {len(email.attachments)}")
            if email.attachments:
                for att in email.attachments:
                    logger.info(f"  - {att.filename}")

            # Log key results
            if result.get("relevance_result"):
                rel = result["relevance_result"]
                logger.info(
                    f"Relevance: {rel.get('relevance')} (confidence: {rel.get('confidence')})"
                )

            if result.get("asset_matches"):
                matches = result["asset_matches"]
                if matches:
                    logger.info(f"Asset Matches: {len(matches)}")
                    for match in matches:
                        logger.info(
                            f"  - {match.get('asset_id')} (confidence: {match.get('confidence')})"
                        )
                else:
                    logger.info("Asset Matches: None")

            if result.get("actions"):
                logger.info(f"Actions: {result['actions']}")

            if result.get("processing_errors"):
                logger.error(f"Processing Errors: {result['processing_errors']}")

            logger.info("=" * 60)

            # Add summary info
            processed_results.append(
                {
                    "email_subject": email.subject[:60],
                    "sender": email.sender.address,
                    "received_date": (
                        email.received_date.isoformat() if email.received_date else None
                    ),
                    "attachments_count": len(email.attachments),
                    "processing_result": result,
                }
            )

        # Disconnect
        await interface.disconnect()

        # Clean results by removing bytes content before JSON serialization
        cleaned_results = []
        for result in processed_results:
            cleaned_result = result.copy()
            # Clean attachment content from the processing result
            if "processing_result" in cleaned_result:
                cleaned_result["processing_result"] = _clean_bytes_from_dict(
                    cleaned_result["processing_result"]
                )
            cleaned_results.append(cleaned_result)

        return {
            "success": True,
            "processed_count": len(cleaned_results),
            "results": cleaned_results,
        }

    except Exception as e:
        logger.error(f"Async email processing error: {e}")
        return {"success": False, "error": str(e)}


@app.route("/attachments")
def attachment_browser() -> str:
    """Render attachment browser page."""
    return render_template("attachments.html")


@app.route("/api/attachments/assets", methods=["GET"])
def list_assets() -> dict[str, Any]:
    """List all asset folders with attachment counts."""
    try:
        assets_path = Path(config.assets_base_path)
        assets = []

        if assets_path.exists():
            for asset_dir in assets_path.iterdir():
                if asset_dir.is_dir():
                    # Count files in this asset directory
                    file_count = len([f for f in asset_dir.iterdir() if f.is_file()])

                    # Get asset info from semantic memory if available
                    asset_info = {
                        "name": asset_dir.name,
                        "display_name": asset_dir.name,
                    }

                    if memory_systems:
                        try:
                            # Get asset name from semantic memory
                            semantic_memory = memory_systems["semantic"]
                            asset_profiles = semantic_memory.search_asset_profiles(
                                asset_dir.name, limit=1
                            )
                            if asset_profiles:
                                asset_info["display_name"] = asset_profiles[0][
                                    "profile"
                                ].get("name", asset_dir.name)
                        except Exception as e:
                            logger.warning(f"Failed to get asset info: {e}")

                    assets.append(
                        {
                            "id": asset_dir.name,
                            "name": asset_info["display_name"],
                            "file_count": file_count,
                            "path": str(asset_dir),
                        }
                    )

        # Sort by name
        assets.sort(key=lambda x: x["name"])

        return jsonify(
            {
                "assets": assets,
                "total_assets": len(assets),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/attachments/assets/<asset_id>", methods=["GET"])
def list_asset_attachments(asset_id: str) -> dict[str, Any]:
    """List attachments for a specific asset."""
    try:
        asset_path = Path(config.assets_base_path) / asset_id
        attachments = []

        if asset_path.exists() and asset_path.is_dir():
            for file_path in asset_path.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    attachments.append(
                        {
                            "filename": file_path.name,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "path": str(
                                file_path.relative_to(Path(config.assets_base_path))
                            ),
                        }
                    )

        # Sort by modification date (newest first)
        attachments.sort(key=lambda x: x["modified"], reverse=True)

        return jsonify(
            {
                "asset_id": asset_id,
                "attachments": attachments,
                "total_files": len(attachments),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to list attachments for asset {asset_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/attachments/download/<path:file_path>", methods=["GET"])
def download_attachment(file_path: str) -> Any:
    """Download an attachment file."""
    try:
        full_path = Path(config.assets_base_path) / file_path

        # Security check: ensure file is within assets directory
        if not str(full_path.resolve()).startswith(
            str(Path(config.assets_base_path).resolve())
        ):
            return jsonify({"error": "Access denied"}), 403

        if not full_path.exists() or not full_path.is_file():
            return jsonify({"error": "File not found"}), 404

        return send_file(full_path, as_attachment=True, download_name=full_path.name)

    except Exception as e:
        logger.error(f"Failed to download file {file_path}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Initialize the system
    if not initialize_system():
        print("Failed to initialize system. Exiting.")
        sys.exit(1)

    # Run Flask app
    print("Starting Inveniam E-mail Agent web interface...")
    print(f"Visit: http://localhost:{config.flask_port}")

    app.run(host=config.flask_host, port=config.flask_port, debug=config.debug)

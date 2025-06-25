#!/usr/bin/env python3
"""
Inveniam E-mail Agent - Simple Flask Frontend for Testing

A basic web interface for testing email processing functionality
with human feedback integration and learning capabilities.
"""

# # Standard library imports
# Standard library imports
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# # Third-party imports
# Third-party imports
from flask import Flask, jsonify, render_template, request, send_file

# # Local application imports
# Local application imports
from src.agents.email_graph import EmailProcessingGraph
from src.email_interface.base import EmailSearchCriteria
from src.email_interface.factory import EmailInterfaceFactory, EmailSystemType
from src.memory import create_memory_systems
from src.memory.simple_memory import reset_all_memory_to_baseline
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.flask_secret_key


# Add CSP headers to allow JavaScript execution
@app.after_request
def add_security_headers(response):
    """Add security headers including CSP to allow legitimate JavaScript."""
    # Content Security Policy that allows our inline scripts and fetch calls
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


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
                if not att.content:
                    logger.warning(f"    No content loaded for {att.filename}")

            # Filter out attachments without content
            valid_attachments = []
            for att in email.attachments:
                if att.content:
                    valid_attachments.append(
                        {
                            "filename": att.filename,
                            "content": att.content,
                            "content_type": att.content_type,
                            "size": att.size,
                        }
                    )
                else:
                    logger.warning(
                        f"Skipping attachment {att.filename} - no content loaded"
                    )

            email_data = {
                "subject": email.subject,
                "sender": email.sender.address,
                "body": email.body_text or email.body_html or "",
                "attachments": valid_attachments,
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


# ===== MEMORY MANAGEMENT API ENDPOINTS =====


@app.route("/memory")
def memory_management() -> str:
    """Serve the memory management page."""
    return render_template("memory.html")


@app.route("/api/memory/semantic", methods=["GET"])
def get_semantic_memory() -> dict[str, Any]:
    """Get semantic memory data."""
    try:
        if not memory_systems or not memory_systems.get("semantic"):
            return {"error": "Semantic memory not available"}, 500

        semantic_memory = memory_systems["semantic"]
        return {
            "success": True,
            "data": semantic_memory.data,
            "stats": {
                "asset_profiles_count": len(
                    semantic_memory.data.get("asset_profiles", {})
                ),
                "file_type_rules_count": len(
                    semantic_memory.data.get("file_type_rules", {})
                ),
                "sender_mappings_count": len(
                    semantic_memory.data.get("sender_mappings", {})
                ),
                "organization_contacts_count": len(
                    semantic_memory.data.get("organization_contacts", {})
                ),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get semantic memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/semantic", methods=["PUT"])
def update_semantic_memory() -> tuple[dict, int]:
    """Update semantic memory data."""
    try:
        if not memory_systems or not memory_systems.get("semantic"):
            return {"error": "Semantic memory not available"}, 500

        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        semantic_memory = memory_systems["semantic"]

        # Validate the data structure
        required_keys = [
            "asset_profiles",
            "file_type_rules",
            "sender_mappings",
            "organization_contacts",
        ]
        for key in required_keys:
            if key not in data:
                return {"error": f"Missing required key: {key}"}, 400

        # Update the data
        semantic_memory.data = data
        semantic_memory._save_data()

        logger.info("Semantic memory updated via API")
        return {"success": True, "message": "Semantic memory updated successfully"}, 200

    except Exception as e:
        logger.error(f"Failed to update semantic memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/procedural", methods=["GET"])
def get_procedural_memory() -> dict[str, Any]:
    """Get procedural memory data."""
    try:
        if not memory_systems or not memory_systems.get("procedural"):
            return {"error": "Procedural memory not available"}, 500

        procedural_memory = memory_systems["procedural"]
        return {
            "success": True,
            "data": procedural_memory.data,
            "stats": {
                "relevance_rules_count": len(
                    procedural_memory.data.get("relevance_rules", [])
                ),
                "asset_matching_rules_count": len(
                    procedural_memory.data.get("asset_matching_rules", [])
                ),
                "file_processing_rules_count": len(
                    procedural_memory.data.get("file_processing_rules", [])
                ),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get procedural memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/procedural", methods=["PUT"])
def update_procedural_memory() -> tuple[dict, int]:
    """Update procedural memory data."""
    try:
        if not memory_systems or not memory_systems.get("procedural"):
            return {"error": "Procedural memory not available"}, 500

        data = request.get_json()
        if not data:
            return {"error": "No data provided"}, 400

        procedural_memory = memory_systems["procedural"]

        # Validate the data structure
        required_keys = [
            "relevance_rules",
            "asset_matching_rules",
            "file_processing_rules",
        ]
        for key in required_keys:
            if key not in data:
                return {"error": f"Missing required key: {key}"}, 400

        # Update the data
        procedural_memory.data = data
        procedural_memory._save_data()

        logger.info("Procedural memory updated via API")
        return {
            "success": True,
            "message": "Procedural memory updated successfully",
        }, 200

    except Exception as e:
        logger.error(f"Failed to update procedural memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/episodic", methods=["GET"])
def get_episodic_memory() -> dict[str, Any]:
    """Get episodic memory data with optional filtering."""
    try:
        if not memory_systems or not memory_systems.get("episodic"):
            return {"error": "Episodic memory not available"}, 500

        episodic_memory = memory_systems["episodic"]

        # Get query parameters for filtering
        limit = request.args.get("limit", 50, type=int)
        search_query = request.args.get("search", "")
        sender_filter = request.args.get("sender", "")
        asset_filter = request.args.get("asset", "")

        # Get recent records
        records = episodic_memory.get_recent_records(limit=limit)

        # Apply filters
        if search_query:
            search_lower = search_query.lower()
            records = [
                r
                for r in records
                if search_lower in r.get("subject", "").lower()
                or search_lower in r.get("sender", "").lower()
                or search_lower in r.get("asset_id", "").lower()
            ]

        if sender_filter:
            records = [
                r
                for r in records
                if sender_filter.lower() in r.get("sender", "").lower()
            ]

        if asset_filter:
            records = [r for r in records if asset_filter == r.get("asset_id", "")]

        # Get feedback history
        feedback_records = episodic_memory.get_feedback_history(limit=20)

        # Get schema validation info
        schema_info = episodic_memory.validate_schema()

        return {
            "success": True,
            "processing_records": records,
            "feedback_records": feedback_records,
            "schema_info": schema_info,
            "stats": {
                "total_processing_records": schema_info["processing_history"][
                    "record_count"
                ],
                "total_feedback_records": schema_info["human_feedback"]["record_count"],
                "filtered_processing_count": len(records),
                "filtered_feedback_count": len(feedback_records),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get episodic memory: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/export", methods=["GET"])
def export_memory_data() -> dict[str, Any]:
    """Export all memory systems data."""
    try:
        export_data = {}

        # Export semantic memory
        if memory_systems and memory_systems.get("semantic"):
            export_data["semantic"] = memory_systems["semantic"].data

        # Export procedural memory
        if memory_systems and memory_systems.get("procedural"):
            export_data["procedural"] = memory_systems["procedural"].data

        # Export episodic memory (recent records only)
        if memory_systems and memory_systems.get("episodic"):
            episodic_memory = memory_systems["episodic"]
            export_data["episodic"] = {
                "processing_records": episodic_memory.get_recent_records(limit=100),
                "feedback_records": episodic_memory.get_feedback_history(limit=50),
                "schema_info": episodic_memory.validate_schema(),
            }

        return {
            "success": True,
            "data": export_data,
            "export_timestamp": datetime.now().isoformat(),
            "version": "1.0",
        }

    except Exception as e:
        logger.error(f"Failed to export memory data: {e}")
        return {"error": str(e)}, 500


@app.route("/api/memory/import", methods=["POST"])
def import_memory_data() -> tuple[dict, int]:
    """Import memory systems data."""
    try:
        data = request.get_json()
        if not data or "data" not in data:
            return {"error": "No data provided"}, 400

        import_data = data["data"]
        results = {"imported": [], "errors": []}

        # Import semantic memory
        if (
            "semantic" in import_data
            and memory_systems
            and memory_systems.get("semantic")
        ):
            try:
                semantic_memory = memory_systems["semantic"]
                semantic_memory.data = import_data["semantic"]
                semantic_memory._save_data()
                results["imported"].append("semantic")
                logger.info("Semantic memory imported successfully")
            except Exception as e:
                results["errors"].append(f"Semantic memory import failed: {e}")

        # Import procedural memory
        if (
            "procedural" in import_data
            and memory_systems
            and memory_systems.get("procedural")
        ):
            try:
                procedural_memory = memory_systems["procedural"]
                procedural_memory.data = import_data["procedural"]
                procedural_memory._save_data()
                results["imported"].append("procedural")
                logger.info("Procedural memory imported successfully")
            except Exception as e:
                results["errors"].append(f"Procedural memory import failed: {e}")

        # Note: We don't import episodic memory as it's historical data
        if "episodic" in import_data:
            results["errors"].append(
                "Episodic memory import not supported (historical data)"
            )

        if results["imported"]:
            return {"success": True, "results": results}, 200
        else:
            return {"success": False, "results": results}, 400

    except Exception as e:
        logger.error(f"Failed to import memory data: {e}")
        return {"error": str(e)}, 500


# ===== END MEMORY MANAGEMENT API ENDPOINTS =====


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
        needs_review_asset = None

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

                    # Special handling for NEEDS_REVIEW
                    if asset_dir.name == "NEEDS_REVIEW":
                        needs_review_asset = {
                            "id": asset_dir.name,
                            "name": "⚠️ Needs Human Review",
                            "file_count": file_count,
                            "path": str(asset_dir),
                            "is_review_folder": True,
                            "priority": True,
                        }
                        continue

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
                            "is_review_folder": False,
                            "priority": False,
                        }
                    )

        # Sort regular assets by name
        assets.sort(key=lambda x: x["name"])

        # Add NEEDS_REVIEW at the beginning if it exists and has files
        final_assets = []
        if needs_review_asset and needs_review_asset["file_count"] > 0:
            final_assets.append(needs_review_asset)
        final_assets.extend(assets)

        return jsonify(
            {
                "assets": final_assets,
                "total_assets": len(final_assets),
                "needs_review_count": (
                    needs_review_asset["file_count"] if needs_review_asset else 0
                ),
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


@app.route("/api/system/reset", methods=["POST"])
def reset_system() -> tuple[dict, int]:
    """Reset system by deleting all files and resetting ALL memory to base state."""
    try:
        deleted_files = 0

        # Delete all files in assets directory
        assets_path = Path(config.assets_base_path)
        if assets_path.exists():
            for item in assets_path.iterdir():
                if item.is_dir():
                    # Delete directory and all contents
                    for file in item.rglob("*"):
                        if file.is_file():
                            file.unlink()
                            deleted_files += 1
                    # Remove empty directories
                    for dir_path in sorted(
                        item.rglob("*"), key=lambda x: len(str(x)), reverse=True
                    ):
                        if dir_path.is_dir():
                            dir_path.rmdir()
                    item.rmdir()
                elif item.is_file():
                    item.unlink()
                    deleted_files += 1

        # Reset ALL memory systems to baseline using centralized function
        try:
            reset_results = reset_all_memory_to_baseline()
            semantic_reset = reset_results.get("semantic_memory", 0)
            procedural_reset = reset_results.get("procedural_memory", 0)
            episodic_reset = reset_results.get("episodic_memory", 0)
            total_reset = reset_results.get("total_items", 0)

            logger.info(f"Memory systems reset to baseline: {total_reset} total items")

        except Exception as e:
            logger.error(f"Failed to reset memory systems to baseline: {e}")
            semantic_reset = 0
            procedural_reset = 0
            episodic_reset = 0
            total_reset = 0

        message = f"Complete reset: {deleted_files} files deleted, memory reset to baseline ({total_reset} items)"
        logger.info(message)

        return {
            "message": message,
            "files_deleted": deleted_files,
            "semantic_items_reset": semantic_reset,
            "procedural_rules_reset": procedural_reset,
            "episodic_records_reset": episodic_reset,
            "total_memory_items_reset": total_reset,
        }, 200

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/system/reset-files-only", methods=["POST"])
def reset_files_only() -> tuple[dict, int]:
    """Reset only saved files, keeping all memory systems intact."""
    try:
        deleted_files = 0

        # Delete all files in assets directory
        assets_path = Path(config.assets_base_path)
        if assets_path.exists():
            for item in assets_path.iterdir():
                if item.is_dir():
                    # Delete directory and all contents
                    for file in item.rglob("*"):
                        if file.is_file():
                            file.unlink()
                            deleted_files += 1
                    # Remove empty directories
                    for dir_path in sorted(
                        item.rglob("*"), key=lambda x: len(str(x)), reverse=True
                    ):
                        if dir_path.is_dir():
                            dir_path.rmdir()
                    item.rmdir()
                elif item.is_file():
                    item.unlink()
                    deleted_files += 1

        message = (
            f"Files cleared: {deleted_files} files deleted (memory systems preserved)"
        )
        logger.info(message)

        return {"message": message, "files_deleted": deleted_files}, 200

    except Exception as e:
        logger.error(f"File reset failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/system/reset-episodic-memory", methods=["POST"])
def reset_episodic_memory() -> tuple[dict, int]:
    """Clear episodic memory (processing history and feedback) only."""
    try:
        cleared_episodes = 0

        if memory_systems and memory_systems.get("episodic"):
            try:
                episodic_memory = memory_systems["episodic"]
                cleared_episodes = episodic_memory.clear_all_data()
            except Exception as e:
                logger.warning(f"Failed to clear episodic memory: {e}")
                return {"error": f"Episodic memory clear failed: {e}"}, 500

        message = f"Episodic memory cleared: {cleared_episodes} records deleted"
        logger.info(message)

        return {"message": message, "records_cleared": cleared_episodes}, 200

    except Exception as e:
        logger.error(f"Episodic memory reset failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/system/reset-semantic-memory", methods=["POST"])
def reset_semantic_memory() -> tuple[dict, int]:
    """Reset semantic memory to base state."""
    try:
        reset_count = 0

        if memory_systems and memory_systems.get("semantic"):
            try:
                semantic_memory = memory_systems["semantic"]
                reset_count = semantic_memory.reset_to_base_state()
            except Exception as e:
                logger.warning(f"Failed to reset semantic memory: {e}")
                return {"error": f"Semantic memory reset failed: {e}"}, 500

        message = f"Semantic memory reset: {reset_count} items reset to base state"
        logger.info(message)

        return {"message": message, "items_reset": reset_count}, 200

    except Exception as e:
        logger.error(f"Semantic memory reset failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/system/reset-procedural-memory", methods=["POST"])
def reset_procedural_memory() -> tuple[dict, int]:
    """Reset procedural memory to base state."""
    try:
        reset_count = 0

        if memory_systems and memory_systems.get("procedural"):
            try:
                procedural_memory = memory_systems["procedural"]
                reset_count = procedural_memory.reset_to_base_state()
            except Exception as e:
                logger.warning(f"Failed to reset procedural memory: {e}")
                return {"error": f"Procedural memory reset failed: {e}"}, 500

        message = f"Procedural memory reset: {reset_count} rules reset to base state"
        logger.info(message)

        return {"message": message, "rules_reset": reset_count}, 200

    except Exception as e:
        logger.error(f"Procedural memory reset failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/attachments/review/<asset_id>/<filename>", methods=["GET"])
def get_attachment_review_details(asset_id: str, filename: str) -> tuple[dict, int]:
    """Get comprehensive decision breakdown for reviewing an attachment classification."""
    try:
        # Find the attachment file
        asset_path = Path(config.assets_base_path) / asset_id
        if not asset_path.exists():
            return {"error": f"Asset {asset_id} not found"}, 404

        file_path = asset_path / filename
        if not file_path.exists():
            return {"error": f"File {filename} not found in asset {asset_id}"}, 404

        # Get processing records for this file from episodic memory
        classification_details = None
        if memory_systems and hasattr(
            memory_systems["episodic"], "find_records_by_filename"
        ):
            # Try to find records by filename first
            records = memory_systems["episodic"].find_records_by_filename(
                filename, limit=5
            )

            # If no specific records found, try recent records
            if not records:
                recent_records = memory_systems["episodic"].get_recent_records(limit=20)
                # Filter for records that might contain this filename
                records = [
                    r for r in recent_records if filename in str(r.get("metadata", {}))
                ]

            logger.info(f"Found {len(records)} episodic records for file: {filename}")

            # Aggregate decision reasoning from all relevant records
            all_decision_reasoning = []
            file_specific_record = None

            # Helper function to create reasoning signature for deduplication
            def get_reasoning_signature(reasoning_entry):
                return f"{reasoning_entry.get('rule_id', '')}_{reasoning_entry.get('rule_type', '')}_{reasoning_entry.get('score', 0)}"

            seen_reasoning = set()

            # Look for detailed reasoning in the records
            for record in records:
                metadata = record.get("metadata", {})

                # Check for asset_matches structure first (more detailed)
                asset_matches = metadata.get("asset_matches", [])
                for match in asset_matches:
                    if match.get("attachment_filename") == filename:
                        file_specific_record = record
                        match_reasoning = match.get("decision_reasoning", [])

                        # Process and deduplicate reasoning entries
                        for reasoning_entry in match_reasoning:
                            # Fix missing fields
                            if "score" not in reasoning_entry:
                                if "highest_confidence" in reasoning_entry:
                                    reasoning_entry["score"] = reasoning_entry[
                                        "highest_confidence"
                                    ]
                                elif "confidence" in reasoning_entry:
                                    reasoning_entry["score"] = reasoning_entry[
                                        "confidence"
                                    ]
                                else:
                                    reasoning_entry["score"] = 0.1

                            if "rule_name" not in reasoning_entry:
                                reasoning_entry["rule_name"] = reasoning_entry.get(
                                    "rule_id", "Unknown Rule"
                                )

                            # Deduplicate based on signature
                            signature = get_reasoning_signature(reasoning_entry)
                            if signature not in seen_reasoning:
                                seen_reasoning.add(signature)
                                all_decision_reasoning.append(reasoning_entry)
                        break

                # If no asset_matches found, check direct decision_reasoning
                if not file_specific_record and ("decision_reasoning" in metadata):
                    decision_reasoning = metadata.get("decision_reasoning", [])

                    # Check if this reasoning is specific to our file or generic
                    file_specific = any(
                        filename in str(reasoning_entry)
                        for reasoning_entry in decision_reasoning
                    )

                    if (
                        file_specific or not all_decision_reasoning
                    ):  # Use if file-specific or no other reasoning found
                        file_specific_record = record

                        # Process and deduplicate reasoning entries
                        for reasoning_entry in decision_reasoning:
                            # Fix missing fields
                            if "score" not in reasoning_entry:
                                if "highest_confidence" in reasoning_entry:
                                    reasoning_entry["score"] = reasoning_entry[
                                        "highest_confidence"
                                    ]
                                elif "confidence" in reasoning_entry:
                                    reasoning_entry["score"] = reasoning_entry[
                                        "confidence"
                                    ]
                                else:
                                    reasoning_entry["score"] = 0.1

                            if "rule_name" not in reasoning_entry:
                                reasoning_entry["rule_name"] = reasoning_entry.get(
                                    "rule_id", "Unknown Rule"
                                )

                            # Deduplicate based on signature
                            signature = get_reasoning_signature(reasoning_entry)
                            if signature not in seen_reasoning:
                                seen_reasoning.add(signature)
                                all_decision_reasoning.append(reasoning_entry)

            # If we found reasoning, create classification details
            if all_decision_reasoning and file_specific_record:
                classification_details = {
                    "classification_result": {
                        "asset_id": file_specific_record.get("asset_id", asset_id),
                        "confidence": file_specific_record.get("confidence", 0.0),
                        "decision": file_specific_record.get("decision", "classified"),
                        "timestamp": file_specific_record.get("timestamp"),
                        "sender": file_specific_record.get("sender"),
                        "subject": file_specific_record.get("subject"),
                    },
                    "decision_reasoning": all_decision_reasoning,
                    "additional_context": {
                        "email_context": {
                            "sender": file_specific_record.get("sender"),
                            "subject": file_specific_record.get("subject"),
                            "timestamp": file_specific_record.get("timestamp"),
                        },
                        "file_info": {
                            "filename": filename,
                            "current_location": str(file_path),
                            "asset_assignment": asset_id,
                        },
                        "records_processed": len(records),
                        "unique_reasoning_rules": len(all_decision_reasoning),
                    },
                }

        # If no detailed reasoning found, or if reasoning lacks asset details, reconstruct analysis
        if not classification_details or (
            classification_details
            and classification_details["decision_reasoning"]
            and all(
                r.get("total_assets_considered", 0) == 0
                for r in classification_details["decision_reasoning"]
            )
        ):
            logger.warning(
                f"Incomplete reasoning found for {filename} - reconstructing asset matching analysis"
            )

            # Get the base classification result if we have it
            base_result = (
                classification_details["classification_result"]
                if classification_details
                else {
                    "asset_id": asset_id,
                    "confidence": 0.1 if asset_id == "HUMAN_REVIEW_QUEUE" else 0.0,
                    "decision": (
                        "needs_review"
                        if asset_id == "HUMAN_REVIEW_QUEUE"
                        else "unknown"
                    ),
                    "reason": "Reconstructed analysis - original reasoning incomplete",
                }
            )

            # Reconstruct what the matching would have looked like
            reconstructed_reasoning = []

            if memory_systems:
                # Get the email context from records if available
                email_context = {
                    "subject": (
                        records[0].get("subject", "") if records else "asset document"
                    ),
                    "sender": records[0].get("sender", "") if records else "unknown",
                    "body": "",  # We don't have the original body
                }

                # Get available assets
                try:
                    asset_profiles = memory_systems["semantic"].search_asset_profiles(
                        ""
                    )
                    logger.info(
                        f"Reconstructing analysis against {len(asset_profiles)} assets"
                    )

                    # Get matching rules (for completeness, though not directly used in reconstruction)
                    memory_systems["procedural"].get_asset_matching_rules()

                    # Simulate what each asset matching would have looked like
                    for asset_profile in asset_profiles:
                        if asset_profile["asset_id"] == "HUMAN_REVIEW_QUEUE":
                            continue  # Skip the fallback asset

                        profile = asset_profile["profile"]
                        asset_name = profile.get("name", asset_profile["asset_id"])
                        keywords = profile.get("keywords", [])

                        # Simulate keyword matching rule
                        combined_text = (
                            f"{filename.lower()} {email_context['subject'].lower()}"
                        )
                        keyword_matches = [
                            kw for kw in keywords if kw.lower() in combined_text
                        ]
                        keyword_score = (
                            len(keyword_matches) / max(len(keywords), 1)
                            if keywords
                            else 0.0
                        )

                        # Simulate filename pattern matching
                        filename_score = 0.0
                        filename_patterns = profile.get("filename_patterns", [])
                        for pattern in filename_patterns:
                            if pattern.lower() in filename.lower():
                                filename_score = 0.8
                                break

                        # Simulate asset name matching
                        asset_name_score = 0.0
                        if asset_name.lower() in combined_text:
                            asset_name_score = 0.9
                        else:
                            # Check for partial word matches
                            asset_words = set(asset_name.lower().split())
                            text_words = set(combined_text.split())
                            common_words = asset_words.intersection(text_words)
                            if len(common_words) >= 2:
                                asset_name_score = (
                                    len(common_words) / len(asset_words)
                                ) * 0.9

                        # Calculate overall score (simplified)
                        overall_score = max(
                            keyword_score * 0.7,
                            filename_score * 0.9,
                            asset_name_score * 0.95,
                        )

                        # Create detailed reasoning for this asset
                        reconstructed_reasoning.append(
                            {
                                "rule_id": f"asset_analysis_{asset_profile['asset_id']}",
                                "rule_name": f"Asset Analysis: {asset_name}",
                                "rule_type": "reconstructed_analysis",
                                "score": overall_score,
                                "result": "evaluated",
                                "reason": f"Reconstructed analysis of matching against {asset_name}",
                                "memory_items": [
                                    {
                                        "type": "semantic_memory",
                                        "source": f"asset_profiles.{asset_profile['asset_id']}",
                                        "description": f"Asset profile for {asset_name}",
                                        "content": {
                                            "keywords": keywords,
                                            "filename_patterns": filename_patterns,
                                            "name": asset_name,
                                        },
                                    }
                                ],
                                "evidence": {
                                    "filename": filename,
                                    "email_subject": email_context["subject"],
                                    "combined_text": (
                                        combined_text[:100] + "..."
                                        if len(combined_text) > 100
                                        else combined_text
                                    ),
                                    "keywords_available": keywords,
                                    "keywords_found": keyword_matches,
                                    "keyword_score": keyword_score,
                                    "filename_patterns": filename_patterns,
                                    "filename_score": filename_score,
                                    "asset_name_score": asset_name_score,
                                    "final_score": overall_score,
                                    "threshold": 0.5,
                                },
                                "contributing_factors": [
                                    (
                                        f"Keyword matching: {len(keyword_matches)}/{len(keywords)} keywords found"
                                        if keywords
                                        else "No keywords defined"
                                    ),
                                    (
                                        f"Keywords found: {keyword_matches}"
                                        if keyword_matches
                                        else "No keywords matched"
                                    ),
                                    (
                                        f"Filename patterns: {len(filename_patterns)} patterns checked"
                                        if filename_patterns
                                        else "No filename patterns defined"
                                    ),
                                    f"Asset name matching: {'Found' if asset_name_score > 0 else 'Not found'} in content",
                                    f"Final score: {overall_score:.3f} (threshold: 0.5)",
                                    f"Result: {'✅ Would match' if overall_score >= 0.5 else '❌ Below threshold'}",
                                ],
                            }
                        )

                    # Add the final fallback reasoning
                    highest_score = max(
                        [r["score"] for r in reconstructed_reasoning], default=0.0
                    )
                    reconstructed_reasoning.append(
                        {
                            "rule_id": "reconstructed_fallback",
                            "rule_name": "Reconstructed Fallback Analysis",
                            "rule_type": "fallback_routing",
                            "score": 0.1,
                            "result": "triggered",
                            "reason": f"No asset achieved confidence ≥ 0.5 - highest was {highest_score:.3f}",
                            "memory_items": [
                                {
                                    "type": "procedural_memory",
                                    "source": "matching_rules.fallback_policy",
                                    "description": "Threshold-based routing to human review",
                                    "content": {
                                        "threshold": 0.5,
                                        "action": "route_to_human_review",
                                    },
                                }
                            ],
                            "evidence": {
                                "threshold": 0.5,
                                "highest_confidence_found": highest_score,
                                "confidence_gap": 0.5 - highest_score,
                                "total_assets_considered": len(reconstructed_reasoning)
                                - 1,
                            },
                            "contributing_factors": [
                                f"Evaluated {len(reconstructed_reasoning)} assets",
                                f"Highest confidence achieved: {highest_score:.3f}",
                                "Required threshold: 0.5",
                                f"Confidence gap: {0.5 - highest_score:.3f}",
                                "Automatic routing to human review queue",
                            ],
                        }
                    )

                except Exception as e:
                    logger.error(f"Error reconstructing analysis: {e}")
                    reconstructed_reasoning = [
                        {
                            "rule_id": "reconstruction_failed",
                            "rule_name": "Analysis Reconstruction Failed",
                            "rule_type": "system_error",
                            "score": 0.0,
                            "result": "error",
                            "reason": f"Could not reconstruct asset matching analysis: {e}",
                            "memory_items": [],
                            "evidence": {"error": str(e)},
                            "contributing_factors": [
                                "System error during analysis reconstruction"
                            ],
                        }
                    ]

            classification_details = {
                "classification_result": base_result,
                "decision_reasoning": reconstructed_reasoning,
                "additional_context": {
                    "email_context": {
                        "sender": email_context["sender"],
                        "subject": email_context["subject"],
                        "timestamp": (
                            records[0].get("timestamp")
                            if records
                            else datetime.now().isoformat()
                        ),
                    },
                    "file_info": {
                        "filename": filename,
                        "current_location": str(file_path),
                        "asset_assignment": asset_id,
                    },
                    "analysis_type": "reconstructed",
                    "note": "Reconstructed analysis showing what rules would have been applied",
                },
            }

        return classification_details, 200

    except Exception as e:
        logger.error(f"Error getting review details for {filename}: {e}")
        return {"error": f"Failed to get review details: {str(e)}"}, 500


@app.route("/api/feedback/submit", methods=["POST"])
def submit_feedback() -> tuple[dict, int]:
    """Submit human feedback for file relevance and asset assignment."""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "filename",
            "file_path",
            "current_asset_id",
            "feedback_type",
            "relevance_feedback",
        ]
        for field in required_fields:
            if field not in data:
                return {"error": f"Missing required field: {field}"}, 400

        # Extract feedback data
        filename = data["filename"]
        current_asset_id = data["current_asset_id"]
        feedback_type = data["feedback_type"]  # 'review' or 'reclassify'
        relevance_feedback = data["relevance_feedback"]  # 'relevant' or 'irrelevant'
        asset_assignment_feedback = data.get("asset_assignment_feedback", "")
        notes = data.get("notes", "")

        # Generate unique email ID for this feedback
        email_id = f"feedback_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Store feedback in episodic memory
        if memory_systems and memory_systems.get("episodic"):
            episodic_memory = memory_systems["episodic"]

            # Determine original and corrected decisions
            original_decision = f"asset:{current_asset_id},relevance:relevant"

            # Build corrected decision
            corrected_relevance = relevance_feedback
            corrected_asset = asset_assignment_feedback or current_asset_id
            if asset_assignment_feedback == "none":
                corrected_asset = "unassigned"

            corrected_decision = (
                f"asset:{corrected_asset},relevance:{corrected_relevance}"
            )

            # Calculate confidence impact (negative for corrections, positive for confirmations)
            confidence_impact = 0.0
            if feedback_type == "reclassify":
                # This is a correction
                confidence_impact = (
                    -0.2 if corrected_decision != original_decision else 0.1
                )
            elif feedback_type == "review":
                # This is human review
                confidence_impact = 0.05  # Small positive for human validation

            # Store the feedback
            episodic_memory.add_human_feedback(
                email_id=email_id,
                original_decision=original_decision,
                corrected_decision=corrected_decision,
                feedback_type=feedback_type,
                confidence_impact=confidence_impact,
                notes=f"File: {filename}\nRelevance: {relevance_feedback}\nAsset: {corrected_asset}\nNotes: {notes}",
            )

            logger.info(f"Human feedback stored: {feedback_type} for {filename}")

        # Note: File movement to correct asset directory could be implemented here
        # if automatic file reorganization is desired based on feedback

        message = f"Feedback recorded for {filename}: {relevance_feedback}, asset: {corrected_asset}"
        return {"message": message, "feedback_type": feedback_type}, 200

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        return {"error": str(e)}, 500


@app.route("/api/system/review-status", methods=["GET"])
def get_review_status() -> dict[str, Any]:
    """Get count of items awaiting human review."""
    try:
        needs_review_path = Path(config.assets_base_path) / "NEEDS_REVIEW"
        review_count = 0

        if needs_review_path.exists() and needs_review_path.is_dir():
            review_count = len([f for f in needs_review_path.iterdir() if f.is_file()])

        return jsonify(
            {
                "needs_review_count": review_count,
                "has_pending_reviews": review_count > 0,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get review status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/validate-schema", methods=["GET"])
def validate_episodic_schema() -> tuple[dict, int]:
    """
    Validate the episodic memory database schema.

    This endpoint helps debug schema issues that can cause the decision
    reasoning functionality to fail in the UI.
    """
    try:
        # # Local application imports
        from src.memory.simple_memory import SimpleEpisodicMemory

        episodic = SimpleEpisodicMemory()
        validation_result = episodic.validate_schema()

        logger.info("Schema validation requested via API")

        return {
            "validation": validation_result,
            "message": "Schema validation complete",
            "timestamp": datetime.now().isoformat(),
        }, 200

    except Exception as e:
        logger.error(f"Schema validation API failed: {e}")
        return {"error": f"Schema validation failed: {e}"}, 500


if __name__ == "__main__":
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # Initialize the system
    if not initialize_system():
        logger.critical("Failed to initialize system. Exiting.")
        sys.exit(1)

    # Run Flask app
    logger.info("Starting Inveniam E-mail Agent web interface...")
    logger.info(f"Visit: http://localhost:{config.flask_port}")

    app.run(host=config.flask_host, port=config.flask_port, debug=config.debug)

"""
Attachment Processor Node - Saves and organizes attachments using memory-driven rules.

This node queries procedural memory for HOW to handle files (naming, folder structure,
security) and performs the actual file system operations.
"""

# # Standard library imports
from datetime import datetime
from pathlib import Path
from typing import Any

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AttachmentProcessorNode:
    """
    Processes and saves attachments using memory-driven file handling rules.

    Queries procedural memory for HOW to process, then performs file operations.
    """

    def __init__(self, procedural_memory=None) -> None:
        """
        Initialize attachment processor with memory system connection.

        Args:
            procedural_memory: Procedural memory for file handling rules
        """
        self.procedural_memory = procedural_memory
        self.base_path = Path(config.assets_base_path)
        self.max_file_size = (
            config.max_attachment_size_mb * 1024 * 1024
        )  # Convert to bytes

        logger.info(f"Attachment processor initialized (base path: {self.base_path})")

    @log_function()
    async def process_attachments(
        self,
        asset_matches: list[dict[str, Any]],
        email_data: dict[str, Any],
        attachments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Process and save attachments based on asset matches.

        Args:
            asset_matches: List of attachment-to-asset matches
            email_data: Email metadata for context
            attachments: Raw attachment data

        Returns:
            List of processing results with file paths and status

        Raises:
            ValueError: If input data is malformed
        """
        if not asset_matches:
            logger.info("No asset matches to process")
            return []

        logger.info(f"Processing {len(asset_matches)} asset matches")

        # Get file handling procedures from procedural memory
        processing_rules = await self.query_processing_procedures(email_data)

        results = []
        for match in asset_matches:
            try:
                result = await self._process_single_attachment(
                    match, email_data, attachments, processing_rules
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to process attachment {match.get('attachment_filename')}: {e}"
                )
                results.append(
                    {
                        "attachment_filename": match.get("attachment_filename"),
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        logger.info(f"Completed processing: {len(results)} results")
        return results

    async def _process_single_attachment(
        self,
        match: dict[str, Any],
        email_data: dict[str, Any],
        attachments: list[dict[str, Any]],
        processing_rules: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process a single attachment match.

        Args:
            match: Asset match information
            email_data: Email context
            attachments: All attachment data
            processing_rules: Rules from procedural memory

        Returns:
            Processing result dictionary
        """
        filename = match["attachment_filename"]
        asset_id = match["asset_id"]

        # Find the actual attachment data
        attachment_data = next(
            (att for att in attachments if att.get("filename") == filename), None
        )

        if not attachment_data:
            raise ValueError(f"Attachment data not found for {filename}")

        # Determine document category using processing rules
        document_category = await self._categorize_document(
            filename, email_data, processing_rules
        )

        # Generate target path using procedural memory rules
        target_path = await self._generate_target_path(
            asset_id, document_category, filename, processing_rules
        )

        # Apply security checks using procedural memory rules
        security_check = await self._apply_security_checks(
            attachment_data, processing_rules
        )

        if not security_check["allowed"]:
            return {
                "attachment_filename": filename,
                "asset_id": asset_id,
                "status": "blocked",
                "reason": security_check["reason"],
                "timestamp": datetime.now().isoformat(),
            }

        # Generate final filename using procedural memory rules
        final_filename = await self._generate_filename(
            filename, asset_id, document_category, email_data, processing_rules
        )

        final_path = target_path / final_filename

        # Simulate file saving (in real implementation, would save actual file)
        await self._save_attachment(attachment_data, final_path)

        return {
            "attachment_filename": filename,
            "asset_id": asset_id,
            "document_category": document_category,
            "saved_path": str(final_path),
            "status": "saved",
            "timestamp": datetime.now().isoformat(),
            "file_size": attachment_data.get("size", 0),
            "confidence": match.get("confidence", 0.0),
        }

    async def _categorize_document(
        self,
        filename: str,
        email_data: dict[str, Any],
        processing_rules: dict[str, Any],
    ) -> str:
        """
        Categorize document type using procedural memory rules.

        This would query procedural memory for categorization algorithms.
        """
        filename_lower = filename.lower()

        # Simple categorization until procedural memory is connected
        if "financial" in filename_lower or "statement" in filename_lower:
            return "financial_statements"
        elif "compliance" in filename_lower or "audit" in filename_lower:
            return "compliance_documents"
        elif "performance" in filename_lower or "report" in filename_lower:
            return "performance_reports"
        else:
            return "general_documents"

    async def _generate_target_path(
        self,
        asset_id: str,
        document_category: str,
        filename: str,
        processing_rules: dict[str, Any],
    ) -> Path:
        """
        Generate target directory path using procedural memory rules.

        This would query procedural memory for folder structure rules.
        """
        # Create directory structure: base_path/asset_id/document_category/
        target_dir = self.base_path / asset_id / document_category

        # Ensure directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        return target_dir

    async def _apply_security_checks(
        self, attachment_data: dict[str, Any], processing_rules: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply security checks using procedural memory rules.

        This would query procedural memory for security procedures.
        """
        filename = attachment_data.get("filename", "")
        file_size = attachment_data.get("size", 0)

        # File size check
        if file_size > self.max_file_size:
            return {
                "allowed": False,
                "reason": f"File too large: {file_size} bytes (max: {self.max_file_size})",
            }

        # File extension check
        allowed_extensions = config.allowed_file_extensions
        file_ext = Path(filename).suffix.lower().lstrip(".")

        if file_ext not in allowed_extensions:
            return {
                "allowed": False,
                "reason": f"File extension not allowed: {file_ext}",
            }

        return {"allowed": True, "reason": "Security checks passed"}

    async def _generate_filename(
        self,
        original_filename: str,
        asset_id: str,
        document_category: str,
        email_data: dict[str, Any],
        processing_rules: dict[str, Any],
    ) -> str:
        """
        Generate standardized filename using procedural memory rules.

        This would query procedural memory for naming conventions.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sender = email_data.get("sender", "unknown").split("@")[0]

        # Extract file extension
        file_ext = Path(original_filename).suffix

        # Generate standardized name: YYYYMMDD_HHMMSS_AssetID_Category_Sender_Original
        base_name = Path(original_filename).stem
        standardized_name = (
            f"{timestamp}_{asset_id}_{document_category}_{sender}_{base_name}{file_ext}"
        )

        # Clean filename (remove invalid characters)
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "\\", "/"]
        for char in invalid_chars:
            standardized_name = standardized_name.replace(char, "_")

        return standardized_name

    async def _save_attachment(
        self, attachment_data: dict[str, Any], target_path: Path
    ) -> None:
        """
        Save attachment to file system.

        In real implementation, this would handle actual file I/O.
        """
        # For now, just simulate saving by creating an empty file
        target_path.touch()
        logger.info(f"Simulated saving attachment to: {target_path}")

        # In real implementation:
        # - Decode attachment content
        # - Write to target_path
        # - Set appropriate file permissions
        # - Calculate and store file hash for integrity

    async def query_processing_procedures(
        self, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Query procedural memory for file processing rules and procedures.

        TODO: Implement when procedural memory is available.

        Args:
            context: Email and processing context

        Returns:
            Dictionary of processing procedures and rules
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return self._get_default_processing_rules()

        # This will query procedural memory for:
        # - File naming conventions
        # - Directory structure rules
        # - Security scanning procedures
        # - Document categorization algorithms
        # - Duplicate handling rules
        # - Backup and archival procedures

        return {}

    def _get_default_processing_rules(self) -> dict[str, Any]:
        """Default processing rules until procedural memory is available."""
        return {
            "naming_convention": "timestamp_asset_category_sender_original",
            "directory_structure": "asset_id/document_category/",
            "duplicate_handling": "rename_with_suffix",
            "security_scan_required": config.enable_virus_scanning,
            "backup_enabled": False,
            "categorization_method": "filename_pattern_matching",
        }

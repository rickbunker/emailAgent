"""
Attachment Processor Node - Saves and organizes attachments using memory-driven rules.

This node queries procedural memory for HOW to handle files (naming, folder structure,
security) and semantic memory for document categorization patterns.
"""

# # Standard library imports
# Standard library imports
from datetime import datetime
from pathlib import Path
from typing import Any

# # Local application imports
# Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AttachmentProcessorNode:
    """
    Processes and saves attachments using memory-driven file handling rules.

    Queries procedural memory for HOW to process and semantic memory for categorization.
    """

    def __init__(self, memory_systems=None) -> None:
        """
        Initialize attachment processor with memory system connections.

        Args:
            memory_systems: Dictionary with all memory systems (semantic, procedural)
        """
        if memory_systems:
            self.procedural_memory = memory_systems.get("procedural")
            self.semantic_memory = memory_systems.get("semantic")
        else:
            # Initialize memory systems directly if not provided
            # # Local application imports
            from src.memory import create_memory_systems

            systems = create_memory_systems()
            self.procedural_memory = systems["procedural"]
            self.semantic_memory = systems["semantic"]

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

        # Return in expected format with additional metadata
        return {
            "results": results,
            "decision_factors": [f"Processed {len(asset_matches)} asset matches"],
            "memory_queries": ["Queried procedural memory for processing rules"],
            "rule_applications": [f"Applied security checks to {len(results)} files"],
            "confidence_factors": [
                f"Successfully processed {len([r for r in results if r.get('status') == 'saved'])} files"
            ],
        }

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

        # Generate target path for asset (no categorization)
        target_path = await self._generate_target_path(
            asset_id, filename, processing_rules
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
            filename, asset_id, email_data, processing_rules
        )

        final_path = target_path / final_filename

        # Simulate file saving (in real implementation, would save actual file)
        await self._save_attachment(attachment_data, final_path)

        return {
            "attachment_filename": filename,
            "asset_id": asset_id,
            "saved_path": str(final_path),
            "status": "saved",
            "timestamp": datetime.now().isoformat(),
            "file_size": attachment_data.get("size", 0),
            "confidence": match.get("confidence", 0.0),
        }

    async def _generate_target_path(
        self,
        asset_id: str,
        filename: str,
        processing_rules: dict[str, Any],
    ) -> Path:
        """
        Generate target directory path for asset.

        Simple structure: base_path/asset_id/
        """
        # Create directory structure: base_path/asset_id/
        target_dir = self.base_path / asset_id

        # Ensure directory exists
        target_dir.mkdir(parents=True, exist_ok=True)

        return target_dir

    async def _apply_security_checks(
        self, attachment_data: dict[str, Any], processing_rules: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply security checks using memory-driven rules.

        Args:
            attachment_data: Attachment metadata including filename and size
            processing_rules: Security rules from procedural memory

        Returns:
            Dictionary with 'allowed' boolean and 'reason' string
        """
        filename = attachment_data.get("filename", "")
        file_size = attachment_data.get("size", 0)
        file_ext = Path(filename).suffix.lower().lstrip(".")

        # Get file type rules from semantic memory
        file_type_rules = None
        if self.semantic_memory:
            try:
                file_type_rules = self.semantic_memory.get_file_type_rules(file_ext)
            except Exception as e:
                logger.warning(
                    f"Failed to get file type rules from semantic memory: {e}"
                )

        # Use memory-driven size limits if available
        max_size_bytes = self.max_file_size  # Default from config
        if file_type_rules and "max_size_mb" in file_type_rules:
            max_size_bytes = file_type_rules["max_size_mb"] * 1024 * 1024

        # File size check with memory-driven limits
        if file_size > max_size_bytes:
            return {
                "allowed": False,
                "reason": f"File too large: {file_size} bytes (max: {max_size_bytes} bytes for {file_ext})",
            }

        # File extension check with memory-driven rules
        if file_type_rules:
            # Use semantic memory rules
            if not file_type_rules.get("allowed", False):
                return {
                    "allowed": False,
                    "reason": f"File type not allowed by memory rules: {file_ext}",
                }
        else:
            # Fallback to config
            allowed_extensions = config.allowed_file_extensions
            if file_ext not in allowed_extensions:
                return {
                    "allowed": False,
                    "reason": f"File extension not allowed: {file_ext}",
                }

        # Get file processing rules from procedural memory
        if self.procedural_memory:
            try:
                file_proc_rules = self.procedural_memory.get_file_processing_rules(
                    file_ext
                )
                if file_proc_rules:
                    # Apply any additional procedural security checks
                    for rule in file_proc_rules:
                        rule_max_size = rule.get("max_size_mb", 100) * 1024 * 1024
                        if file_size > rule_max_size:
                            return {
                                "allowed": False,
                                "reason": f"File exceeds procedural rule limit: {rule_max_size} bytes",
                            }
            except Exception as e:
                logger.warning(f"Failed to apply procedural security checks: {e}")

        return {"allowed": True, "reason": "Security checks passed"}

    async def _generate_filename(
        self,
        original_filename: str,
        asset_id: str,
        email_data: dict[str, Any],
        processing_rules: dict[str, Any],
    ) -> str:
        """
        Generate standardized filename.

        Simple format: YYYYMMDD_HHMMSS_AssetID_Sender_Original
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sender = email_data.get("sender", "unknown").split("@")[0]

        # Extract file extension
        file_ext = Path(original_filename).suffix

        # Generate standardized name: YYYYMMDD_HHMMSS_AssetID_Sender_Original
        base_name = Path(original_filename).stem
        standardized_name = f"{timestamp}_{asset_id}_{sender}_{base_name}{file_ext}"

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

        Args:
            context: Email and processing context

        Returns:
            Dictionary of processing procedures and rules
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return self._get_default_processing_rules()

        try:
            # Get all file processing rules from procedural memory
            all_rules = self.procedural_memory.get_file_processing_rules()

            # Organize rules by type for easy access
            organized_rules = {
                "file_type_rules": {},
                "naming_convention": "timestamp_asset_sender_original",
                "directory_structure": "asset_id/",
                "duplicate_handling": "rename_with_suffix",
                "security_scan_required": config.enable_virus_scanning,
                "backup_enabled": False,
            }

            # Process file processing rules
            for rule in all_rules:
                rule_id = rule.get("rule_id", "unknown")
                file_types = rule.get("file_types", [])

                for file_type in file_types:
                    if file_type not in organized_rules["file_type_rules"]:
                        organized_rules["file_type_rules"][file_type] = []

                    organized_rules["file_type_rules"][file_type].append(
                        {
                            "rule_id": rule_id,
                            "description": rule.get("description", ""),
                            "max_size_mb": rule.get("max_size_mb", 50),
                            "extract_text": rule.get("extract_text", False),
                        }
                    )

            logger.info(
                f"Retrieved {len(all_rules)} file processing rules from procedural memory"
            )
            return organized_rules

        except Exception as e:
            logger.error(f"Failed to query procedural memory: {e}")
            return self._get_default_processing_rules()

    def _get_default_processing_rules(self) -> dict[str, Any]:
        """Default processing rules."""
        return {
            "naming_convention": "timestamp_asset_sender_original",
            "directory_structure": "asset_id/",
            "duplicate_handling": "rename_with_suffix",
            "security_scan_required": config.enable_virus_scanning,
            "backup_enabled": False,
        }

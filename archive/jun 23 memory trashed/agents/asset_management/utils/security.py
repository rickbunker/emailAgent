"""
Security service for asset management.

This module provides security validation including:
- File type validation
- File size validation
- File hash calculation
- Antivirus scanning

It uses semantic memory for file type rules instead of hardcoding them.
"""

# # Standard library imports
import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Optional

# # Local application imports
from src.memory.semantic import SemanticMemory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class SecurityService:
    """
    Security validation service.

    Handles all security-related validations for documents including
    file type checks, size limits, and antivirus scanning.

    Uses semantic memory for file type rules (FACTS) rather than
    hardcoding them in the service.
    """

    def __init__(self, semantic_memory: Optional[SemanticMemory] = None):
        """
        Initialize the security service.

        Args:
            semantic_memory: Semantic memory for file type validation rules
        """
        self.semantic_memory = semantic_memory or self._create_semantic_memory()
        self.max_file_size = getattr(
            config, "max_file_size", 100 * 1024 * 1024
        )  # 100MB default
        self.enable_av_scan = getattr(
            config, "enable_av_scan", False
        )  # Disabled by default

        # Cache for file type validation
        self._file_type_cache: dict[str, dict[str, Any]] = {}

        logger.info(
            f"Security service initialized "
            f"(max_size: {self.max_file_size/1024/1024:.1f}MB, "
            f"av_scan: {self.enable_av_scan})"
        )

    def _create_semantic_memory(self) -> SemanticMemory:
        """Create semantic memory instance."""
        return SemanticMemory(
            max_items=getattr(config, "semantic_memory_max_items", 50000),
            qdrant_url=getattr(config, "qdrant_url", "http://localhost:6333"),
            embedding_model=getattr(config, "embedding_model", "all-MiniLM-L6-v2"),
        )

    @log_function()
    async def validate_file_type(self, filename: str) -> bool:
        """
        Validate if a file type is allowed.

        Uses semantic memory to check file type rules rather than
        hardcoding allowed extensions.

        Args:
            filename: Name of the file to validate

        Returns:
            True if file type is allowed, False otherwise
        """
        if not filename:
            logger.warning("Empty filename provided for validation")
            return False

        # Extract file extension
        extension = Path(filename).suffix.lower()
        if not extension:
            logger.warning(f"No file extension found for: {filename}")
            return False

        # Remove the dot from extension
        extension = extension[1:]

        # Check cache first
        if extension in self._file_type_cache:
            validation_info = self._file_type_cache[extension]
            is_allowed = validation_info.get("is_allowed", False)
            logger.info(
                f"File type validation (cached): {extension} -> "
                f"{'allowed' if is_allowed else 'blocked'}"
            )
            return is_allowed

        try:
            # Get validation from semantic memory
            validation_info = await self.semantic_memory.get_file_type_validation(
                extension
            )

            # Cache the result
            self._file_type_cache[extension] = validation_info

            is_allowed = validation_info.get("is_allowed", False)
            security_level = validation_info.get("security_level", "unknown")

            logger.info(
                f"File type validation: {extension} -> "
                f"{'allowed' if is_allowed else 'blocked'} "
                f"(security: {security_level})"
            )

            # Learn from this validation
            if self.semantic_memory:
                await self.semantic_memory.learn_file_type_success(
                    file_extension=extension, success=is_allowed
                )

            return is_allowed

        except Exception as e:
            logger.error(f"Error validating file type {extension}: {e}")
            # Default to blocking unknown file types for security
            return False

    @log_function()
    async def validate_file_size(self, content: bytes) -> bool:
        """
        Validate if file size is within limits.

        Args:
            content: File content as bytes

        Returns:
            True if size is acceptable, False otherwise
        """
        if not content:
            logger.warning("Empty content provided for size validation")
            return False

        file_size = len(content)

        if file_size > self.max_file_size:
            logger.warning(
                f"File too large: {file_size/1024/1024:.1f}MB "
                f"(max: {self.max_file_size/1024/1024:.1f}MB)"
            )
            return False

        logger.debug(f"File size OK: {file_size/1024:.1f}KB")
        return True

    @log_function()
    async def calculate_file_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            content: File content as bytes

        Returns:
            Hex string of the file hash
        """
        if not content:
            logger.warning("Empty content provided for hash calculation")
            return ""

        hash_obj = hashlib.sha256(content)
        file_hash = hash_obj.hexdigest()

        logger.debug(f"Calculated file hash: {file_hash[:16]}...")
        return file_hash

    @log_function()
    async def scan_file_antivirus(
        self, content: bytes, filename: str
    ) -> dict[str, Any]:
        """
        Scan file with antivirus if enabled.

        Args:
            content: File content to scan
            filename: Name of the file

        Returns:
            Dictionary with scan results:
            {
                'clean': bool,
                'scanned': bool,
                'reason': str (if not clean),
                'scanner': str
            }
        """
        if not self.enable_av_scan:
            logger.debug("AV scanning disabled, skipping")
            return {"clean": True, "scanned": False, "scanner": "none"}

        try:
            # Find ClamAV scanner
            clamscan_path = self._find_clamscan()
            if not clamscan_path:
                logger.warning("ClamAV not found, skipping AV scan")
                return {
                    "clean": True,
                    "scanned": False,
                    "scanner": "none",
                    "reason": "ClamAV not available",
                }

            # Write content to temporary file
            # # Standard library imports
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            try:
                # Run ClamAV scan
                result = subprocess.run(
                    [clamscan_path, "--no-summary", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Check result
                if result.returncode == 0:
                    logger.info(f"AV scan passed for: {filename}")
                    return {"clean": True, "scanned": True, "scanner": "clamav"}
                else:
                    logger.warning(f"AV scan failed for {filename}: {result.stdout}")
                    return {
                        "clean": False,
                        "scanned": True,
                        "scanner": "clamav",
                        "reason": result.stdout.strip(),
                    }

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except subprocess.TimeoutExpired:
            logger.error(f"AV scan timeout for: {filename}")
            return {
                "clean": False,
                "scanned": True,
                "scanner": "clamav",
                "reason": "Scan timeout",
            }
        except Exception as e:
            logger.error(f"AV scan error: {e}")
            return {
                "clean": True,
                "scanned": False,
                "scanner": "none",
                "reason": f"Scan error: {str(e)}",
            }

    def _find_clamscan(self) -> Optional[str]:
        """Find ClamAV scanner executable."""
        possible_paths = [
            "/usr/bin/clamscan",
            "/usr/local/bin/clamscan",
            "/opt/homebrew/bin/clamscan",  # macOS with Homebrew
            "clamscan",  # In PATH
        ]

        for path in possible_paths:
            try:
                # Check if exists and is executable
                result = subprocess.run(
                    [path, "--version"], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    logger.debug(f"Found ClamAV at: {path}")
                    return path
            except:
                continue

        return None

    def clear_cache(self) -> None:
        """Clear the file type validation cache."""
        self._file_type_cache.clear()
        logger.info("Security service cache cleared")

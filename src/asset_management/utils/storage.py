"""
Storage service for asset management.

This module handles file storage operations including:
- Saving files to asset folders
- Duplicate detection
- File organization by asset and category

The service maintains a proper folder structure and tracks
files to prevent duplicates.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class StorageService:
    """
    File storage service.

    Handles saving files to appropriate folders and tracking
    for duplicate detection. Maintains a structured folder
    hierarchy based on assets and document categories.
    """

    DOCUMENT_TRACKING_COLLECTION = "processed_documents"

    def __init__(
        self,
        base_path: Optional[str] = None,
        qdrant_client: Optional[QdrantClient] = None,
    ):
        """
        Initialize the storage service.

        Args:
            base_path: Base directory for file storage.
                      Defaults to config.asset_storage_path
            qdrant_client: Qdrant client for duplicate tracking
        """
        self.base_path = Path(
            base_path or getattr(config, "asset_storage_path", "data")
        )
        self.qdrant = qdrant_client or self._create_qdrant_client()

        # Ensure base directories exist
        self.asset_folder = self.base_path / "assets"
        self.unmatched_folder = self.base_path / "unmatched"
        self.quarantine_folder = self.base_path / "quarantine"

        for folder in [
            self.asset_folder,
            self.unmatched_folder,
            self.quarantine_folder,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"Storage service initialized with base path: {self.base_path}")

    def _create_qdrant_client(self) -> Optional[QdrantClient]:
        """Create Qdrant client for duplicate tracking."""
        try:
            return QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        except Exception as e:
            logger.warning(f"Could not create Qdrant client: {e}")
            return None

    @log_function()
    async def check_duplicate(self, file_hash: str) -> bool:
        """
        Check if a file with this hash already exists.

        Args:
            file_hash: SHA-256 hash of the file

        Returns:
            True if duplicate exists, False otherwise
        """
        if not self.qdrant:
            logger.warning("No Qdrant client available for duplicate check")
            return False

        try:
            # Search for existing document with this hash
            search_result = self.qdrant.scroll(
                collection_name=self.DOCUMENT_TRACKING_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_hash",
                            match=MatchValue(value=file_hash),
                        )
                    ]
                ),
                limit=1,
            )

            if search_result[0]:
                logger.info(f"Duplicate found for hash: {file_hash[:16]}...")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            # Assume not duplicate on error to allow processing
            return False

    @log_function()
    async def save_to_asset_folder(
        self,
        content: bytes,
        filename: str,
        asset_id: str,
        category: str,
        file_hash: str,
    ) -> dict[str, Any]:
        """
        Save file to asset-specific folder.

        Creates folder structure: assets/{asset_id}/{category}/{timestamp}_{filename}

        Args:
            content: File content
            filename: Original filename
            asset_id: Asset identifier
            category: Document category
            file_hash: File hash for tracking

        Returns:
            Dictionary with storage details including file_path
        """
        # Create asset/category folder structure
        asset_folder = self.asset_folder / asset_id / category
        asset_folder.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{filename}"
        file_path = asset_folder / stored_filename

        # Save the file
        try:
            file_path.write_bytes(content)
            logger.info(
                f"Saved file to asset folder: {asset_id}/{category}/{stored_filename}"
            )

            # Track in Qdrant if available
            if self.qdrant:
                await self._track_document(
                    file_hash=file_hash,
                    file_path=str(file_path),
                    asset_id=asset_id,
                    category=category,
                    original_filename=filename,
                )

            return {
                "file_path": file_path,
                "asset_id": asset_id,
                "category": category,
                "stored_filename": stored_filename,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return {"file_path": None, "error": str(e), "success": False}

    @log_function()
    async def save_to_unmatched_folder(
        self, content: bytes, filename: str, file_hash: str
    ) -> dict[str, Any]:
        """
        Save file to unmatched folder when no asset is identified.

        Args:
            content: File content
            filename: Original filename
            file_hash: File hash for tracking

        Returns:
            Dictionary with storage details
        """
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{filename}"
        file_path = self.unmatched_folder / stored_filename

        try:
            file_path.write_bytes(content)
            logger.info(f"Saved unmatched file: {stored_filename}")

            # Track in Qdrant if available
            if self.qdrant:
                await self._track_document(
                    file_hash=file_hash,
                    file_path=str(file_path),
                    asset_id="unmatched",
                    category="unmatched",
                    original_filename=filename,
                )

            return {
                "file_path": file_path,
                "location": "unmatched",
                "stored_filename": stored_filename,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to save unmatched file: {e}")
            return {"file_path": None, "error": str(e), "success": False}

    @log_function()
    async def save_to_quarantine(
        self, content: bytes, filename: str, reason: str
    ) -> dict[str, Any]:
        """
        Save file to quarantine folder.

        Used for files that fail security validation.

        Args:
            content: File content
            filename: Original filename
            reason: Reason for quarantine

        Returns:
            Dictionary with quarantine details
        """
        # Create reason-specific subfolder
        safe_reason = "".join(c for c in reason if c.isalnum() or c in "_ -")[:50]
        quarantine_subfolder = self.quarantine_folder / safe_reason
        quarantine_subfolder.mkdir(parents=True, exist_ok=True)

        # Add timestamp to filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"{timestamp}_{filename}"
        file_path = quarantine_subfolder / stored_filename

        try:
            file_path.write_bytes(content)

            # Also save quarantine info
            info_path = file_path.with_suffix(file_path.suffix + ".info")
            info_content = f"""Quarantined: {datetime.now().isoformat()}
Original filename: {filename}
Reason: {reason}
Size: {len(content)} bytes
"""
            info_path.write_text(info_content)

            logger.warning(f"File quarantined: {stored_filename} (reason: {reason})")

            return {
                "file_path": file_path,
                "location": "quarantine",
                "reason": reason,
                "stored_filename": stored_filename,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to quarantine file: {e}")
            return {"file_path": None, "error": str(e), "success": False}

    async def _track_document(
        self,
        file_hash: str,
        file_path: str,
        asset_id: str,
        category: str,
        original_filename: str,
    ) -> None:
        """
        Track processed document in Qdrant.

        Args:
            file_hash: Document hash
            file_path: Storage path
            asset_id: Associated asset ID
            category: Document category
            original_filename: Original filename
        """
        if not self.qdrant:
            return

        try:
            from qdrant_client.models import PointStruct
            import uuid

            # Create point for tracking
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=[0.0] * 384,  # Placeholder vector
                payload={
                    "file_hash": file_hash,
                    "file_path": file_path,
                    "asset_id": asset_id,
                    "category": category,
                    "original_filename": original_filename,
                    "processed_date": datetime.now().isoformat(),
                },
            )

            self.qdrant.upsert(
                collection_name=self.DOCUMENT_TRACKING_COLLECTION, points=[point]
            )

            logger.debug(f"Tracked document: {file_hash[:16]}...")

        except Exception as e:
            logger.error(f"Failed to track document: {e}")

    async def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "base_path": str(self.base_path),
            "asset_count": 0,
            "unmatched_count": 0,
            "quarantine_count": 0,
            "total_size_mb": 0.0,
        }

        try:
            # Count assets
            if self.asset_folder.exists():
                stats["asset_count"] = len(list(self.asset_folder.iterdir()))

            # Count unmatched files
            if self.unmatched_folder.exists():
                stats["unmatched_count"] = len(list(self.unmatched_folder.glob("*")))

            # Count quarantined files
            if self.quarantine_folder.exists():
                stats["quarantine_count"] = len(
                    list(self.quarantine_folder.glob("**/*"))
                )

            # Calculate total size
            total_size = 0
            for folder in [
                self.asset_folder,
                self.unmatched_folder,
                self.quarantine_folder,
            ]:
                if folder.exists():
                    for file in folder.glob("**/*"):
                        if file.is_file():
                            total_size += file.stat().st_size

            stats["total_size_mb"] = total_size / (1024 * 1024)

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")

        return stats

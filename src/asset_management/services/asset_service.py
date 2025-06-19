"""
Asset management service for CRUD operations.

This module provides a clean service layer for managing assets,
replacing the asset management functionality from the old monolithic
AssetDocumentAgent.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from src.asset_management.core.data_models import Asset, AssetType
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AssetService:
    """
    Service for managing asset CRUD operations.

    This service handles:
    - Creating, reading, updating, and deleting assets
    - Asset storage in Qdrant vector database
    - Asset folder management on filesystem
    """

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        base_assets_path: Optional[Path] = None,
    ):
        """
        Initialize the asset service.

        Args:
            qdrant_client: Optional Qdrant client for vector storage
            base_assets_path: Base path for asset folders
        """
        self.qdrant = qdrant_client
        self.base_assets_path = Path(base_assets_path or config.assets_base_path)
        self.collection_name = "assets"

        # Create base assets directory if it doesn't exist
        self.base_assets_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Asset service initialized with base path: {self.base_assets_path}"
        )

    @log_function()
    async def initialize_collection(self) -> None:
        """Initialize the Qdrant collection for assets."""
        if not self.qdrant:
            logger.warning("No Qdrant client - skipping collection initialization")
            return

        try:
            from qdrant_client.models import Distance, VectorParams

            # Check if collection exists
            collections = self.qdrant.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                # Create collection
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.debug(f"Collection already exists: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    @log_function()
    async def create_asset(
        self,
        deal_name: str,
        asset_name: str,
        asset_type: AssetType,
        identifiers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new asset.

        Args:
            deal_name: Short name for the asset
            asset_name: Full descriptive name
            asset_type: Type of private market asset
            identifiers: Alternative names/identifiers
            metadata: Additional metadata

        Returns:
            Asset deal_id (UUID)

        Raises:
            RuntimeError: If asset creation fails
        """
        deal_id = str(uuid.uuid4())

        try:
            # Create asset object
            asset = Asset(
                deal_id=deal_id,
                deal_name=deal_name,
                asset_name=asset_name,
                asset_type=asset_type,
                folder_path=f"{deal_id}_{deal_name.replace(' ', '_')}",
                identifiers=identifiers or [],
                created_date=datetime.now(UTC),
                last_updated=datetime.now(UTC),
                metadata=metadata,
            )

            # Store in Qdrant if available
            if self.qdrant:
                asset_data = {
                    "deal_id": asset.deal_id,
                    "deal_name": asset.deal_name,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type.value,
                    "identifiers": asset.identifiers,
                    "created_date": asset.created_date.isoformat(),
                    "last_updated": asset.last_updated.isoformat(),
                    "folder_path": asset.folder_path,
                    "metadata": asset.metadata or {},
                }

                # Create point with placeholder vector
                point = PointStruct(
                    id=deal_id,
                    vector=[0.0] * 384,  # Placeholder vector
                    payload=asset_data,
                )

                self.qdrant.upsert(collection_name=self.collection_name, points=[point])
                logger.info(f"Stored asset in Qdrant: {deal_name} ({deal_id})")

            # Create asset folder
            asset_folder = self.base_assets_path / asset.folder_path
            asset_folder.mkdir(parents=True, exist_ok=True)

            # Create standard subfolders
            for subfolder in ["correspondence", "legal_documents", "needs_review"]:
                (asset_folder / subfolder).mkdir(exist_ok=True)

            logger.info(f"✅ Created asset: {deal_name} ({deal_id}) at {asset_folder}")
            return deal_id

        except Exception as e:
            logger.error(f"Failed to create asset {deal_name}: {e}")
            raise RuntimeError(f"Asset creation failed: {e}") from e

    @log_function()
    async def get_asset(self, deal_id: str) -> Optional[Asset]:
        """
        Get asset by deal_id.

        Args:
            deal_id: Asset identifier

        Returns:
            Asset object if found, None otherwise
        """
        if not self.qdrant:
            logger.debug("No Qdrant client - cannot retrieve asset")
            return None

        try:
            # Retrieve from Qdrant
            points = self.qdrant.retrieve(
                collection_name=self.collection_name, ids=[deal_id]
            )

            if not points:
                logger.debug(f"Asset not found: {deal_id}")
                return None

            payload = points[0].payload
            if payload is None:
                logger.debug(f"Asset payload is None: {deal_id}")
                return None

            # Reconstruct Asset object
            asset = Asset(
                deal_id=payload["deal_id"],
                deal_name=payload["deal_name"],
                asset_name=payload["asset_name"],
                asset_type=AssetType(payload["asset_type"]),
                folder_path=payload["folder_path"],
                identifiers=payload.get("identifiers", []),
                created_date=datetime.fromisoformat(payload["created_date"]),
                last_updated=datetime.fromisoformat(payload["last_updated"]),
                metadata=payload.get("metadata"),
            )

            logger.debug(f"Retrieved asset: {asset.deal_name}")
            return asset

        except Exception as e:
            logger.error(f"Failed to retrieve asset {deal_id}: {e}")
            return None

    @log_function()
    async def list_assets(self) -> List[Asset]:
        """
        List all assets.

        Returns:
            List of Asset objects
        """
        if not self.qdrant:
            logger.debug("No Qdrant client - returning empty asset list")
            return []

        try:
            # Get all assets from collection
            scroll_result = self.qdrant.scroll(
                collection_name=self.collection_name, limit=1000  # Adjust as needed
            )

            assets = []
            for point in scroll_result[0]:
                payload = point.payload
                if payload is None:
                    continue

                try:
                    asset = Asset(
                        deal_id=payload["deal_id"],
                        deal_name=payload["deal_name"],
                        asset_name=payload["asset_name"],
                        asset_type=AssetType(payload["asset_type"]),
                        folder_path=payload["folder_path"],
                        identifiers=payload.get("identifiers", []),
                        created_date=datetime.fromisoformat(payload["created_date"]),
                        last_updated=datetime.fromisoformat(payload["last_updated"]),
                        metadata=payload.get("metadata"),
                    )
                    assets.append(asset)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid asset data in point {point.id}: {e}")
                    continue

            logger.debug(f"Retrieved {len(assets)} assets from storage")
            return assets

        except Exception as e:
            logger.error(f"Failed to list assets: {e}")
            return []

    @log_function()
    async def update_asset(
        self,
        deal_id: str,
        deal_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        asset_type: Optional[AssetType] = None,
        identifiers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update an existing asset.

        Args:
            deal_id: Asset identifier
            deal_name: New deal name (optional)
            asset_name: New asset name (optional)
            asset_type: New asset type (optional)
            identifiers: New identifiers (optional)
            metadata: New metadata (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing asset
            asset = await self.get_asset(deal_id)
            if not asset:
                logger.warning(f"Asset not found for update: {deal_id}")
                return False

            # Update fields
            if deal_name is not None:
                asset.deal_name = deal_name
            if asset_name is not None:
                asset.asset_name = asset_name
            if asset_type is not None:
                asset.asset_type = asset_type
            if identifiers is not None:
                asset.identifiers = identifiers
            if metadata is not None:
                asset.metadata = metadata

            asset.last_updated = datetime.now(UTC)

            # Update in Qdrant
            if self.qdrant:
                asset_data = {
                    "deal_id": asset.deal_id,
                    "deal_name": asset.deal_name,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type.value,
                    "identifiers": asset.identifiers,
                    "created_date": asset.created_date.isoformat(),
                    "last_updated": asset.last_updated.isoformat(),
                    "folder_path": asset.folder_path,
                    "metadata": asset.metadata or {},
                }

                point = PointStruct(
                    id=deal_id,
                    vector=[0.0] * 384,  # Placeholder vector
                    payload=asset_data,
                )

                self.qdrant.upsert(collection_name=self.collection_name, points=[point])

            logger.info(f"Updated asset: {asset.deal_name} ({deal_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to update asset {deal_id}: {e}")
            return False

    @log_function()
    async def delete_asset(self, deal_id: str) -> bool:
        """
        Delete an asset.

        Args:
            deal_id: Asset identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get asset for folder info
            asset = await self.get_asset(deal_id)
            if not asset:
                logger.warning(f"Asset not found for deletion: {deal_id}")
                return False

            # Delete from Qdrant
            if self.qdrant:
                self.qdrant.delete(
                    collection_name=self.collection_name, points_selector=[deal_id]
                )

            # Note: We don't delete the folder as it may contain important documents
            logger.warning(
                f"Asset {deal_id} deleted from database. "
                f"Folder preserved at: {self.base_assets_path / asset.folder_path}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to delete asset {deal_id}: {e}")
            return False

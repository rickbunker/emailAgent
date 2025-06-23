"""
Asset management service for CRUD operations.

This module provides a clean service layer for managing assets,
replacing the asset management functionality from the old monolithic
AssetDocumentAgent.
"""

# # Standard library imports
import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

# # Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

# # Local application imports
from src.asset_management.core.data_models import Asset, AssetType
from src.memory.semantic import KnowledgeType, SemanticMemory
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
        self.semantic_memory = SemanticMemory()
        self._folder_rules_cache = {}

        # Create base assets directory if it doesn't exist
        self.base_assets_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Asset service initialized with base path: {self.base_assets_path}"
        )

    def _string_to_uuid(self, string_id: str) -> str:
        """Convert a string ID to a deterministic UUID."""
        # Create a deterministic UUID from the string using SHA-256
        hash_bytes = hashlib.sha256(string_id.encode()).digest()
        # Use first 16 bytes to create a UUID
        return str(uuid.UUID(bytes=hash_bytes[:16]))

    @log_function()
    async def _get_folder_structure(self, asset_type: AssetType) -> list[str]:
        """
        Get folder structure for an asset type from business rules in memory.

        Args:
            asset_type: The asset type to get folder structure for

        Returns:
            List of folder names to create
        """
        cache_key = asset_type.value
        if cache_key in self._folder_rules_cache:
            return self._folder_rules_cache[cache_key]

        try:
            # First try to get asset-type-specific folder structure
            asset_type_rules = await self.semantic_memory.search(
                query=f"Asset type {asset_type.value} folder structure",
                limit=10,
                knowledge_type=KnowledgeType.RULE,
            )

            folders = []
            for rule in asset_type_rules:
                metadata = (
                    rule.metadata
                )  # Access metadata property directly from MemoryItem
                if (
                    metadata.get("rule_category") == "asset_folder_structure"
                    and metadata.get("rule_type") == "asset_type_specific"
                    and metadata.get("asset_type") == asset_type.value
                ):
                    folders = metadata.get("folders", [])
                    break

            # Fall back to standard folder structure if no asset-specific structure found
            if not folders:
                logger.info(
                    f"No specific folder structure for {asset_type.value}, using standard structure"
                )
                standard_rules = await self.semantic_memory.search(
                    query="Asset folder standard folders",
                    limit=20,
                    knowledge_type=KnowledgeType.RULE,
                )

                # Collect standard folders with their priorities
                folder_info = []
                for rule in standard_rules:
                    metadata = (
                        rule.metadata
                    )  # Access metadata property directly from MemoryItem
                    if (
                        metadata.get("rule_category") == "asset_folder_structure"
                        and metadata.get("rule_type") == "standard_folder"
                    ):
                        folder_info.append(
                            {
                                "name": metadata.get("folder_name"),
                                "required": metadata.get("required", True),
                                "priority": metadata.get("priority", 999),
                            }
                        )

                # Sort by priority and get folder names
                folder_info.sort(key=lambda x: x["priority"])
                folders = [
                    f["name"] for f in folder_info if f["name"] and f["required"]
                ]

            # Cache the result
            self._folder_rules_cache[cache_key] = folders

            logger.info(f"Folder structure for {asset_type.value}: {folders}")
            return folders

        except Exception as e:
            logger.error(f"Failed to get folder structure from memory: {e}")
            # Fallback to minimal hardcoded structure as last resort
            fallback_folders = ["correspondence", "needs_review"]
            logger.warning(f"Using fallback folder structure: {fallback_folders}")
            return fallback_folders

    @log_function()
    async def initialize_collection(self) -> None:
        """Initialize the Qdrant collection for assets."""
        if not self.qdrant:
            logger.warning("No Qdrant client - skipping collection initialization")
            return

        try:
            # # Third-party imports
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
        identifiers: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
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
                # Convert string ID to UUID for Qdrant
                point_id = self._string_to_uuid(deal_id)
                point = PointStruct(
                    id=point_id,
                    vector=[0.0] * 384,  # Placeholder vector
                    payload=asset_data,
                )

                self.qdrant.upsert(collection_name=self.collection_name, points=[point])
                logger.info(f"Stored asset in Qdrant: {deal_name} ({deal_id})")

            # Create asset folder
            asset_folder = self.base_assets_path / asset.folder_path
            asset_folder.mkdir(parents=True, exist_ok=True)

            # Create subfolders based on business rules from memory
            folder_structure = await self._get_folder_structure(asset_type)
            for subfolder in folder_structure:
                (asset_folder / subfolder).mkdir(exist_ok=True)
                logger.debug(f"Created subfolder: {subfolder}")

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
            # Convert string ID to UUID for Qdrant lookup
            point_id = self._string_to_uuid(deal_id)

            # Retrieve from Qdrant
            points = self.qdrant.retrieve(
                collection_name=self.collection_name, ids=[point_id]
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
    async def list_assets(self) -> list[Asset]:
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
        identifiers: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
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

                point_id = self._string_to_uuid(deal_id)
                point = PointStruct(
                    id=point_id,
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
                point_id = self._string_to_uuid(deal_id)
                self.qdrant.delete(
                    collection_name=self.collection_name, points_selector=[point_id]
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

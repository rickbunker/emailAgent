"""
Sender mapping integration for asset identification.

This module integrates with the existing asset_management_sender_mappings
collection to check if an email sender is mapped to a specific asset.
Uses the existing infrastructure rather than duplicating it.
"""

# # Standard library imports
from typing import Any, Optional

# # Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

# # Local application imports
from src.asset_management.core.data_models import AssetMatch, SenderMapping
from src.asset_management.core.exceptions import MemorySystemError
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class SenderMappingService:
    """
    Service for accessing sender-to-asset mappings.

    This integrates with the existing asset_management_sender_mappings
    collection in Qdrant to check if email senders are mapped to specific assets.
    """

    COLLECTION_NAME = "asset_management_sender_mappings"

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize the sender mapping service.

        Args:
            qdrant_client: Optional Qdrant client instance.
                          If not provided, creates a new one from config.
        """
        self.qdrant = qdrant_client or self._create_qdrant_client()

    def _create_qdrant_client(self) -> QdrantClient:
        """Create a new Qdrant client from configuration."""
        try:
            return QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        except Exception as e:
            logger.error(f"Failed to create Qdrant client: {e}")
            raise MemorySystemError(
                "Could not connect to Qdrant", details={"error": str(e)}
            )

    @log_function()
    async def get_sender_assets(self, sender_email: str) -> list[SenderMapping]:
        """
        Get all assets associated with a sender email.

        This method queries the existing asset_management_sender_mappings
        collection to find all assets mapped to the given sender.

        Args:
            sender_email: Email address to look up

        Returns:
            List of sender mappings for this email

        Raises:
            MemorySystemError: If the query fails
        """
        logger.info(f"Looking up sender mappings for: {sender_email}")

        if not self.qdrant:
            logger.warning("Qdrant client not available")
            return []

        try:
            # Query the existing collection
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="sender_email",
                            match=MatchValue(value=sender_email.lower()),
                        )
                    ]
                ),
                limit=100,
            )

            mappings = []
            if search_result[0]:
                logger.info(f"Found {len(search_result[0])} sender mapping(s)")

                for point in search_result[0]:
                    if point.payload is None:
                        continue

                    mapping = SenderMapping(
                        mapping_id=str(point.id),
                        sender_email=point.payload.get("sender_email", ""),
                        asset_id=point.payload.get("asset_id", ""),
                        confidence=point.payload.get("confidence", 1.0),
                        created_date=point.payload.get("created_date"),
                        last_activity=point.payload.get("last_activity"),
                        email_count=point.payload.get("email_count", 0),
                        metadata=point.payload.get("metadata", {}),
                    )
                    mappings.append(mapping)

                    logger.debug(
                        f"Mapping: {mapping.asset_id} "
                        f"(confidence: {mapping.confidence:.3f})"
                    )
            else:
                logger.info(f"No sender mappings found for: {sender_email}")

            return mappings

        except Exception as e:
            logger.error(f"Error querying sender mappings: {e}")
            raise MemorySystemError(
                f"Failed to query sender mappings for {sender_email}",
                details={"error": str(e)},
            )

    @log_function()
    async def get_asset_match_from_sender(
        self, sender_email: str, known_assets: Optional[dict[str, Any]] = None
    ) -> Optional[AssetMatch]:
        """
        Get the best asset match for a sender email.

        If multiple mappings exist, returns the one with highest confidence.

        Args:
            sender_email: Email address to look up
            known_assets: Optional dict of known assets for name lookup

        Returns:
            AssetMatch if a mapping exists, None otherwise
        """
        mappings = await self.get_sender_assets(sender_email)

        if not mappings:
            return None

        # Sort by confidence and pick the highest
        best_mapping = max(mappings, key=lambda m: m.confidence)

        # Get asset name if known_assets provided
        asset_name = "Unknown"
        if known_assets and best_mapping.asset_id in known_assets:
            asset_name = known_assets[best_mapping.asset_id].get("deal_name", "Unknown")

        return AssetMatch(
            asset_id=best_mapping.asset_id,
            asset_name=asset_name,
            confidence=best_mapping.confidence,
            match_source="sender_mapping",
            match_details={
                "sender_email": sender_email,
                "mapping_id": best_mapping.mapping_id,
                "email_count": best_mapping.email_count,
                "created_date": best_mapping.created_date,
            },
        )

    @log_function()
    async def list_all_mappings(
        self, asset_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> tuple[list[SenderMapping], int]:
        """
        List all sender mappings with optional filtering.

        Args:
            asset_id: Optional asset ID to filter by
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Tuple of (list of mappings, total count)

        Raises:
            MemorySystemError: If the query fails
        """
        logger.info(
            f"Listing sender mappings (asset_id={asset_id}, limit={limit}, offset={offset})"
        )

        if not self.qdrant:
            logger.warning("Qdrant client not available")
            return [], 0

        try:
            # Build filter if asset_id provided
            query_filter = None
            if asset_id:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="asset_id",
                            match=MatchValue(value=asset_id),
                        )
                    ]
                )

            # Get total count
            count_result = self.qdrant.count(
                collection_name=self.COLLECTION_NAME,
                count_filter=query_filter,
                exact=True,
            )
            total_count = count_result.count

            # Query with pagination
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=query_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            mappings = []
            if search_result[0]:
                for point in search_result[0]:
                    if point.payload is None:
                        continue

                    mapping = SenderMapping(
                        mapping_id=str(point.id),
                        sender_email=point.payload.get("sender_email", ""),
                        asset_id=point.payload.get("asset_id", ""),
                        confidence=point.payload.get("confidence", 1.0),
                        created_date=point.payload.get("created_date"),
                        last_activity=point.payload.get("last_activity"),
                        email_count=point.payload.get("email_count", 0),
                        metadata=point.payload.get("metadata", {}),
                    )
                    mappings.append(mapping)

            logger.info(f"Found {len(mappings)} sender mappings (total: {total_count})")
            return mappings, total_count

        except Exception as e:
            logger.error(f"Error listing sender mappings: {e}")
            raise MemorySystemError(
                "Failed to list sender mappings",
                details={"error": str(e)},
            )

    @log_function()
    async def get_mapping(self, mapping_id: str) -> Optional[SenderMapping]:
        """
        Get a specific sender mapping by ID.

        Args:
            mapping_id: The mapping ID to retrieve

        Returns:
            SenderMapping if found, None otherwise

        Raises:
            MemorySystemError: If the query fails
        """
        logger.info(f"Getting sender mapping: {mapping_id}")

        if not self.qdrant:
            logger.warning("Qdrant client not available")
            return None

        try:
            # Get the specific point
            points = self.qdrant.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[mapping_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                logger.info(f"Sender mapping not found: {mapping_id}")
                return None

            point = points[0]
            if point.payload is None:
                return None

            mapping = SenderMapping(
                mapping_id=str(point.id),
                sender_email=point.payload.get("sender_email", ""),
                asset_id=point.payload.get("asset_id", ""),
                confidence=point.payload.get("confidence", 1.0),
                created_date=point.payload.get("created_date"),
                last_activity=point.payload.get("last_activity"),
                email_count=point.payload.get("email_count", 0),
                metadata=point.payload.get("metadata", {}),
            )

            logger.info(
                f"Found sender mapping: {mapping.sender_email} -> {mapping.asset_id}"
            )
            return mapping

        except Exception as e:
            logger.error(f"Error getting sender mapping: {e}")
            raise MemorySystemError(
                f"Failed to get sender mapping {mapping_id}",
                details={"error": str(e)},
            )

    @log_function()
    async def create_mapping(
        self,
        sender_email: str,
        asset_id: str,
        organization: Optional[str] = None,
        notes: Optional[str] = None,
        confidence: float = 1.0,
    ) -> SenderMapping:
        """
        Create a new sender mapping.

        Args:
            sender_email: Email address to map
            asset_id: Asset ID to map to
            organization: Optional organization name
            notes: Optional notes about the mapping
            confidence: Confidence score (0-1)

        Returns:
            Created SenderMapping

        Raises:
            MemorySystemError: If creation fails
        """
        import uuid
        from datetime import datetime

        logger.info(f"Creating sender mapping: {sender_email} -> {asset_id}")

        if not self.qdrant:
            raise MemorySystemError("Qdrant client not available")

        try:
            # Generate a unique ID
            mapping_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            # Create the payload
            payload = {
                "sender_email": sender_email.lower(),
                "asset_id": asset_id,
                "confidence": confidence,
                "created_date": now,
                "last_activity": now,
                "email_count": 0,
                "metadata": {
                    "organization": organization,
                    "notes": notes,
                    "created_via": "web_api",
                },
            }

            # Upsert to Qdrant
            from qdrant_client.models import PointStruct

            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=mapping_id,
                        payload=payload,
                        vector={},  # Empty vector for non-semantic collection
                    )
                ],
            )

            # Return the created mapping
            mapping = SenderMapping(
                mapping_id=mapping_id,
                sender_email=sender_email.lower(),
                asset_id=asset_id,
                confidence=confidence,
                created_date=now,
                last_activity=now,
                email_count=0,
                metadata=payload["metadata"],
            )

            logger.info(f"Created sender mapping: {mapping_id}")
            return mapping

        except Exception as e:
            logger.error(f"Error creating sender mapping: {e}")
            raise MemorySystemError(
                "Failed to create sender mapping",
                details={"error": str(e)},
            )

    @log_function()
    async def update_mapping(
        self,
        mapping_id: str,
        asset_id: Optional[str] = None,
        organization: Optional[str] = None,
        notes: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Optional[SenderMapping]:
        """
        Update an existing sender mapping.

        Args:
            mapping_id: The mapping ID to update
            asset_id: Optional new asset ID
            organization: Optional new organization
            notes: Optional new notes
            confidence: Optional new confidence score

        Returns:
            Updated SenderMapping if successful, None if not found

        Raises:
            MemorySystemError: If update fails
        """
        logger.info(f"Updating sender mapping: {mapping_id}")

        # First get the existing mapping
        existing = await self.get_mapping(mapping_id)
        if not existing:
            logger.warning(f"Sender mapping not found for update: {mapping_id}")
            return None

        try:
            from datetime import datetime

            # Build update payload
            updates = {}
            if asset_id is not None:
                updates["asset_id"] = asset_id
            if confidence is not None:
                updates["confidence"] = confidence

            # Update metadata
            metadata = existing.metadata.copy() if existing.metadata else {}
            if organization is not None:
                metadata["organization"] = organization
            if notes is not None:
                metadata["notes"] = notes
            updates["metadata"] = metadata

            # Always update last_activity
            updates["last_activity"] = datetime.utcnow().isoformat()

            # Update in Qdrant
            self.qdrant.set_payload(
                collection_name=self.COLLECTION_NAME,
                payload=updates,
                points=[mapping_id],
            )

            # Return updated mapping
            updated = await self.get_mapping(mapping_id)
            logger.info(f"Updated sender mapping: {mapping_id}")
            return updated

        except Exception as e:
            logger.error(f"Error updating sender mapping: {e}")
            raise MemorySystemError(
                f"Failed to update sender mapping {mapping_id}",
                details={"error": str(e)},
            )

    @log_function()
    async def delete_mapping(self, mapping_id: str) -> bool:
        """
        Delete a sender mapping.

        Args:
            mapping_id: The mapping ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            MemorySystemError: If deletion fails
        """
        logger.info(f"Deleting sender mapping: {mapping_id}")

        if not self.qdrant:
            logger.warning("Qdrant client not available")
            return False

        try:
            # Check if exists first
            existing = await self.get_mapping(mapping_id)
            if not existing:
                logger.warning(f"Sender mapping not found for deletion: {mapping_id}")
                return False

            # Delete from Qdrant
            self.qdrant.delete(
                collection_name=self.COLLECTION_NAME, points_selector=[mapping_id]
            )

            logger.info(f"Deleted sender mapping: {mapping_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting sender mapping: {e}")
            raise MemorySystemError(
                f"Failed to delete sender mapping {mapping_id}",
                details={"error": str(e)},
            )

    async def check_collection_exists(self) -> bool:
        """
        Check if the sender mappings collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.qdrant.get_collections()
            return any(c.name == self.COLLECTION_NAME for c in collections.collections)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

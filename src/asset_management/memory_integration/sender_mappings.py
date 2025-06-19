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

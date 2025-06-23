#!/usr/bin/env python3
"""
Load assets and sender mappings into their proper Qdrant collections.
This bridges the gap between the new memory system and the old collection-based approach.
"""

# # Standard library imports
import asyncio
import hashlib
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

# # Local application imports
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


def string_to_uuid(string_id: str) -> str:
    """Convert a string ID to a deterministic UUID."""
    # Create a deterministic UUID from the string using SHA-256
    hash_bytes = hashlib.sha256(string_id.encode()).digest()
    # Use first 16 bytes to create a UUID
    return str(uuid.UUID(bytes=hash_bytes[:16]))


async def create_assets_collection(client: QdrantClient) -> None:
    """Create the assets collection if it doesn't exist."""
    try:
        collections = client.get_collections()
        if "assets" not in [c.name for c in collections.collections]:
            client.create_collection(
                collection_name="assets",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info("Created 'assets' collection")
        else:
            logger.info("'assets' collection already exists")
    except Exception as e:
        logger.error(f"Failed to create assets collection: {e}")
        raise


async def create_sender_mappings_collection(client: QdrantClient) -> None:
    """Create the sender mappings collection if it doesn't exist."""
    try:
        collections = client.get_collections()
        if "asset_management_sender_mappings" not in [
            c.name for c in collections.collections
        ]:
            # Create a collection without vectors (just for payload storage)
            client.create_collection(
                collection_name="asset_management_sender_mappings",
                vectors_config={},  # No vectors needed
                on_disk_payload=True,
            )

            # Create payload indexes for efficient querying
            client.create_payload_index(
                collection_name="asset_management_sender_mappings",
                field_name="sender_email",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name="asset_management_sender_mappings",
                field_name="asset_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )

            logger.info(
                "Created 'asset_management_sender_mappings' collection with indexes"
            )
        else:
            logger.info("'asset_management_sender_mappings' collection already exists")
    except Exception as e:
        logger.error(f"Failed to create sender mappings collection: {e}")
        raise


async def load_assets_from_knowledge(client: QdrantClient) -> int:
    """Load assets from knowledge base into the assets collection."""
    knowledge_file = project_root / "knowledge" / "asset_data.json"

    if not knowledge_file.exists():
        logger.error(f"Asset data file not found: {knowledge_file}")
        return 0

    with open(knowledge_file) as f:
        data = json.load(f)

    assets = data.get("assets", [])
    logger.info(f"Loading {len(assets)} assets into 'assets' collection")

    points = []
    for asset in assets:
        deal_id = asset.get("asset_id", str(uuid.uuid4()))
        deal_name = asset.get("deal_name", "Unknown")

        # Create folder path
        folder_path = f"{deal_id}_{deal_name.replace(' ', '_')}"

        # Create asset payload
        payload = {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "asset_name": asset.get("asset_name", deal_name),
            "asset_type": asset.get("asset_type", "private_credit"),
            "identifiers": asset.get("identifiers", []),
            "created_date": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
            "folder_path": folder_path,
            "metadata": {
                "business_context": asset.get("business_context", {}),
                "key_contacts": asset.get("key_contacts", []),
                "document_patterns": asset.get("document_patterns", []),
            },
        }

        # Create point with placeholder vector
        # Convert string ID to deterministic UUID for Qdrant
        point_id = string_to_uuid(deal_id)
        point = PointStruct(
            id=point_id,
            vector=[0.0] * 384,  # Placeholder vector
            payload=payload,
        )
        points.append(point)

        logger.info(f"   ID conversion: {deal_id} -> {point_id}")

        logger.info(f"✅ Prepared asset: {deal_name} ({deal_id})")

    # Upsert all points
    if points:
        client.upsert(collection_name="assets", points=points)
        logger.info(
            f"Successfully loaded {len(points)} assets into 'assets' collection"
        )

    return len(points)


async def load_sender_mappings_from_knowledge(client: QdrantClient) -> int:
    """Load sender mappings from knowledge base into the collection."""
    knowledge_file = project_root / "knowledge" / "sender_mappings.json"

    if not knowledge_file.exists():
        logger.error(f"Sender mappings file not found: {knowledge_file}")
        return 0

    with open(knowledge_file) as f:
        data = json.load(f)

    mappings = data.get("sender_mappings", [])
    logger.info(f"Loading {len(mappings)} sender mappings")

    points = []
    for mapping in mappings:
        mapping_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Create mapping payload
        payload = {
            "sender_email": mapping["sender_email"].lower(),
            "asset_id": mapping["asset_id"],
            "confidence": mapping.get("confidence", 0.95),
            "created_date": now,
            "last_activity": now,
            "email_count": 0,
            "metadata": {
                "organization": mapping.get("organization"),
                "notes": f"Pre-configured mapping to {mapping.get('asset_name')}",
                "relationship_type": mapping.get("relationship_type", "lender"),
                "trust_score": mapping.get("trust_score", 0.90),
                "created_via": "knowledge_base",
            },
        }

        # Create point without vector
        point = PointStruct(
            id=mapping_id,
            payload=payload,
            vector={},  # Empty vector for non-semantic collection
        )
        points.append(point)

        logger.info(
            f"✅ Prepared mapping: {mapping['sender_email']} -> {mapping['asset_name']}"
        )

    # Upsert all points
    if points:
        client.upsert(collection_name="asset_management_sender_mappings", points=points)
        logger.info(
            f"Successfully loaded {len(points)} sender mappings into collection"
        )

    return len(points)


async def main():
    """Main function to load assets and sender mappings."""
    logger.info("=" * 60)
    logger.info("Loading Assets and Sender Mappings into Qdrant Collections")
    logger.info("=" * 60)

    # Initialize Qdrant client
    client = QdrantClient(url="http://localhost:6333")

    try:
        # Create collections if needed
        await create_assets_collection(client)
        await create_sender_mappings_collection(client)

        # Load data
        assets_loaded = await load_assets_from_knowledge(client)
        mappings_loaded = await load_sender_mappings_from_knowledge(client)

        # Summary
        logger.info("=" * 60)
        logger.info("Loading Complete!")
        logger.info(f"  Assets loaded: {assets_loaded}")
        logger.info(f"  Sender mappings loaded: {mappings_loaded}")
        logger.info("=" * 60)

        # Verify the data
        assets_count = client.count("assets").count
        mappings_count = client.count("asset_management_sender_mappings").count

        logger.info("Verification:")
        logger.info(f"  Total assets in collection: {assets_count}")
        logger.info(f"  Total sender mappings in collection: {mappings_count}")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

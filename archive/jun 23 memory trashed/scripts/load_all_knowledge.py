#!/usr/bin/env python3
"""
Load all knowledge base data into memory systems.

This script systematically loads all JSON files from the knowledge directory
into the appropriate memory systems.
"""

# # Standard library imports
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# # Third-party imports
from qdrant_client import QdrantClient

# # Local application imports
from src.asset_management.services.asset_service import AssetService
from src.memory.contact import ContactMemory
from src.memory.episodic import EpisodicMemory
from src.memory.procedural import ProceduralMemory
from src.memory.semantic import KnowledgeConfidence, KnowledgeType, SemanticMemory
from src.utils.config import PROJECT_ROOT, config
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def load_asset_data(
    semantic_memory: SemanticMemory, asset_service: AssetService
) -> int:
    """Load asset data into semantic memory and asset service."""
    file_path = PROJECT_ROOT / "knowledge" / "asset_data.json"

    if not file_path.exists():
        logger.warning(f"Asset data file not found: {file_path}")
        return 0

    with open(file_path) as f:
        data = json.load(f)

    assets = data.get("assets", [])
    items_loaded = 0

    logger.info(f"Loading {len(assets)} assets into memory")

    for asset in assets:
        try:
            # Load into semantic memory
            content = f"Asset: {asset['deal_name']} ({asset['asset_name']})"
            content += f"\nType: {asset['asset_type']}"
            content += f"\nIdentifiers: {', '.join(asset['identifiers'])}"

            if "business_context" in asset:
                context = asset["business_context"]
                content += f"\nDescription: {context.get('description', '')}"
                content += f"\nLender: {context.get('lender', '')}"
                content += f"\nKeywords: {', '.join(context.get('keywords', []))}"

            metadata = {
                "asset_id": asset["asset_id"],
                "deal_name": asset["deal_name"],
                "asset_type": asset["asset_type"],
                "category": "asset_data",
                "source": "knowledge_base",
            }

            await semantic_memory.add(
                content=content,
                knowledge_type=KnowledgeType.UNKNOWN,  # Assets are general knowledge
                confidence=KnowledgeConfidence.HIGH,
                metadata=metadata,
            )

            # Also register with asset service
            await asset_service.create_asset(
                deal_name=asset["deal_name"], asset_type=asset["asset_type"]
            )

            items_loaded += 1
            logger.info(f"Loaded asset: {asset['deal_name']}")

        except Exception as e:
            logger.error(
                f"Failed to load asset {asset.get('deal_name', 'unknown')}: {e}"
            )

    return items_loaded


async def load_spam_patterns(procedural_memory: ProceduralMemory) -> int:
    """Load spam patterns into procedural memory."""
    # The seed_from_knowledge_base method doesn't handle spam patterns,
    # so we'll skip this for now and handle it through the new knowledge base system
    logger.info("Spam patterns will be loaded through the new knowledge base system")
    return 0


async def load_contact_patterns(procedural_memory: ProceduralMemory) -> int:
    """Load contact patterns into procedural memory."""
    # The seed_from_knowledge_base method doesn't handle contact patterns,
    # so we'll skip this for now and handle it through the new knowledge base system
    logger.info("Contact patterns will be loaded through the new knowledge base system")
    return 0


async def load_business_rules(procedural_memory: ProceduralMemory) -> int:
    """Load business rules into procedural memory."""
    # Business rules are handled by seed_from_knowledge_base
    logger.info("Business rules loaded via seed_from_knowledge_base")
    return 0


async def load_asset_types(semantic_memory: SemanticMemory) -> int:
    """Load asset types and document categories into semantic memory."""
    file_path = PROJECT_ROOT / "knowledge" / "asset_types.json"

    if not file_path.exists():
        logger.warning(f"Asset types file not found: {file_path}")
        return 0

    with open(file_path) as f:
        data = json.load(f)

    items_loaded = 0

    # Load asset types
    for asset_type in data.get("asset_types", {}).get("types", []):
        content = f"Asset Type: {asset_type['display_name']}"
        content += f"\nID: {asset_type['type_id']}"
        content += f"\nDescription: {asset_type['description']}"
        content += (
            f"\nIdentifiers: {', '.join(asset_type.get('common_identifiers', []))}"
        )
        content += (
            f"\nTypical Documents: {', '.join(asset_type.get('typical_documents', []))}"
        )

        metadata = {
            "type_id": asset_type["type_id"],
            "category": "asset_type_definition",
            "source": "knowledge_base",
        }

        await semantic_memory.add(
            content=content,
            knowledge_type=KnowledgeType.DOMAIN,  # Asset type knowledge is domain expertise
            confidence=KnowledgeConfidence.HIGH,
            metadata=metadata,
        )
        items_loaded += 1

    # Load document categories
    for doc_cat in data.get("document_categories", {}).get("categories", []):
        content = f"Document Category: {doc_cat['display_name']}"
        content += f"\nID: {doc_cat['category_id']}"
        content += f"\nDescription: {doc_cat['description']}"
        content += f"\nAsset Types: {', '.join(doc_cat.get('asset_types', []))}"
        content += f"\nKeywords: {', '.join(doc_cat.get('keywords', []))}"

        metadata = {
            "category_id": doc_cat["category_id"],
            "category": "document_category",
            "asset_types": doc_cat.get("asset_types", []),
            "source": "knowledge_base",
        }

        await semantic_memory.add(
            content=content,
            knowledge_type=KnowledgeType.DOMAIN,  # Document categories are domain knowledge
            confidence=KnowledgeConfidence.HIGH,
            metadata=metadata,
        )
        items_loaded += 1

    logger.info(f"Loaded {items_loaded} asset type definitions")
    return items_loaded


async def main():
    """Main function to load all knowledge base data."""
    logger.info("Starting knowledge base loading process")

    # Get Qdrant URL from config
    qdrant_url = f"http://{config.qdrant_host}:{config.qdrant_port}"

    # Create Qdrant client for ProceduralMemory
    qdrant_client = QdrantClient(url=qdrant_url)

    # Initialize memory systems
    semantic_memory = SemanticMemory(qdrant_url=qdrant_url)
    episodic_memory = EpisodicMemory(qdrant_url=qdrant_url)
    procedural_memory = ProceduralMemory(qdrant_client=qdrant_client)
    contact_memory = ContactMemory(qdrant_url=qdrant_url)

    # Initialize asset service
    asset_service = AssetService()
    await asset_service.initialize_collection()

    total_loaded = 0

    try:
        # Initialize procedural memory collections first
        logger.info("Initializing procedural memory collections...")
        await procedural_memory.initialize_collections()

        # Load procedural patterns from knowledge base
        logger.info("Loading procedural patterns from knowledge base...")
        knowledge_path = str(PROJECT_ROOT / "knowledge")
        procedural_stats = await procedural_memory.seed_from_knowledge_base(
            knowledge_path
        )
        total_loaded += procedural_stats.get("total_patterns", 0)
        logger.info(
            f"✓ Loaded {procedural_stats.get('total_patterns', 0)} procedural patterns"
        )

        # Load asset data
        logger.info("Loading asset data...")
        items = await load_asset_data(semantic_memory, asset_service)
        total_loaded += items
        logger.info(f"✓ Loaded {items} asset records")

        # Load asset types
        logger.info("Loading asset types...")
        items = await load_asset_types(semantic_memory)
        total_loaded += items
        logger.info(f"✓ Loaded {items} asset type definitions")

        # The following are now handled by procedural memory seed_from_knowledge_base
        # or will be handled through the new system
        logger.info(
            "Spam patterns and contact patterns will be loaded through the new knowledge base system"
        )

        logger.info("\n✅ Knowledge base loading complete!")
        logger.info(f"Total items loaded: {total_loaded}")

        # Show summary of each memory system
        logger.info("\nMemory System Summary:")

        semantic_info = await semantic_memory.get_collection_info()
        logger.info(f"- Semantic Memory: {semantic_info.get('count', 0)} items")

        episodic_info = await episodic_memory.get_collection_info()
        logger.info(f"- Episodic Memory: {episodic_info.get('count', 0)} items")

        procedural_pattern_stats = await procedural_memory.get_pattern_stats()
        logger.info(
            f"- Procedural Memory: {procedural_pattern_stats.get('total_patterns', 0)} patterns"
        )

        contact_info = await contact_memory.get_collection_info()
        logger.info(f"- Contact Memory: {contact_info.get('count', 0)} items")

        # Show procedural memory breakdown
        if procedural_stats:
            logger.info("\nProcedural Memory Breakdown:")
            for pattern_type, count in procedural_stats.items():
                if pattern_type != "total_patterns":
                    logger.info(f"  - {pattern_type}: {count}")

    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

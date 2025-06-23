#!/usr/bin/env python3
"""
Load the NEW clean knowledge base into memory systems.
This script properly loads each type of knowledge into the correct memory system.
"""

# # Standard library imports
import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
from src.memory.contact import ContactMemory
from src.memory.episodic import EpisodicMemory
from src.memory.procedural import ProceduralMemory
from src.memory.semantic import KnowledgeConfidence, KnowledgeType, SemanticMemory
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def load_assets(semantic_memory: SemanticMemory) -> int:
    """Load asset definitions into semantic memory."""
    file_path = project_root / "knowledge" / "asset_data.json"
    logger.info(f"Loading assets from {file_path}")

    with open(file_path) as f:
        data = json.load(f)

    items_loaded = 0
    for asset in data["assets"]:
        # Create comprehensive content for semantic understanding
        content = f"""Asset Definition:
Name: {asset['deal_name']}
ID: {asset['asset_id']}
Type: {asset['asset_type']}
Full Name: {asset['asset_name']}
Identifiers: {', '.join(asset['identifiers'])}
Lender: {asset['business_context']['lender']}
Facility Type: {asset['business_context']['facility_type']}
Document Identifiers: {', '.join(asset['business_context']['document_identifiers'])}
Common Filename Patterns: {', '.join(asset['business_context']['common_filename_patterns'])}"""

        metadata = {
            "source": "asset_data.json",
            "asset_id": asset["asset_id"],
            "deal_name": asset["deal_name"],
            "asset_type": asset["asset_type"],
            "lender": asset["business_context"]["lender"],
        }

        await semantic_memory.add(
            content=content,
            knowledge_type=KnowledgeType.DOMAIN,
            confidence=KnowledgeConfidence.HIGH,
            metadata=metadata,
        )
        items_loaded += 1
        logger.info(f"Loaded asset: {asset['deal_name']}")

    return items_loaded


async def load_document_categories(semantic_memory: SemanticMemory) -> int:
    """Load document categories into semantic memory."""
    file_path = project_root / "knowledge" / "document_categories.json"
    logger.info(f"Loading document categories from {file_path}")

    with open(file_path) as f:
        data = json.load(f)

    items_loaded = 0
    for category in data["document_categories"]:
        # Create content with classification hints
        hints = "\n".join([f"- {hint}" for hint in category["classification_hints"]])
        content = f"""Document Category:
ID: {category['category_id']}
Name: {category['display_name']}
Description: {category['description']}
Allowed Asset Types: {', '.join(category['asset_types'])}
Classification Hints:
{hints}"""

        metadata = {
            "source": "document_categories.json",
            "category_id": category["category_id"],
            "asset_types": category["asset_types"],
            "category_type": "document_classification",
        }

        await semantic_memory.add(
            content=content,
            knowledge_type=KnowledgeType.DOMAIN,
            confidence=KnowledgeConfidence.HIGH,
            metadata=metadata,
        )
        items_loaded += 1

        # Also add individual classification hints
        for hint in category["classification_hints"]:
            hint_content = f"{hint} -> Category: {category['display_name']}"
            await semantic_memory.add(
                content=hint_content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=KnowledgeConfidence.HIGH,
                metadata={
                    "source": "classification_hint",
                    "category_id": category["category_id"],
                    "hint_type": "classification",
                },
            )
            items_loaded += 1

    logger.info(f"Loaded {items_loaded} category items")
    return items_loaded


async def load_sender_mappings(contact_memory: ContactMemory) -> int:
    """Load sender mappings into contact memory."""
    file_path = project_root / "knowledge" / "sender_mappings.json"
    logger.info(f"Loading sender mappings from {file_path}")

    with open(file_path) as f:
        data = json.load(f)

    items_loaded = 0

    # Load individual sender mappings
    for mapping in data["sender_mappings"]:
        await contact_memory.add_contact(
            sender_email=mapping["sender_email"],
            organization=mapping["organization"],
            confidence=mapping["confidence"],
            metadata={
                "asset_id": mapping["asset_id"],
                "asset_name": mapping["asset_name"],
                "relationship_type": mapping["relationship_type"],
                "trust_score": mapping["trust_score"],
            },
        )

        # Create sender-to-asset mapping
        await contact_memory.create_sender_mapping(
            sender_email=mapping["sender_email"],
            asset_id=mapping["asset_id"],
            confidence=mapping["confidence"],
        )

        items_loaded += 2  # Contact + mapping
        logger.info(
            f"Loaded sender mapping: {mapping['sender_email']} -> {mapping['asset_name']}"
        )

    # Load organization patterns
    for org_pattern in data["organization_patterns"]:
        content = f"Organization {org_pattern['organization']} (domain: {org_pattern['domain']}) typically relates to {org_pattern['default_asset_hint']}"
        await contact_memory.add(
            content=content,
            metadata={
                "type": "organization_pattern",
                "domain": org_pattern["domain"],
                "organization": org_pattern["organization"],
                "asset_hint": org_pattern["default_asset_hint"],
                "confidence_boost": org_pattern["confidence_boost"],
            },
        )
        items_loaded += 1

    logger.info(f"Loaded {items_loaded} contact items")
    return items_loaded


async def initialize_procedural_patterns(procedural_memory: ProceduralMemory) -> int:
    """Initialize procedural memory with patterns from knowledge base."""
    logger.info("Initializing procedural memory from knowledge base")

    # ProceduralMemory loads patterns automatically from knowledge base
    await procedural_memory.seed_from_knowledge_base(str(project_root / "knowledge"))

    # Get counts
    counts = await procedural_memory.get_pattern_counts()
    total = sum(counts.values())

    logger.info(f"Loaded {total} procedural patterns")
    for pattern_type, count in counts.items():
        logger.info(f"  - {pattern_type}: {count}")

    return total


async def main():
    """Main loading function."""
    logger.info("=" * 60)
    logger.info("LOADING NEW CLEAN KNOWLEDGE BASE")
    logger.info("=" * 60)

    # Initialize Qdrant client
    # # Third-party imports
    from qdrant_client import QdrantClient

    qdrant_client = QdrantClient(url="http://localhost:6333")

    # Initialize memory systems
    semantic_memory = SemanticMemory()
    episodic_memory = EpisodicMemory()
    procedural_memory = ProceduralMemory(qdrant_client)
    contact_memory = ContactMemory()

    # Initialize procedural memory collections
    await procedural_memory.initialize_collections()

    # Initialize procedural collections
    await procedural_memory.initialize_collections()

    total_loaded = 0

    # 1. Load procedural patterns
    logger.info("\n1. Loading Procedural Patterns...")
    procedural_count = await initialize_procedural_patterns(procedural_memory)
    total_loaded += procedural_count

    # 2. Load assets into semantic memory
    logger.info("\n2. Loading Asset Definitions...")
    asset_count = await load_assets(semantic_memory)
    total_loaded += asset_count

    # 3. Load document categories
    logger.info("\n3. Loading Document Categories...")
    category_count = await load_document_categories(semantic_memory)
    total_loaded += category_count

    # 4. Load sender mappings
    logger.info("\n4. Loading Sender Mappings...")
    sender_count = await load_sender_mappings(contact_memory)
    total_loaded += sender_count

    # Get final counts
    logger.info("\n" + "=" * 60)
    logger.info("KNOWLEDGE BASE LOADING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nTotal items loaded: {total_loaded}")

    # Show memory stats
    semantic_info = await semantic_memory.get_collection_info()
    episodic_info = await episodic_memory.get_collection_info()
    contact_info = await contact_memory.get_collection_info()
    procedural_counts = await procedural_memory.get_pattern_counts()

    logger.info("\nMemory System Summary:")
    logger.info(f"- Semantic Memory: {semantic_info.get('points_count', 0)} items")
    logger.info(f"- Episodic Memory: {episodic_info.get('points_count', 0)} items")
    logger.info(f"- Contact Memory: {contact_info.get('points_count', 0)} items")
    logger.info(f"- Procedural Memory: {sum(procedural_counts.values())} patterns")

    logger.info("\n✅ The Email Agent is now ready to process emails!")
    logger.info("   - Asset identification will use sender mappings and identifiers")
    logger.info("   - Document classification will follow the defined categories")
    logger.info("   - Business rules will govern confidence and routing")


if __name__ == "__main__":
    asyncio.run(main())

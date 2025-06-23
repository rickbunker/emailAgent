#!/usr/bin/env python3
"""
Simple knowledge base loader for Email Agent.
This script loads all knowledge base files into the appropriate memory systems.
"""

# # Standard library imports
import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Standard library imports
import uuid

# # Third-party imports
from qdrant_client import QdrantClient

# # Local application imports
from src.memory.contact import ContactConfidence as ContactConf
from src.memory.contact import ContactMemory, ContactType
from src.memory.procedural import ProceduralMemory
from src.memory.semantic import KnowledgeConfidence, KnowledgeType, SemanticMemory
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def load_assets_to_semantic(
    semantic_memory: SemanticMemory, file_path: Path
) -> int:
    """Load asset data into semantic memory."""
    logger.info(f"Loading assets from {file_path}")
    items_loaded = 0

    with open(file_path) as f:
        data = json.load(f)

    # Load each asset
    for asset in data.get("assets", []):
        content = f"{asset['deal_name']} - {asset['asset_name']}. "
        content += f"Type: {asset.get('asset_type', 'unknown')}. "

        # Add identifiers
        if asset.get("identifiers"):
            content += f"Known as: {', '.join(asset['identifiers'])}. "

        # Add business context
        if asset.get("business_context"):
            ctx = asset["business_context"]
            content += f"Lender: {ctx.get('lender', 'N/A')}. "
            content += f"Facility type: {ctx.get('facility_type', 'N/A')}. "

        # Add classification guidance
        if asset.get("classification_guidance"):
            hints = asset["classification_guidance"].get("classification_hints", [])
            content += f"Classification hints: {'; '.join(hints)}. "

        metadata = {
            "asset_id": asset.get("asset_id"),
            "deal_name": asset.get("deal_name"),
            "asset_type": asset.get("asset_type"),
            "key_contacts": asset.get("key_contacts", []),
        }

        try:
            await semantic_memory.add(
                content=content,
                knowledge_type=KnowledgeType.UNKNOWN,  # General knowledge
                confidence=KnowledgeConfidence.HIGH,
                metadata=metadata,
            )
            items_loaded += 1
            logger.info(f"✅ Loaded asset: {asset['deal_name']}")
        except Exception as e:
            logger.error(f"Failed to load asset {asset.get('asset_id')}: {e}")

    return items_loaded


async def load_document_categories_to_semantic(
    semantic_memory: SemanticMemory, file_path: Path
) -> int:
    """Load document categories into semantic memory."""
    logger.info(f"Loading document categories from {file_path}")
    items_loaded = 0

    with open(file_path) as f:
        data = json.load(f)

    # Load each document category
    for category in data.get("document_categories", []):
        content = f"{category['display_name']}: {category['description']}. "
        content += f"For asset types: {', '.join(category.get('asset_types', []))}. "

        # Add classification hints
        if category.get("classification_hints"):
            content += f"Hints: {'; '.join(category['classification_hints'])}. "

        metadata = {
            "category_id": category.get("category_id"),
            "display_name": category.get("display_name"),
            "asset_types": category.get("asset_types", []),
        }

        try:
            await semantic_memory.add(
                content=content,
                knowledge_type=KnowledgeType.DOMAIN,  # Domain knowledge
                confidence=KnowledgeConfidence.HIGH,
                metadata=metadata,
            )
            items_loaded += 1
            logger.info(f"✅ Loaded category: {category['display_name']}")
        except Exception as e:
            logger.error(f"Failed to load category {category.get('category_id')}: {e}")

    return items_loaded


async def load_classification_patterns_to_procedural(
    procedural_memory: ProceduralMemory, file_path: Path
) -> int:
    """Load classification patterns into procedural memory."""
    logger.info(f"Loading classification patterns from {file_path}")
    items_loaded = 0

    with open(file_path) as f:
        data = json.load(f)

    # Load each classification pattern
    for pattern in data.get("classification_patterns", []):
        try:
            pattern_data = {
                "pattern_id": pattern.get("pattern_id", str(uuid.uuid4())),
                "pattern_type": "classification",
                "document_category": pattern.get("document_category"),
                "asset_type": pattern.get("asset_type"),
                "regex_patterns": pattern.get("regex_patterns", []),
                "keywords": pattern.get("keywords", []),
                "confidence_range": pattern.get("confidence_range", [0.7, 0.9]),
                "source": pattern.get("source", "knowledge_base"),
                "created_date": pattern.get("created_date"),
            }

            # Store in procedural memory
            await procedural_memory._store_procedural_pattern(pattern_data)
            items_loaded += 1
            logger.info(f"✅ Loaded pattern: {pattern.get('pattern_id')}")

        except Exception as e:
            logger.error(f"Failed to load pattern {pattern.get('pattern_id')}: {e}")

    return items_loaded


async def load_business_rules_to_procedural(
    procedural_memory: ProceduralMemory, file_path: Path
) -> int:
    """Load business rules into procedural memory."""
    logger.info(f"Loading business rules from {file_path}")
    items_loaded = 0

    with open(file_path) as f:
        data = json.load(f)

    # Load confidence thresholds as configuration rules
    confidence_thresholds = data.get("confidence_thresholds", {})
    for rule_name, thresholds in confidence_thresholds.items():
        pattern_data = {
            "pattern_id": f"confidence_{rule_name}",
            "pattern_type": "configuration",
            "rule_name": rule_name,
            "thresholds": thresholds,
            "source": "knowledge_base",
            "confidence": 1.0,
        }

        try:
            await procedural_memory._store_procedural_pattern(pattern_data)
            items_loaded += 1
            logger.info(f"✅ Loaded confidence rule: {rule_name}")
        except Exception as e:
            logger.error(f"Failed to load confidence rule {rule_name}: {e}")

    # Load processing rules
    processing_rules = data.get("processing_rules", {})
    for rule_name, rule_config in processing_rules.items():
        pattern_data = {
            "pattern_id": f"processing_{rule_name}",
            "pattern_type": "configuration",
            "rule_name": rule_name,
            "rule_config": rule_config,
            "source": "knowledge_base",
            "confidence": 1.0,
        }

        try:
            await procedural_memory._store_procedural_pattern(pattern_data)
            items_loaded += 1
            logger.info(f"✅ Loaded processing rule: {rule_name}")
        except Exception as e:
            logger.error(f"Failed to load processing rule {rule_name}: {e}")

    return items_loaded


async def load_sender_mappings_to_contact(
    contact_memory: ContactMemory, file_path: Path
) -> int:
    """Load sender mappings into contact memory."""
    logger.info(f"Loading sender mappings from {file_path}")
    items_loaded = 0

    with open(file_path) as f:
        data = json.load(f)

    # Load each sender mapping
    for mapping in data.get("sender_mappings", []):
        metadata = {
            "sender_email": mapping.get("sender_email"),
            "organization": mapping.get("organization"),
            "asset_id": mapping.get("asset_id"),
            "asset_name": mapping.get("asset_name"),
            "confidence": mapping.get("confidence", 0.95),
            "relationship_type": mapping.get("relationship_type"),
            "trust_score": mapping.get("trust_score", 0.90),
        }

        content = f"{mapping['sender_email']} from {mapping['organization']} is associated with {mapping['asset_name']}"

        try:
            await contact_memory.add_contact(
                email=mapping["sender_email"],
                organization=mapping.get("organization"),
                contact_type=ContactType.PROFESSIONAL,
                confidence=ContactConf.HIGH,
                relationship=mapping.get("relationship_type", "lender"),
                notes=f"Pre-configured mapping to {mapping['asset_name']} (confidence: {mapping.get('confidence', 0.95)}). Trust score: {mapping.get('trust_score', 0.90)}",
                tags=[f"asset:{mapping['asset_id']}", mapping["asset_name"]],
            )
            items_loaded += 1
            logger.info(f"✅ Loaded sender mapping: {mapping['sender_email']}")
        except Exception as e:
            logger.error(
                f"Failed to load sender mapping {mapping.get('sender_email')}: {e}"
            )

    return items_loaded


async def main():
    """Main function to load all knowledge."""
    logger.info("=" * 60)
    logger.info("LOADING NEW CLEAN KNOWLEDGE BASE")
    logger.info("=" * 60)

    # Initialize Qdrant client
    qdrant_client = QdrantClient(url="http://localhost:6333")

    # Initialize memory systems
    semantic_memory = SemanticMemory()
    procedural_memory = ProceduralMemory(qdrant_client)
    contact_memory = ContactMemory()

    # Initialize procedural memory collections
    await procedural_memory.initialize_collections()

    # Load knowledge files
    knowledge_dir = project_root / "knowledge"

    # Track total items loaded
    total_loaded = 0

    # 1. Load assets to semantic memory
    assets_file = knowledge_dir / "asset_data.json"
    if assets_file.exists():
        count = await load_assets_to_semantic(semantic_memory, assets_file)
        logger.info(f"Loaded {count} assets to semantic memory")
        total_loaded += count

    # 2. Load document categories to semantic memory
    categories_file = knowledge_dir / "document_categories.json"
    if categories_file.exists():
        count = await load_document_categories_to_semantic(
            semantic_memory, categories_file
        )
        logger.info(f"Loaded {count} document categories to semantic memory")
        total_loaded += count

    # 3. Load classification patterns to procedural memory
    patterns_file = knowledge_dir / "classification_patterns.json"
    if patterns_file.exists():
        count = await load_classification_patterns_to_procedural(
            procedural_memory, patterns_file
        )
        logger.info(f"Loaded {count} classification patterns to procedural memory")
        total_loaded += count

    # 4. Load business rules to procedural memory
    rules_file = knowledge_dir / "business_rules.json"
    if rules_file.exists():
        count = await load_business_rules_to_procedural(procedural_memory, rules_file)
        logger.info(f"Loaded {count} business rules to procedural memory")
        total_loaded += count

    # 5. Load sender mappings to contact memory
    senders_file = knowledge_dir / "sender_mappings.json"
    if senders_file.exists():
        count = await load_sender_mappings_to_contact(contact_memory, senders_file)
        logger.info(f"Loaded {count} sender mappings to contact memory")
        total_loaded += count

    logger.info("=" * 60)
    logger.info("✅ KNOWLEDGE LOADING COMPLETE")
    logger.info(f"✅ Total items loaded: {total_loaded}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

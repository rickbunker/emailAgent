#!/usr/bin/env python
"""
Load asset types and document categories from knowledge base into semantic memory.

This script reads asset definitions from knowledge/asset_types.json and
loads them into the semantic memory system for use throughout the application.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence
from src.utils.logging_system import get_logger, log_function
from src.utils.config import config

logger = get_logger(__name__)


@log_function()
async def load_asset_types_to_memory(
    patterns_file: Path, memory: SemanticMemory
) -> int:
    """
    Load asset types and document categories from JSON file into semantic memory.

    Args:
        patterns_file: Path to the JSON file containing asset definitions
        memory: SemanticMemory instance to load data into

    Returns:
        Number of items loaded
    """
    logger.info(f"Loading asset types from: {patterns_file}")

    with open(patterns_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items_loaded = 0

    # Load asset types
    if "asset_types" in data:
        asset_data = data["asset_types"]

        for asset_type in asset_data.get("types", []):
            # Store main asset type definition
            content = {
                "type": "asset_type",
                "type_id": asset_type["type_id"],
                "display_name": asset_type["display_name"],
                "description": asset_type.get("description", ""),
                "common_identifiers": asset_type.get("common_identifiers", []),
                "typical_documents": asset_type.get("typical_documents", []),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Asset type: {asset_type['display_name']} - {asset_type.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.FACT,
                confidence=KnowledgeConfidence.HIGH,
            )
            items_loaded += 1

            # Store identifier patterns for this asset type
            for identifier in asset_type.get("common_identifiers", []):
                identifier_content = {
                    "type": "asset_identifier",
                    "pattern": identifier.lower(),
                    "asset_type": asset_type["type_id"],
                    "display_name": asset_type["display_name"],
                    "source": "knowledge_base",
                }

                await memory.add(
                    content=f"Asset identifier '{identifier}' for {asset_type['display_name']}",
                    metadata=identifier_content,
                    knowledge_type=KnowledgeType.PATTERN,
                    confidence=KnowledgeConfidence.HIGH,
                )
                items_loaded += 1

    # Load document categories
    if "document_categories" in data:
        category_data = data["document_categories"]

        for category in category_data.get("categories", []):
            # Store main category definition
            content = {
                "type": "document_category",
                "category_id": category["category_id"],
                "display_name": category["display_name"],
                "asset_types": category.get("asset_types", []),
                "keywords": category.get("keywords", []),
                "description": category.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Document category: {category['display_name']} - {category.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.FACT,
                confidence=KnowledgeConfidence.HIGH,
            )
            items_loaded += 1

            # Store keyword patterns for this category
            for keyword in category.get("keywords", []):
                keyword_content = {
                    "type": "category_keyword",
                    "keyword": keyword.lower(),
                    "category_id": category["category_id"],
                    "display_name": category["display_name"],
                    "asset_types": category.get("asset_types", []),
                    "source": "knowledge_base",
                }

                await memory.add(
                    content=f"Category keyword '{keyword}' for {category['display_name']}",
                    metadata=keyword_content,
                    knowledge_type=KnowledgeType.PATTERN,
                    confidence=KnowledgeConfidence.MEDIUM,
                )
                items_loaded += 1

    # Load file type validation rules
    if "file_type_validation" in data:
        validation_data = data["file_type_validation"]

        # Store allowed extensions
        for ext in validation_data.get("allowed_extensions", []):
            ext_content = {
                "type": "file_validation",
                "validation_type": "allowed_extension",
                "extension": ext,
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Allowed file extension: {ext}",
                metadata=ext_content,
                knowledge_type=KnowledgeType.FACT,
                confidence=KnowledgeConfidence.HIGH,
            )
            items_loaded += 1

        # Store suspicious extensions
        for ext in validation_data.get("suspicious_extensions", []):
            ext_content = {
                "type": "file_validation",
                "validation_type": "suspicious_extension",
                "extension": ext,
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Suspicious file extension: {ext}",
                metadata=ext_content,
                knowledge_type=KnowledgeType.FACT,
                confidence=KnowledgeConfidence.HIGH,
            )
            items_loaded += 1

        # Store file size limit
        await memory.add(
            content="Maximum file size limit",
            metadata={
                "type": "file_validation",
                "validation_type": "max_file_size",
                "limit_mb": validation_data.get("max_file_size_mb", 100),
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.FACT,
            confidence=KnowledgeConfidence.HIGH,
        )
        items_loaded += 1

    logger.info(f"Successfully loaded {items_loaded} asset-related items into memory")
    return items_loaded


@log_function()
async def verify_data_loaded(memory: SemanticMemory) -> None:
    """
    Verify that asset types and categories were loaded correctly.

    Args:
        memory: SemanticMemory instance to check
    """
    logger.info("Verifying loaded asset data...")

    # Test search for different data types
    test_searches = [
        ("asset type", 10),
        ("document category", 10),
        ("commercial real estate", 5),
        ("loan documents", 5),
        ("file validation", 5),
    ]

    for query, limit in test_searches:
        results = await memory.search(query, limit=limit)
        logger.info(f"Search '{query}' returned {len(results)} results")

        for i, result in enumerate(results[:3]):
            logger.info(f"  Result {i+1}: {result.content[:50]}...")


async def main():
    """Main function to load asset types."""
    patterns_file = Path("knowledge/asset_types.json")

    if not patterns_file.exists():
        logger.error(f"Asset types file not found: {patterns_file}")
        return 1

    # Initialize semantic memory
    memory = SemanticMemory()

    # Load data
    items_loaded = await load_asset_types_to_memory(patterns_file, memory)

    # Verify loading
    await verify_data_loaded(memory)

    logger.info(f"Asset type loading complete. {items_loaded} items loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

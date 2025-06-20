#!/usr/bin/env python
"""
Load contact extraction patterns from knowledge base into semantic memory.

This script reads contact patterns from knowledge/contact_patterns.json and
loads them into the semantic memory system for use by the contact extractor.
"""

# # Standard library imports
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# # Local application imports
from src.memory.semantic import KnowledgeConfidence, KnowledgeType, SemanticMemory
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


@log_function()
async def load_contact_patterns_to_memory(
    patterns_file: Path, memory: SemanticMemory
) -> int:
    """
    Load contact patterns from JSON file into semantic memory.

    Args:
        patterns_file: Path to the JSON file containing contact patterns
        memory: SemanticMemory instance to load patterns into

    Returns:
        Number of patterns loaded
    """
    logger.info(f"Loading contact patterns from: {patterns_file}")

    with open(patterns_file, encoding="utf-8") as f:
        data = json.load(f)

    patterns_loaded = 0

    # Load no-reply patterns
    if "contact_patterns" in data and "no_reply_patterns" in data["contact_patterns"]:
        no_reply_data = data["contact_patterns"]["no_reply_patterns"]

        for pattern in no_reply_data.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "no_reply",
                "pattern": pattern["pattern"],
                "pattern_format": pattern["type"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"No-reply pattern: {pattern['description']}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.8
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load bulk domains
    if "bulk_domains" in data["contact_patterns"]:
        bulk_domains = data["contact_patterns"]["bulk_domains"]

        for pattern in bulk_domains.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "bulk_domain",
                "domain": pattern["domain"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Bulk email domain: {pattern['domain']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=KnowledgeConfidence.HIGH,
            )
            patterns_loaded += 1

    # Load personal indicators
    if "personal_indicators" in data["contact_patterns"]:
        personal_data = data["contact_patterns"]["personal_indicators"]
        weight = personal_data.get("confidence_weight", -0.5)

        for pattern in personal_data.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "personal_indicator",
                "pattern": pattern["pattern"],
                "confidence": pattern["confidence"],
                "weight": weight,
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Personal indicator pattern: {pattern['description']}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load automated indicators
    if "automated_indicators" in data["contact_patterns"]:
        automated_data = data["contact_patterns"]["automated_indicators"]
        weight = automated_data.get("confidence_weight", 0.5)

        for pattern in automated_data.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "automated_indicator",
                "pattern": pattern["pattern"],
                "confidence": pattern["confidence"],
                "weight": weight,
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Automated indicator pattern: {pattern['description']}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load local part indicators
    if "local_part_indicators" in data["contact_patterns"]:
        local_part_data = data["contact_patterns"]["local_part_indicators"]

        for pattern in local_part_data.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "local_part_indicator",
                "indicator": pattern["indicator"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Local part indicator: {pattern['indicator']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Store extraction configuration
    if "extraction_configuration" in data["contact_patterns"]:
        await memory.add(
            content="Contact extraction configuration",
            metadata={
                "type": "configuration",
                "config_type": "contact_extraction",
                "configuration": data["contact_patterns"]["extraction_configuration"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.PROCESS,
            confidence=KnowledgeConfidence.HIGH,
        )
        patterns_loaded += 1

    # Load signature markers
    if "signature_markers" in data["contact_patterns"]:
        signature_data = data["contact_patterns"]["signature_markers"]

        for pattern in signature_data.get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "signature_marker",
                "marker": pattern["marker"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Signature marker: {pattern['marker']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load contact classification terms
    if "contact_classification" in data["contact_patterns"]:
        classification_data = data["contact_patterns"]["contact_classification"]

        # Load family terms
        for pattern in classification_data.get("family_terms", {}).get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "family_term",
                "term": pattern["term"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Family term: {pattern['term']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=KnowledgeConfidence.HIGH,
            )
            patterns_loaded += 1

        # Load business terms
        for pattern in classification_data.get("business_terms", {}).get(
            "patterns", []
        ):
            content = {
                "type": "contact_pattern",
                "pattern_type": "business_term",
                "term": pattern["term"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Business term: {pattern['term']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

        # Load vendor terms
        for pattern in classification_data.get("vendor_terms", {}).get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "vendor_term",
                "term": pattern["term"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Vendor term: {pattern['term']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load organization patterns
    if "organization_patterns" in data["contact_patterns"]:
        org_data = data["contact_patterns"]["organization_patterns"]

        # Load company suffixes
        for pattern in org_data.get("company_suffixes", {}).get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "company_suffix",
                "pattern": pattern["pattern"],
                "pattern_format": pattern["type"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Company suffix pattern: {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

        # Load job titles
        for pattern in org_data.get("job_titles", {}).get("patterns", []):
            content = {
                "type": "contact_pattern",
                "pattern_type": "job_title",
                "pattern": pattern["pattern"],
                "pattern_format": pattern["type"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Job title pattern: {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    logger.info(f"Successfully loaded {patterns_loaded} contact patterns into memory")
    return patterns_loaded


@log_function()
async def verify_patterns_loaded(memory: SemanticMemory) -> None:
    """
    Verify that contact patterns were loaded correctly.

    Args:
        memory: SemanticMemory instance to check
    """
    logger.info("Verifying loaded contact patterns...")

    # Test search for different pattern types
    test_searches = [
        ("contact patterns", 10),
        ("no-reply", 5),
        ("bulk domain", 5),
        ("personal indicator", 5),
        ("automated indicator", 5),
    ]

    for query, limit in test_searches:
        results = await memory.search(
            query, limit=limit, knowledge_type=KnowledgeType.PATTERN
        )
        logger.info(f"Search '{query}' returned {len(results)} results")

        for i, result in enumerate(results[:3]):
            logger.info(f"  Result {i+1}: {result.content[:50]}...")


async def main():
    """Main function to load contact patterns."""
    patterns_file = Path("knowledge/contact_patterns.json")

    if not patterns_file.exists():
        logger.error(f"Patterns file not found: {patterns_file}")
        return 1

    # Initialize semantic memory
    memory = SemanticMemory()

    # Load patterns
    patterns_loaded = await load_contact_patterns_to_memory(patterns_file, memory)

    # Verify loading
    await verify_patterns_loaded(memory)

    logger.info(f"Contact pattern loading complete. {patterns_loaded} patterns loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

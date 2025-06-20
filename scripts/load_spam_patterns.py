#!/usr/bin/env python
"""
Load spam detection patterns from knowledge base into semantic memory.

This script reads spam patterns from knowledge/spam_patterns.json and
loads them into the semantic memory system for use by the spam detector.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence
from src.utils.logging_system import get_logger, log_function
from src.utils.config import config

logger = get_logger(__name__)


@log_function()
async def load_spam_patterns_to_memory(
    patterns_file: Path, memory: SemanticMemory
) -> int:
    """
    Load spam patterns from JSON file into semantic memory.

    Args:
        patterns_file: Path to the JSON file containing spam patterns
        memory: SemanticMemory instance to load patterns into

    Returns:
        Number of patterns loaded
    """
    logger.info(f"Loading spam patterns from: {patterns_file}")

    with open(patterns_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    patterns_loaded = 0

    # Load spam words
    if "spam_patterns" in data and "spam_words" in data["spam_patterns"]:
        spam_words = data["spam_patterns"]["spam_words"]
        weight = spam_words.get("confidence_weight", 2.0)

        for pattern in spam_words.get("patterns", []):
            content = {
                "type": "spam_pattern",
                "pattern_type": "keyword",
                "word": pattern["word"],
                "confidence": pattern["confidence"],
                "category": pattern.get("category", "spam"),
                "weight": weight,
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Spam keyword pattern: {pattern['word']}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.8
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Load regex patterns
    for pattern_type in ["suspicious_regex_patterns", "phishing_patterns"]:
        if pattern_type in data["spam_patterns"]:
            patterns_data = data["spam_patterns"][pattern_type]
            weight = patterns_data.get("confidence_weight", 1.5)

            for pattern in patterns_data.get("patterns", []):
                content = {
                    "type": "spam_pattern",
                    "pattern_type": "regex",
                    "regex": pattern.get("regex", pattern.get("word", "")),
                    "description": pattern.get("description", ""),
                    "confidence": pattern["confidence"],
                    "category": pattern.get("category", "suspicious"),
                    "weight": weight,
                    "source": "knowledge_base",
                }

                # Create a safe key from the pattern
                regex_key = pattern.get("regex", pattern.get("word", ""))
                description = pattern.get("description", regex_key)

                await memory.add(
                    content=f"Spam regex pattern: {description}",
                    metadata=content,
                    knowledge_type=KnowledgeType.PATTERN,
                    confidence=(
                        KnowledgeConfidence.HIGH
                        if pattern["confidence"] > 0.8
                        else KnowledgeConfidence.MEDIUM
                    ),
                )
                patterns_loaded += 1

    # Load blacklists
    for blacklist_type in ["blacklists", "domain_blacklists"]:
        if blacklist_type in data["spam_patterns"]:
            blacklist_data = data["spam_patterns"][blacklist_type]

            for pattern in blacklist_data.get("patterns", []):
                content = {
                    "type": "spam_pattern",
                    "pattern_type": "blacklist",
                    "server": pattern["server"],
                    "blacklist_type": pattern.get("type", "unknown"),
                    "weight": pattern.get("weight", 0.8),
                    "description": pattern.get("description", ""),
                    "source": "knowledge_base",
                }

                await memory.add(
                    content=f"Spam blacklist server: {pattern['server']} - {pattern.get('description', '')}",
                    metadata=content,
                    knowledge_type=KnowledgeType.PATTERN,
                    confidence=KnowledgeConfidence.HIGH,
                )
                patterns_loaded += 1

    # Load suspicious TLDs
    if "suspicious_tlds" in data["spam_patterns"]:
        tld_data = data["spam_patterns"]["suspicious_tlds"]

        for pattern in tld_data.get("patterns", []):
            content = {
                "type": "spam_pattern",
                "pattern_type": "tld",
                "tld": pattern["tld"],
                "confidence": pattern["confidence"],
                "description": pattern.get("description", ""),
                "source": "knowledge_base",
            }

            await memory.add(
                content=f"Suspicious TLD: {pattern['tld']} - {pattern.get('description', '')}",
                metadata=content,
                knowledge_type=KnowledgeType.PATTERN,
                confidence=(
                    KnowledgeConfidence.HIGH
                    if pattern["confidence"] > 0.7
                    else KnowledgeConfidence.MEDIUM
                ),
            )
            patterns_loaded += 1

    # Store learning configuration
    if "learning_configuration" in data:
        await memory.add(
            content="Spam detection learning configuration",
            metadata={
                "type": "configuration",
                "config_type": "spam_learning",
                "configuration": data["learning_configuration"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.PROCESS,
            confidence=KnowledgeConfidence.HIGH,
        )
        patterns_loaded += 1

    logger.info(f"Successfully loaded {patterns_loaded} spam patterns into memory")
    return patterns_loaded


@log_function()
async def verify_patterns_loaded(memory: SemanticMemory) -> None:
    """
    Verify that spam patterns were loaded correctly.

    Args:
        memory: SemanticMemory instance to check
    """
    logger.info("Verifying loaded spam patterns...")

    # Test search for different pattern types
    test_searches = [
        ("spam patterns", 10),
        ("phishing", 5),
        ("blacklist", 5),
        ("urgent free money", 5),
    ]

    for query, limit in test_searches:
        results = await memory.search(
            query, limit=limit, knowledge_type=KnowledgeType.PATTERN
        )
        logger.info(f"Search '{query}' returned {len(results)} results")

        for i, result in enumerate(results[:3]):
            logger.info(f"  Result {i+1}: {result.content[:50]}...")


async def main():
    """Main function to load spam patterns."""
    patterns_file = Path("knowledge/spam_patterns.json")

    if not patterns_file.exists():
        logger.error(f"Patterns file not found: {patterns_file}")
        return 1

    # Initialize semantic memory
    memory = SemanticMemory()

    # Load patterns
    patterns_loaded = await load_spam_patterns_to_memory(patterns_file, memory)

    # Verify loading
    await verify_patterns_loaded(memory)

    logger.info(f"Spam pattern loading complete. {patterns_loaded} patterns loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

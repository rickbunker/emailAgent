#!/usr/bin/env python
"""
Load all knowledge base patterns into semantic memory.

This script loads all pattern files from the knowledge directory into
the semantic memory system. It's a convenience script that runs all
individual pattern loaders.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.semantic import SemanticMemory
from src.utils.logging_system import get_logger, log_function

# Import individual loaders
from load_spam_patterns import load_spam_patterns_to_memory
from load_contact_patterns import load_contact_patterns_to_memory
from load_asset_types import load_asset_types_to_memory

logger = get_logger(__name__)


@log_function()
async def load_all_patterns() -> Tuple[int, List[str]]:
    """
    Load all pattern files into semantic memory.

    Returns:
        Tuple of (total_items_loaded, list_of_errors)
    """
    logger.info("Starting to load all knowledge base patterns...")

    # Initialize semantic memory
    memory = SemanticMemory()

    total_loaded = 0
    errors: List[str] = []

    # Define pattern files and their loaders
    pattern_loaders = [
        ("knowledge/spam_patterns.json", load_spam_patterns_to_memory, "spam patterns"),
        (
            "knowledge/contact_patterns.json",
            load_contact_patterns_to_memory,
            "contact patterns",
        ),
        ("knowledge/asset_types.json", load_asset_types_to_memory, "asset types"),
    ]

    for pattern_file, loader_func, description in pattern_loaders:
        pattern_path = Path(pattern_file)

        if not pattern_path.exists():
            error_msg = f"Pattern file not found: {pattern_file}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue

        try:
            logger.info(f"Loading {description} from {pattern_file}...")
            items_loaded = await loader_func(pattern_path, memory)
            total_loaded += items_loaded
            logger.info(f"Successfully loaded {items_loaded} {description}")

        except Exception as e:
            error_msg = f"Failed to load {description}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return total_loaded, errors


@log_function()
async def verify_all_patterns_loaded(memory: SemanticMemory) -> None:
    """
    Verify that all pattern types were loaded correctly.

    Args:
        memory: SemanticMemory instance to check
    """
    logger.info("Verifying all loaded patterns...")

    # Test searches across all pattern types
    test_searches = [
        # Spam patterns
        ("spam pattern", 5),
        ("phishing", 3),
        # Contact patterns
        ("contact pattern", 5),
        ("no-reply", 3),
        # Asset types
        ("asset type", 5),
        ("document category", 5),
        ("file validation", 3),
    ]

    for query, limit in test_searches:
        results = await memory.search(query, limit=limit)
        logger.info(f"Search '{query}' returned {len(results)} results")


async def main():
    """Main function to load all patterns."""
    logger.info("=" * 60)
    logger.info("Knowledge Base Pattern Loader")
    logger.info("=" * 60)

    # Load all patterns
    total_loaded, errors = await load_all_patterns()

    # Initialize memory for verification
    memory = SemanticMemory()

    # Verify loading
    await verify_all_patterns_loaded(memory)

    # Report results
    logger.info("=" * 60)
    logger.info(f"Pattern loading complete!")
    logger.info(f"Total items loaded: {total_loaded}")

    if errors:
        logger.error(f"Errors encountered: {len(errors)}")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    else:
        logger.info("All patterns loaded successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

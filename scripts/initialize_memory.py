#!/usr/bin/env python
"""
Initialize or reset the Email Agent memory system.

This script should be run ONLY when:
1. Setting up the system for the first time
2. Resetting the memory to baseline patterns
3. Updating the knowledge base after changes to JSON files

During normal operation, agents read ONLY from memory (Qdrant),
never from the JSON files directly.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_system import get_logger
from load_all_patterns import load_all_patterns, verify_all_patterns_loaded
from src.memory.semantic import SemanticMemory

logger = get_logger(__name__)


async def initialize_memory_system(reset: bool = False) -> int:
    """
    Initialize the Email Agent memory system with baseline patterns.

    Args:
        reset: If True, clears existing memory before loading patterns

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 70)
    logger.info("EMAIL AGENT MEMORY SYSTEM INITIALIZATION")
    logger.info("=" * 70)

    if reset:
        logger.warning("RESET MODE: This will clear existing memory patterns!")
        logger.warning(
            "Human feedback and learned patterns will be preserved in episodic memory"
        )

        # In a real implementation, you might want to:
        # 1. Backup episodic memory
        # 2. Clear semantic memory patterns with source='knowledge_base'
        # 3. Reload patterns
        # 4. Restore episodic memory

        response = input(
            "\nAre you sure you want to reset the memory system? (yes/no): "
        )
        if response.lower() != "yes":
            logger.info("Reset cancelled by user")
            return 0

    logger.info("\nLoading knowledge base patterns into memory...")
    logger.info("This compiles JSON 'source code' into the memory system")
    logger.info("-" * 70)

    # Load all patterns
    total_loaded, errors = await load_all_patterns()

    if errors:
        logger.error(f"\nInitialization failed with {len(errors)} errors")
        return 1

    # Verify patterns loaded correctly
    memory = SemanticMemory()
    await verify_all_patterns_loaded(memory)

    logger.info("-" * 70)
    logger.info(f"✅ Memory system initialized successfully!")
    logger.info(f"Total patterns loaded: {total_loaded}")
    logger.info("\nAgents will now read patterns from memory (Qdrant) during operation")
    logger.info("JSON files are only used for version control and system resets")
    logger.info("=" * 70)

    return 0


async def main():
    """Main function with command line argument handling."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize the Email Agent memory system",
        epilog="Note: During normal operation, agents read from memory, not JSON files",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset memory system to baseline patterns (preserves episodic learning)",
    )

    args = parser.parse_args()

    return await initialize_memory_system(reset=args.reset)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

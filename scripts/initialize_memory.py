#!/usr/bin/env python
"""
Initialize or reset the Email Agent memory system.

⚠️  WARNING: This script is NOT part of normal application startup!

This script should be run ONLY when:
1. Setting up the system for the first time
2. Resetting memory for testing environments
3. Updating the knowledge base after changes to JSON files
4. Emergency recovery from corrupted memory

In production, memory persists across application restarts and continuously
learns from human feedback. Running this script will reset patterns to
baseline versions and lose learned optimizations.

During normal operation, agents read ONLY from persistent memory (Qdrant),
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

    ⚠️  WARNING: This is NOT part of normal application startup!

    This operation resets patterns to baseline versions. In production,
    this means losing learned optimizations and pattern effectiveness
    improvements gained through human feedback over time.

    Args:
        reset: If True, clears existing memory before loading patterns

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 70)
    logger.info("EMAIL AGENT MEMORY SYSTEM INITIALIZATION")
    logger.info("=" * 70)
    logger.warning("⚠️  This is NOT part of normal application startup!")
    logger.warning("⚠️  This resets patterns to baseline versions!")

    if reset:
        logger.error("🚨 RESET MODE: This will clear existing memory patterns!")
        logger.error("🚨 Learned optimizations and effectiveness scores will be LOST!")
        logger.warning("Human feedback in episodic memory will be preserved")

        print("\n" + "=" * 50)
        print("🚨 DANGER: MEMORY RESET OPERATION")
        print("=" * 50)
        print("This will:")
        print("- Reset all patterns to baseline JSON versions")
        print("- Lose learned pattern effectiveness improvements")
        print("- Require the system to re-learn optimizations")
        print("- Preserve human feedback in episodic memory")
        print("=" * 50)

        response = input("\nType 'RESET' to confirm this destructive operation: ")
        if response != "RESET":
            logger.info("Reset cancelled - memory preserved")
            return 0
    else:
        print("\n" + "=" * 50)
        print("⚠️  MEMORY INITIALIZATION")
        print("=" * 50)
        print("This will load baseline patterns into memory.")
        print("Only proceed if:")
        print("- This is initial system setup")
        print("- You're setting up a test environment")
        print("- You've updated JSON pattern files")
        print("=" * 50)

        response = input("\nProceed with memory initialization? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Initialization cancelled")
            return 0

    logger.info("\nLoading knowledge base patterns into memory...")
    logger.info("Compiling JSON 'source code' into the memory system...")
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
    logger.info("\n📋 Next steps:")
    logger.info("1. Start the application normally")
    logger.info("2. Agents will read patterns from memory (Qdrant)")
    logger.info("3. System will learn and improve from human feedback")
    logger.info("4. Memory will persist across application restarts")
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

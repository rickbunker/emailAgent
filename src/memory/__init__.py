"""
Simplified Memory System for Email Agent

Uses JSON files and SQLite for storage instead of Qdrant vector database.
This provides a much simpler development and testing experience while maintaining
the same interface as the full vector-based system.

Memory Types:
- Semantic Memory: Asset profiles, keywords, patterns (JSON files)
- Procedural Memory: Business rules and procedures (JSON files)
- Episodic Memory: Processing history and feedback (SQLite database)
- Contact Memory: Sender mappings and relationships (JSON files)
"""

# # Standard library imports
from typing import Any

# # Local application imports
from src.utils.config import config  # noqa: E402
from src.utils.logging_system import get_logger  # noqa: E402

logger = get_logger(__name__)

# Import the simplified memory implementations
from .simple_memory import (  # noqa: E402
    SimpleEpisodicMemory,
    SimpleProceduralMemory,
    SimpleSemanticMemory,
)

__all__ = [
    "SimpleSemanticMemory",
    "SimpleProceduralMemory",
    "SimpleEpisodicMemory",
    "create_memory_systems",
]


def create_memory_systems() -> dict[str, Any]:
    """
    Create all memory systems using JSON/SQLite storage.

    Returns:
        Dictionary with all memory system instances
    """
    logger.info("🧠 Creating simplified memory systems (JSON/SQLite)")

    try:
        memory_systems = {
            "semantic": SimpleSemanticMemory(),  # Now includes contact data
            "procedural": SimpleProceduralMemory(),
            "episodic": SimpleEpisodicMemory(),
        }

        logger.info("✅ All memory systems created successfully")
        return memory_systems

    except Exception as e:
        logger.error(f"❌ Failed to create memory systems: {e}")
        raise

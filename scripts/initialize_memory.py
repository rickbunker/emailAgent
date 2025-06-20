#!/usr/bin/env python3
"""
Initialize memory systems and load knowledge base data.

This script properly initializes all four memory systems and loads
the knowledge base data according to the architecture design.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set cache directory for sentence transformers BEFORE importing
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
    Path.home() / ".cache" / "sentence_transformers"
)
os.environ["TRANSFORMERS_CACHE"] = str(Path.home() / ".cache" / "huggingface")
os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

from qdrant_client import QdrantClient
from src.utils.config import config, PROJECT_ROOT
from src.utils.logging_system import get_logger
from src.memory.semantic import SemanticMemory
from src.memory.episodic import EpisodicMemory
from src.memory.procedural import ProceduralMemory
from src.memory.contact import ContactMemory
from src.asset_management.services.asset_service import AssetService

logger = get_logger(__name__)


async def ensure_embedding_model():
    """Ensure the embedding model is available locally."""
    from sentence_transformers import SentenceTransformer

    cache_dir = Path.home() / ".cache" / "sentence_transformers"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Try to load from cache first
        model = SentenceTransformer(config.embedding_model, cache_folder=str(cache_dir))
        logger.info(f"✅ Embedding model '{config.embedding_model}' loaded from cache")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Could not load embedding model: {e}")

        # Offer alternative solutions
        logger.info("\n" + "=" * 60)
        logger.info("EMBEDDING MODEL OPTIONS:")
        logger.info("1. Download the model manually:")
        logger.info(
            f"   git clone https://huggingface.co/sentence-transformers/{config.embedding_model} {cache_dir}/{config.embedding_model}"
        )
        logger.info("\n2. Use OpenAI embeddings instead:")
        logger.info("   Set OPENAI_API_KEY environment variable and update config")
        logger.info("\n3. Use a different local model:")
        logger.info("   Update config.embedding_model to a model you have locally")
        logger.info("=" * 60 + "\n")

        return False


async def load_into_semantic_memory(semantic_memory: SemanticMemory) -> int:
    """Load knowledge base data into semantic memory."""
    items_loaded = 0

    # Load asset data
    asset_file = PROJECT_ROOT / "knowledge" / "asset_data.json"
    if asset_file.exists():
        with open(asset_file) as f:
            data = json.load(f)

        for asset in data.get("assets", []):
            try:
                # Add asset knowledge
                await semantic_memory.add_asset_knowledge(
                    asset_id=asset["asset_id"],
                    deal_name=asset["deal_name"],
                    asset_name=asset["asset_name"],
                    asset_type=asset["asset_type"],
                    identifiers=asset.get("identifiers", []),
                    business_context=asset.get("business_context", {}),
                )
                items_loaded += 1
                logger.info(f"Loaded asset: {asset['deal_name']}")
            except Exception as e:
                logger.error(f"Failed to load asset {asset.get('deal_name')}: {e}")

    # Load asset types
    types_file = PROJECT_ROOT / "knowledge" / "asset_types.json"
    if types_file.exists():
        with open(types_file) as f:
            data = json.load(f)

        # Load asset type definitions
        for asset_type in data.get("asset_types", {}).get("types", []):
            content = f"Asset Type: {asset_type['display_name']}\n"
            content += f"Description: {asset_type['description']}\n"
            content += (
                f"Identifiers: {', '.join(asset_type.get('common_identifiers', []))}"
            )

            await semantic_memory.add(
                content=content,
                metadata={
                    "type": "asset_type_definition",
                    "type_id": asset_type["type_id"],
                    "source": "knowledge_base",
                },
            )
            items_loaded += 1

    logger.info(f"✅ Loaded {items_loaded} items into semantic memory")
    return items_loaded


async def initialize_procedural_memory(qdrant_client: QdrantClient) -> ProceduralMemory:
    """Initialize procedural memory with business rules."""
    procedural_memory = ProceduralMemory(qdrant_client=qdrant_client)

    # Initialize collections
    await procedural_memory.initialize_collections()

    # Seed from knowledge base (includes business rules)
    knowledge_path = str(PROJECT_ROOT / "knowledge")
    stats = await procedural_memory.seed_from_knowledge_base(knowledge_path)

    logger.info(
        f"✅ Procedural memory initialized with {stats.get('total_patterns', 0)} patterns"
    )
    return procedural_memory


async def main():
    """Initialize all memory systems and load knowledge base."""
    logger.info("🚀 Memory System Initialization")
    logger.info("=" * 60)

    # Check embedding model availability first
    if not await ensure_embedding_model():
        logger.error("❌ Cannot proceed without embedding model")
        return 1

    # Initialize Qdrant client
    qdrant_url = f"http://{config.qdrant_host}:{config.qdrant_port}"
    qdrant_client = QdrantClient(url=qdrant_url)
    logger.info(f"✅ Connected to Qdrant at {qdrant_url}")

    try:
        # Initialize memory systems
        logger.info("\n📦 Initializing Memory Systems...")

        # Semantic Memory - Knowledge and human feedback
        semantic_memory = SemanticMemory(
            max_items=config.semantic_memory_max_items,
            qdrant_url=qdrant_url,
            embedding_model=config.embedding_model,
        )
        logger.info(f"✅ Semantic Memory: {config.semantic_memory_max_items} max items")

        # Procedural Memory - Business rules and procedures
        procedural_memory = await initialize_procedural_memory(qdrant_client)
        logger.info(
            f"✅ Procedural Memory: {config.procedural_memory_max_items} max items"
        )

        # Episodic Memory - Experience history
        episodic_memory = EpisodicMemory(
            max_items=config.episodic_memory_max_items,
            qdrant_url=qdrant_url,
            embedding_model=config.embedding_model,
        )
        logger.info(f"✅ Episodic Memory: {config.episodic_memory_max_items} max items")

        # Contact Memory - Sender relationships
        contact_memory = ContactMemory(
            max_items=config.contact_memory_max_items,
            qdrant_url=qdrant_url,
            embedding_model=config.embedding_model,
        )
        logger.info(f"✅ Contact Memory: {config.contact_memory_max_items} max items")

        # Load knowledge base data
        logger.info("\n📚 Loading Knowledge Base...")

        # Load into semantic memory
        semantic_items = await load_into_semantic_memory(semantic_memory)

        # Initialize asset service
        asset_service = AssetService()
        await asset_service.initialize_collection()
        logger.info("✅ Asset service initialized")

        # Show summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 INITIALIZATION SUMMARY")
        logger.info("=" * 60)

        # Get collection info
        semantic_info = await semantic_memory.get_collection_info()
        episodic_info = await episodic_memory.get_collection_info()
        procedural_stats = await procedural_memory.get_pattern_stats()
        contact_info = await contact_memory.get_collection_info()

        logger.info(f"Semantic Memory: {semantic_info.get('points_count', 0)} items")
        logger.info(
            f"Procedural Memory: {procedural_stats.get('total_patterns', 0)} patterns"
        )
        logger.info(f"Episodic Memory: {episodic_info.get('points_count', 0)} items")
        logger.info(f"Contact Memory: {contact_info.get('points_count', 0)} items")

        logger.info("\n✅ Memory systems initialized and ready!")
        logger.info("\nYou can now:")
        logger.info("1. Start the API server: python -m src.web_api.main")
        logger.info("2. Access the web UI at: http://localhost:8000")
        logger.info("3. View memory dashboard at: http://localhost:8000/memory")

        return 0

    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

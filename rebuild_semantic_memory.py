#!/usr/bin/env python3
"""Clear semantic memory and rebuild from clean knowledge base."""

import asyncio
from src.utils.config import config
from qdrant_client import QdrantClient
from src.memory.semantic import SemanticMemory


async def rebuild_semantic_memory():
    """Clear semantic memory and rebuild from knowledge base."""
    print("Rebuilding Semantic Memory from Clean Knowledge Base")
    print("=" * 60)

    # Initialize Qdrant client and semantic memory
    qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
    semantic_memory = SemanticMemory(qdrant_client)

    try:
        # Step 1: Clear existing semantic memory
        print("Step 1: Clearing existing semantic memory...")
        await semantic_memory.clear()
        print("✅ Semantic memory cleared")

        # Step 2: Reload from knowledge base
        print("\nStep 2: Reloading from clean knowledge base...")
        results = await semantic_memory.load_knowledge_base("knowledge")

        print("✅ Knowledge base loaded successfully!")
        print(f"   File types loaded: {results.get('file_types_loaded', 0)}")
        print(f"   Total knowledge items: {results.get('total_knowledge_items', 0)}")
        print(f"   Assets loaded: {results.get('assets_loaded', 0)}")

        if results.get("errors"):
            print(f"⚠️  Errors during loading: {results['errors']}")

        # Step 3: Verify the rebuild
        print("\nStep 3: Verifying semantic memory...")

        # Check for test-asset-123 (should be none)
        test_search = await semantic_memory.search("test-asset-123", limit=5)
        if test_search:
            print(f"❌ ERROR: Still found {len(test_search)} test-asset-123 entries!")
            for item in test_search:
                print(f"   - {item.content[:100]}...")
        else:
            print("✅ No test-asset-123 entries found")

        # Check for legitimate assets
        asset_search = await semantic_memory.search("Asset:", limit=10)
        print(f"✅ Found {len(asset_search)} legitimate asset entries:")
        for i, item in enumerate(asset_search[:4]):
            content = item.content
            if "Asset:" in content:
                asset_line = content.split("\n")[0]  # First line usually has asset info
                print(f"   {i+1}. {asset_line}")

        print("\n" + "=" * 60)
        print("🎉 Semantic memory successfully rebuilt from clean knowledge base!")
        print("The PNG file matching issue should now be resolved.")

    except Exception as e:
        print(f"❌ Error rebuilding semantic memory: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(rebuild_semantic_memory())

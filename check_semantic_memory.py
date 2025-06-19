#!/usr/bin/env python3
"""Check semantic memory for asset information."""

import asyncio
from src.utils.config import config
from qdrant_client import QdrantClient


async def check_semantic_memory():
    """Check semantic memory for assets."""
    # Initialize Qdrant client
    qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)

    print("Checking semantic memory for asset information...")
    print("=" * 60)

    # Check semantic collection
    collection_name = "semantic"

    try:
        # Query the collection
        search_result = qdrant_client.scroll(
            collection_name=collection_name,
            limit=50,  # Get first 50 items
            with_payload=True,
            with_vectors=False,
        )
        facts = search_result[0]
        print(f"Found {len(facts)} facts in semantic memory")
        print()

        # Look for any fact containing test-asset-123
        test_asset_facts = []
        all_facts_preview = []

        for fact in facts:
            payload = fact.payload
            content_str = str(payload).lower()

            # Check for test-asset-123 anywhere
            if "test-asset-123" in content_str:
                test_asset_facts.append(
                    {
                        "id": fact.id,
                        "content": payload.get("content", ""),
                        "knowledge_type": payload.get("knowledge_type", ""),
                        "metadata": payload,
                    }
                )

            # Also collect preview of all facts for inspection
            all_facts_preview.append(
                {
                    "id": fact.id,
                    "content": payload.get("content", "")[:100] + "...",
                    "knowledge_type": payload.get("knowledge_type", ""),
                }
            )

        print(f"Found {len(test_asset_facts)} facts containing test-asset-123:")
        print("-" * 40)

        if test_asset_facts:
            for i, fact in enumerate(test_asset_facts):
                print(f'{i+1}. ID: {fact["id"]}')
                print(f'   Knowledge Type: {fact["knowledge_type"]}')
                print(f'   Content: {fact["content"]}')
                print(f'   Full metadata: {fact["metadata"]}')
                print()
        else:
            print("No facts found with test-asset-123")
            print("\nFirst 10 facts in semantic memory for reference:")
            for i, fact in enumerate(all_facts_preview[:10]):
                print(f'{i+1}. {fact["knowledge_type"]}: {fact["content"]}')

    except Exception as e:
        print(f"Error checking semantic memory: {e}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_semantic_memory())

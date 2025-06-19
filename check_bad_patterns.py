#!/usr/bin/env python3
"""Check for bad asset matching patterns in procedural memory."""

import asyncio
from src.memory.procedural import ProceduralMemory
from src.utils.config import config
from qdrant_client import QdrantClient


async def check_bad_patterns():
    """Check for bad asset matching patterns."""
    # Initialize Qdrant client
    qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
    pm = ProceduralMemory(qdrant_client)

    print("Checking for bad asset matching patterns...")
    print("=" * 60)

    # Check both asset patterns and classification patterns
    collections_to_check = [
        "procedural_asset_patterns",
        "procedural_classification_patterns",
        "procedural_confidence_models",
    ]

    search_terms = ["test-asset-123", "display", "png", "fix"]
    all_bad_patterns = []

    for collection_name in collections_to_check:
        try:
            # Query each collection
            search_result = qdrant_client.scroll(
                collection_name=collection_name,
                limit=100,  # Get up to 100 patterns
                with_payload=True,
                with_vectors=False,
            )
            patterns = search_result[0]  # First element is the list of points
            print(f"Found {len(patterns)} patterns in {collection_name}")

            # Look for problematic patterns
            for pattern in patterns:
                payload = pattern.payload
                payload_str = str(payload).lower()

                # Check if any search terms appear in the pattern
                for term in search_terms:
                    if term in payload_str:
                        all_bad_patterns.append(
                            {
                                "collection": collection_name,
                                "id": pattern.id,
                                "payload": payload,
                                "matched_term": term,
                            }
                        )
                        break

        except Exception as e:
            print(f"Error checking {collection_name}: {e}")
            continue

    print(
        f"\nFound {len(all_bad_patterns)} potentially bad patterns across all collections:"
    )
    print("-" * 60)

    # Display results
    for i, pattern in enumerate(all_bad_patterns[:10]):  # Show first 10
        print(f'{i+1}. Collection: {pattern["collection"]}')
        print(f'   ID: {pattern["id"]}')
        print(f'   Matched term: {pattern["matched_term"]}')
        print(f'   Asset ID: {pattern["payload"].get("asset_id", "N/A")}')
        print(f'   Keywords: {pattern["payload"].get("keywords", [])}')
        print(f'   Confidence: {pattern["payload"].get("confidence", "N/A")}')
        print(f'   Content preview: {str(pattern["payload"])[:150]}...')
        print()

    if len(all_bad_patterns) > 10:
        print(f"... and {len(all_bad_patterns) - 10} more patterns")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_bad_patterns())

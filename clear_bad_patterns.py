#!/usr/bin/env python3
"""Clear bad patterns from procedural memory."""

import asyncio
from src.utils.config import config
from qdrant_client import QdrantClient


async def clear_bad_patterns():
    """Clear bad patterns that incorrectly match PNG files to assets."""
    # Initialize Qdrant client
    qdrant_client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)

    print("Clearing bad patterns from procedural memory...")
    print("=" * 60)

    # Focus on procedural_confidence_models where the bad patterns are
    collection_name = "procedural_confidence_models"
    search_terms = ["png", "display", "fix"]  # Problematic terms
    patterns_to_delete = []

    try:
        # Query the collection
        search_result = qdrant_client.scroll(
            collection_name=collection_name,
            limit=200,  # Get all patterns
            with_payload=True,
            with_vectors=False,
        )
        patterns = search_result[0]
        print(f"Found {len(patterns)} patterns in {collection_name}")

        # Find patterns to delete
        for pattern in patterns:
            payload = pattern.payload
            payload_str = str(payload).lower()

            # Check if any search terms appear AND it's not a legitimate knowledge base pattern
            for term in search_terms:
                if term in payload_str:
                    # Check if it's NOT from knowledge base (those are legitimate)
                    source = payload.get("source", "")
                    if "knowledge_base" not in source.lower():
                        patterns_to_delete.append(
                            {"id": pattern.id, "payload": payload, "matched_term": term}
                        )
                        break

        print(f"\nFound {len(patterns_to_delete)} bad patterns to delete:")
        print("-" * 40)

        # Show what we're deleting
        for i, pattern in enumerate(patterns_to_delete[:5]):  # Show first 5
            print(f'{i+1}. ID: {pattern["id"]}')
            print(f'   Matched term: {pattern["matched_term"]}')
            print(f'   Source: {pattern["payload"].get("source", "N/A")}')
            print(f'   Created: {pattern["payload"].get("created_date", "N/A")}')
            print(f'   Content preview: {str(pattern["payload"])[:100]}...')
            print()

        if len(patterns_to_delete) > 5:
            print(f"... and {len(patterns_to_delete) - 5} more patterns\n")

        # Confirm deletion
        if patterns_to_delete:
            confirm = input(f"Delete {len(patterns_to_delete)} bad patterns? (y/N): ")
            if confirm.lower() == "y":
                # Delete the patterns
                pattern_ids = [p["id"] for p in patterns_to_delete]
                qdrant_client.delete(
                    collection_name=collection_name, points_selector=pattern_ids
                )
                print(f"✅ Deleted {len(patterns_to_delete)} bad patterns!")
            else:
                print("❌ Deletion cancelled.")
        else:
            print("✅ No bad patterns found to delete.")

    except Exception as e:
        print(f"Error clearing bad patterns: {e}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(clear_bad_patterns())

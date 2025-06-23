#!/usr/bin/env python3
"""
Clean up unnecessary Qdrant collections.
"""

# # Standard library imports

# # Third-party imports
from qdrant_client import QdrantClient


def cleanup_collections():
    """Remove unnecessary collections from Qdrant."""
    client = QdrantClient(url="http://localhost:6333")

    # Get all collections
    collections = client.get_collections()
    existing_names = [c.name for c in collections.collections]

    print("Current collections:")
    for name in existing_names:
        print(f"  - {name}")

    # Collections to remove
    unnecessary_collections = [
        # From simple_load_knowledge.py script
        "knowledge_asset_data",
        "knowledge_asset_types",
        "knowledge_business_rules",
        "knowledge_contact_patterns",
        "knowledge_spam_patterns",
        # Wrong name
        "contacts",  # Should be "contact" without 's'
    ]

    # Collections to keep (for reference)
    needed_collections = [
        "semantic",  # SemanticMemory
        "episodic",  # EpisodicMemory
        "contact",  # ContactMemory (note: no 's')
        "procedural_classification_patterns",  # ProceduralMemory
        "procedural_asset_patterns",  # ProceduralMemory
        "procedural_configuration_rules",  # ProceduralMemory
        "procedural_confidence_models",  # ProceduralMemory
        "assets",  # Asset service
        "photos",  # Keep this one
    ]

    print(f"\nCollections to remove: {len(unnecessary_collections)}")
    for name in unnecessary_collections:
        if name in existing_names:
            print(f"  - {name}")

    response = input("\nProceed with cleanup? (yes/no): ")
    if response.lower() != "yes":
        print("Cleanup cancelled")
        return

    # Delete unnecessary collections
    deleted = 0
    for collection_name in unnecessary_collections:
        if collection_name in existing_names:
            try:
                client.delete_collection(collection_name)
                print(f"✅ Deleted: {collection_name}")
                deleted += 1
            except Exception as e:
                print(f"❌ Failed to delete {collection_name}: {e}")

    print(f"\n✅ Cleanup complete! Deleted {deleted} collections")

    # Show remaining collections
    collections = client.get_collections()
    remaining_names = [c.name for c in collections.collections]
    print("\nRemaining collections:")
    for name in remaining_names:
        status = "✅" if name in needed_collections else "❓"
        print(f"  {status} {name}")

    # Note if contact collection is missing
    if "contact" not in remaining_names:
        print(
            "\n⚠️  Note: 'contact' collection is missing. ContactMemory will create it when initialized."
        )


if __name__ == "__main__":
    cleanup_collections()

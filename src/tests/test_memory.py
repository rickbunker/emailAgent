import asyncio
import time
from typing import List
import pytest
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory

@pytest.mark.asyncio
async def test_procedural_memory():
    """Test procedural memory for rules and procedures."""
    memory = ProceduralMemory(max_items=100)
    await memory.clear_collection(force_delete=True)  # Clean start
    
    # Add some rules
    rule1_id = await memory.add(
        "Always respond to urgent emails within 1 hour",
        metadata={"priority": "high", "category": "response_time"}
    )
    
    rule2_id = await memory.add(
        "Archive emails older than 30 days",
        metadata={"priority": "medium", "category": "maintenance"}
    )
    
    # Test retrieval
    rule1 = await memory.get(rule1_id)
    assert rule1 is not None
    assert "urgent" in rule1.content.lower()
    assert rule1.metadata["priority"] == "high"
    
    # Test search
    results = await memory.search(
        "urgent email response",
        limit=5
    )
    assert len(results) > 0
    assert any("urgent" in r.content.lower() for r in results)
    
    # Test update
    success = await memory.update(
        rule1_id,
        "Always respond to urgent emails within 30 minutes",
        metadata={"priority": "critical", "category": "response_time"}
    )
    assert success
    
    updated_rule = await memory.get(rule1_id)
    assert "30 minutes" in updated_rule.content
    assert updated_rule.metadata["priority"] == "critical"
    
    # Test delete
    success = await memory.delete(rule2_id)
    assert success
    deleted_rule = await memory.get(rule2_id)
    assert deleted_rule is None

@pytest.mark.asyncio
async def test_semantic_memory():
    """Test semantic memory for sender and email type knowledge."""
    memory = SemanticMemory(max_items=100)
    await memory.clear_collection(force_delete=True)  # Clean start
    
    # Add knowledge about senders
    sender1_id = await memory.add(
        "John Smith frequently sends project updates on Mondays",
        metadata={
            "sender": "john.smith@example.com",
            "email_type": "project_update",
            "frequency": "weekly"
        }
    )
    
    sender2_id = await memory.add(
        "Sarah Johnson sends monthly reports with budget information",
        metadata={
            "sender": "sarah.j@example.com",
            "email_type": "report",
            "frequency": "monthly"
        }
    )
    
    # Test vector search
    results = await memory.search(
        "project updates",
        limit=5
    )
    assert len(results) > 0
    assert any("project" in r.content.lower() for r in results)
    
    # Test search with filter
    results = await memory.search(
        "reports",
        filter={
            "must": [
                {
                    "key": "metadata.email_type",
                    "match": {"value": "report"}
                }
            ]
        }
    )
    assert len(results) > 0
    assert all(r.metadata["email_type"] == "report" for r in results)

@pytest.mark.asyncio
async def test_episodic_memory():
    """Test episodic memory for conversation history and feedback."""
    memory = EpisodicMemory(max_items=100)
    await memory.clear_collection(force_delete=True)  # Clean start
    
    # Add conversation history
    conv1_id = await memory.add(
        "User asked about email categorization rules",
        metadata={
            "conversation_id": "conv_001",
            "type": "user_query",
            "timestamp": time.time() - 3600  # 1 hour ago
        }
    )
    
    conv2_id = await memory.add(
        "System provided explanation of categorization rules",
        metadata={
            "conversation_id": "conv_001",
            "type": "system_response",
            "timestamp": time.time() - 3500  # 58 minutes ago
        }
    )
    
    # Test time-based search
    results = await memory.search(
        "categorization rules",
        filter={
            "must": [
                {
                    "key": "metadata.timestamp",
                    "range": {
                        "gte": time.time() - 7200,  # 2 hours ago
                        "lte": time.time()
                    }
                }
            ]
        }
    )
    assert len(results) > 0
    
    # Test conversation-based search
    results = await memory.search(
        "categorization",
        filter={
            "must": [
                {
                    "key": "metadata.conversation_id",
                    "match": {"value": "conv_001"}
                }
            ]
        }
    )
    assert len(results) == 2  # Both parts of the conversation
    
    # Test type-based search
    results = await memory.search(
        "rules",
        filter={
            "must": [
                {
                    "key": "metadata.type",
                    "match": {"value": "user_query"}
                }
            ]
        }
    )
    assert len(results) > 0
    assert all(r.metadata["type"] == "user_query" for r in results)

@pytest.mark.asyncio
async def test_memory_interaction():
    """Test interaction between different memory types."""
    procedural = ProceduralMemory(max_items=100)
    semantic = SemanticMemory(max_items=100)
    episodic = EpisodicMemory(max_items=100)
    
    # Clean start for all memory types
    await procedural.clear_collection(force_delete=True)
    await semantic.clear_collection(force_delete=True)
    await episodic.clear_collection(force_delete=True)
    
    # Add a rule
    rule_id = await procedural.add(
        "Always prioritize emails from the CEO",
        metadata={"priority": "high", "category": "priority_rules"}
    )
    
    # Add semantic knowledge
    sender_id = await semantic.add(
        "CEO's emails are always marked as urgent",
        metadata={
            "sender": "ceo@company.com",
            "email_type": "executive",
            "priority": "high"
        }
    )
    
    # Add conversation about the rule
    conv_id = await episodic.add(
        "User asked about CEO email priority rules",
        metadata={
            "conversation_id": "conv_002",
            "type": "user_query",
            "timestamp": time.time()
        }
    )
    
    # Search across memories
    rule_results = await procedural.search("CEO priority")
    semantic_results = await semantic.search("CEO emails")
    episodic_results = await episodic.search("CEO rules")
    
    assert len(rule_results) > 0
    assert len(semantic_results) > 0
    assert len(episodic_results) > 0

async def cleanup_collections(force_cleanup: bool = False):
    """Clear all collections before running tests."""
    if not force_cleanup:
        print("\nWARNING: This will delete all data in the memory collections.")
        print("Collections: procedural, semantic, episodic")
        response = input("Are you sure you want to proceed? (y/N): ")
        if response.lower() != 'y':
            print("Cleanup cancelled. Tests may fail due to existing data.")
            return False
    
    print("Clearing existing collections...")
    procedural = ProceduralMemory(max_items=100)
    semantic = SemanticMemory(max_items=100) 
    episodic = EpisodicMemory(max_items=100)
    
    await procedural.clear_collection(force_delete=True)
    await semantic.clear_collection(force_delete=True) 
    await episodic.clear_collection(force_delete=True)
    print("✓ Collections cleared")
    return True

async def main(force_cleanup: bool = False):
    """Run all tests."""
    cleanup_success = await cleanup_collections(force_cleanup)
    if not cleanup_success:
        print("\nRunning tests without cleanup...")
    
    print("\nTesting Procedural Memory...")
    await test_procedural_memory()
    print("✓ Procedural Memory tests passed")
    
    print("\nTesting Semantic Memory...")
    await test_semantic_memory()
    print("✓ Semantic Memory tests passed")
    
    print("\nTesting Episodic Memory...")
    await test_episodic_memory()
    print("✓ Episodic Memory tests passed")
    
    print("\nTesting Memory Interaction...")
    await test_memory_interaction()
    print("✓ Memory Interaction tests passed")

if __name__ == "__main__":
    asyncio.run(main()) 
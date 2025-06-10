"""
Memory System Test Suite for EmailAgent

test suite for complete memory system validation in
private market asset management email automation environments. Provides
thorough testing of procedural, semantic, and episodic memory systems
with realistic asset management scenarios.

Features:
    - Complete memory system testing and validation
    - Realistic asset management test scenarios and data
    - test patterns and assertion validation
    - Memory system integration and coordination testing
    - Performance testing and optimization validation
    - error handling and recovery testing

Business Context:
    Designed for asset management firms requiring
    memory systems for email automation, relationship management,
    knowledge retention, and business intelligence. Tests
    real-world scenarios for investment workflows, compliance,
    and operational efficiency.

Test Categories:
    - Procedural Memory: Business rules and workflow automation
    - Semantic Memory: Sender intelligence and knowledge management
    - Episodic Memory: Conversation history and learning experiences
    - Integration Testing: Cross-memory system coordination
    - Performance Testing: Scalability and optimization validation
    - Error Handling: Resilience and recovery testing

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Core logging system
from utils.logging_system import get_logger, log_function, log_debug, log_info

# Memory system imports
from ..memory.procedural import ProceduralMemory, RuleType, RulePriority, RuleConfidence
from ..memory.semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence
from ..memory.episodic import EpisodicMemory, EpisodicMemoryType

# Testing framework
import pytest

# Initialize logger
logger = get_logger(__name__)

class MemoryTestSuite:
    """
    memory system test suite for asset management.
    
    Provides complete testing capabilities for all memory systems
    including business rules, sender intelligence, conversation history,
    and system integration for asset management environments.
    
    Features:
        - Complete test coverage for all memory types
        - Realistic asset management test scenarios
        - test patterns and validation
        - Performance benchmarking and optimization
        - Error handling and recovery testing
        
    Attributes:
        test_stats: Test execution metrics and results
        procedural_memory: Test instance of procedural memory
        semantic_memory: Test instance of semantic memory
        episodic_memory: Test instance of episodic memory
    """
    
    def __init__(self) -> None:
        """Initialize the memory test suite."""
        logger.info("Initializing MemoryTestSuite for asset management environments")
        
        self.test_stats = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
        # Initialize test memory instances
        self.procedural_memory = None
        self.semantic_memory = None
        self.episodic_memory = None
        
        logger.info("MemoryTestSuite initialized successfully")

    @log_function()
    async def setup_test_environment(self) -> None:
        """
        Setup clean test environment for memory system testing.
        
        Initializes clean memory instances and prepares test data
        for complete memory system validation.
        
        Raises:
            Exception: If test environment setup fails
        """
        logger.info("Setting up test environment for memory system testing")
        
        try:
            # Initialize memory instances with test configurations
            self.procedural_memory = ProceduralMemory(max_items=100)
            self.semantic_memory = SemanticMemory(max_items=100)
            self.episodic_memory = EpisodicMemory(max_items=100)
            
            # Clear existing data for clean testing
            await self.procedural_memory.clear_collection(force_delete=True)
            await self.semantic_memory.clear_collection(force_delete=True)
            await self.episodic_memory.clear_collection(force_delete=True)
            
            logger.info("Test environment setup completed successfully")
            
        except Exception as e:
            logger.error(f"Test environment setup failed: {e}")
            raise

    @log_function()
    async def cleanup_test_environment(self) -> None:
        """
        Clean up test environment after testing completion.
        
        Removes test data and cleans up memory instances to ensure
        no test artifacts remain in the system.
        """
        logger.info("Cleaning up test environment")
        
        try:
            if self.procedural_memory:
                await self.procedural_memory.clear_collection(force_delete=True)
            if self.semantic_memory:
                await self.semantic_memory.clear_collection(force_delete=True)
            if self.episodic_memory:
                await self.episodic_memory.clear_collection(force_delete=True)
                
            logger.info("Test environment cleanup completed")
            
        except Exception as e:
            logger.error(f"Test environment cleanup failed: {e}")

@pytest.mark.asyncio
@log_function()
async def test_procedural_memory() -> None:
    """
    Test procedural memory for business rules and procedures.
    
    Validates complete procedural memory capabilities including
    rule creation, retrieval, updates, deletion, and business logic
    for asset management environments.
    
    Raises:
        AssertionError: If procedural memory tests fail
    """
    logger.info("Testing procedural memory system")
    
    # Initialize test memory
    memory = ProceduralMemory(max_items=100)
    await memory.clear_collection(force_delete=True)
    
    # Test investment rule creation
    logger.info("Testing investment rule creation and retrieval")
    rule1_id = await memory.add(
        "Investment committee approval required for investments exceeding $25M",
        metadata={
            "threshold_amount": 25000000,
            "approval_body": "investment_committee",
            "sector": "all",
            "effective_date": "2024-01-01"
        },
        rule_type=RuleType.INVESTMENT,
        priority=RulePriority.HIGH,
        confidence=RuleConfidence.VERIFIED
    )
    
    # Test compliance rule creation
    logger.info("Testing compliance rule creation")
    rule2_id = await memory.add(
        "All transactions must be screened for AML compliance",
        metadata={
            "regulation_source": "AML_Guidelines",
            "mandatory": True,
            "screening_required": True
        },
        rule_type=RuleType.COMPLIANCE,
        priority=RulePriority.CRITICAL,
        confidence=RuleConfidence.VERIFIED
    )
    
    # Test rule retrieval
    logger.info("Testing rule retrieval")
    rule1 = await memory.get(rule1_id)
    assert rule1 is not None, "Rule should be retrievable"
    assert "investment committee" in rule1.content.lower(), "Rule content should match"
    assert rule1.metadata["threshold_amount"] == 25000000, "Metadata should be preserved"
    assert rule1.rule_type == RuleType.INVESTMENT, "Rule type should be correct"
    assert rule1.priority == RulePriority.HIGH, "Priority should be correct"
    
    # Test search functionality
    logger.info("Testing rule search functionality")
    search_results = await memory.search(
        "investment committee approval",
        limit=5
    )
    assert len(search_results) > 0, "Search should return results"
    assert any("investment committee" in r.content.lower() for r in search_results), "Search should find relevant rules"
    
    # Test rule type filtering
    logger.info("Testing rule type filtering")
    investment_rules = await memory.search_by_rule_type(
        rule_type=RuleType.INVESTMENT,
        limit=10
    )
    assert len(investment_rules) > 0, "Should find investment rules"
    assert all(r.rule_type == RuleType.INVESTMENT for r in investment_rules), "All results should be investment rules"
    
    # Test rule updates
    logger.info("Testing rule updates")
    success = await memory.update(
        rule1_id,
        "Investment committee approval required for investments exceeding $15M",
        metadata={
            "threshold_amount": 15000000,
            "approval_body": "investment_committee",
            "sector": "all",
            "effective_date": "2024-01-01",
            "last_updated": datetime.now(UTC).isoformat()
        }
    )
    assert success, "Rule update should succeed"
    
    updated_rule = await memory.get(rule1_id)
    assert "$15M" in updated_rule.content, "Rule content should be updated"
    assert updated_rule.metadata["threshold_amount"] == 15000000, "Metadata should be updated"
    
    # Test rule deletion
    logger.info("Testing rule deletion")
    success = await memory.delete(rule2_id)
    assert success, "Rule deletion should succeed"
    
    deleted_rule = await memory.get(rule2_id)
    assert deleted_rule is None, "Deleted rule should not be retrievable"
    
    # Test statistics
    logger.info("Testing rule statistics")
    stats = await memory.get_rule_statistics()
    assert stats["total_count"] > 0, "Should have rules in system"
    assert stats["active_count"] > 0, "Should have active rules"
    
    logger.info("Procedural memory tests completed successfully")

@pytest.mark.asyncio
@log_function()
async def test_semantic_memory() -> None:
    """
    Test semantic memory for sender intelligence and knowledge management.
    
    Validates complete semantic memory capabilities including
    knowledge creation, retrieval, search, and business intelligence
    for asset management environments.
    
    Raises:
        AssertionError: If semantic memory tests fail
    """
    logger.info("Testing semantic memory system")
    
    # Initialize test memory
    memory = SemanticMemory(max_items=100)
    await memory.clear_collection(force_delete=True)
    
    # Test sender intelligence creation
    logger.info("Testing sender intelligence creation")
    sender1_id = await memory.add(
        "Blackstone Group responds within 24 hours to investment inquiries with detailed technical analysis",
        metadata={
            "sender_domain": "blackstone.com",
            "organization": "Blackstone Group",
            "response_pattern": "fast_detailed",
            "business_category": "private_equity",
            "communication_style": "technical"
        },
        knowledge_type=KnowledgeType.SENDER,
        confidence=KnowledgeConfidence.HIGH
    )
    
    # Test domain expertise creation
    logger.info("Testing domain expertise creation")
    domain_id = await memory.add(
        "Real estate due diligence typically requires 6-12 months for transactions over $100M",
        metadata={
            "domain": "real_estate",
            "expertise_area": "due_diligence",
            "timeline": "6-12_months",
            "transaction_threshold": 100000000
        },
        knowledge_type=KnowledgeType.DOMAIN,
        confidence=KnowledgeConfidence.HIGH
    )
    
    # Test email type knowledge creation
    logger.info("Testing email type knowledge creation")
    email_type_id = await memory.add(
        "Investment proposals typically include fund size, target returns, and investment timeline",
        metadata={
            "email_type": "investment_proposal",
            "typical_content": ["fund_size", "target_returns", "timeline"],
            "classification_keywords": ["fund", "investment", "proposal", "returns"]
        },
        knowledge_type=KnowledgeType.EMAIL_TYPE,
        confidence=KnowledgeConfidence.HIGH
    )
    
    # Test knowledge retrieval
    logger.info("Testing knowledge retrieval")
    sender_knowledge = await memory.get(sender1_id)
    assert sender_knowledge is not None, "Knowledge should be retrievable"
    assert "Blackstone" in sender_knowledge.content, "Content should match"
    assert sender_knowledge.metadata["organization"] == "Blackstone Group", "Metadata should be preserved"
    assert sender_knowledge.knowledge_type == KnowledgeType.SENDER, "Knowledge type should be correct"
    
    # Test vector search
    logger.info("Testing vector search functionality")
    search_results = await memory.search(
        "investment proposal fund size",
        limit=5
    )
    assert len(search_results) > 0, "Search should return results"
    assert any("investment" in r.content.lower() for r in search_results), "Search should find relevant knowledge"
    
    # Test knowledge type filtering
    logger.info("Testing knowledge type filtering")
    sender_knowledge_items = await memory.search_by_knowledge_type(
        knowledge_type=KnowledgeType.SENDER,
        limit=10
    )
    assert len(sender_knowledge_items) > 0, "Should find sender knowledge"
    assert all(k.knowledge_type == KnowledgeType.SENDER for k in sender_knowledge_items), "All results should be sender knowledge"
    
    # Test domain-based search
    logger.info("Testing domain-based search")
    domain_results = await memory.search_by_domain(
        domain="blackstone.com",
        limit=5
    )
    assert len(domain_results) > 0, "Should find domain-specific knowledge"
    
    # Test filtered search
    logger.info("Testing filtered search")
    filtered_results = await memory.search(
        "investment",
        filter={
            "must": [
                {
                    "key": "metadata.business_category",
                    "match": {"value": "private_equity"}
                }
            ]
        }
    )
    assert len(filtered_results) > 0, "Filtered search should return results"
    
    # Test statistics
    logger.info("Testing knowledge statistics")
    stats = await memory.get_knowledge_statistics()
    assert stats["total_count"] > 0, "Should have knowledge in system"
    assert stats["sender_knowledge_count"] > 0, "Should have sender knowledge"
    
    logger.info("Semantic memory tests completed successfully")

@pytest.mark.asyncio
@log_function()
async def test_episodic_memory() -> None:
    """
    Test episodic memory for conversation history and learning experiences.
    
    Validates complete episodic memory capabilities including
    conversation storage, retrieval, temporal search, and learning
    for asset management environments.
    
    Raises:
        AssertionError: If episodic memory tests fail
    """
    logger.info("Testing episodic memory system")
    
    # Initialize test memory
    memory = EpisodicMemory(max_items=100)
    await memory.clear_collection(force_delete=True)
    
    # Test meeting memory creation
    logger.info("Testing meeting memory creation")
    meeting_id = await memory.add(
        "Investment committee approved $50M allocation to European infrastructure fund",
        metadata={
            "meeting_type": "investment_committee",
            "decision": "approved",
            "allocation_amount": 50000000,
            "asset_class": "infrastructure",
            "geographic_focus": "europe",
            "participants": ["CIO", "portfolio_managers"],
            "timestamp": time.time() - 24 * 3600  # 1 day ago
        },
        memory_type=EpisodicMemoryType.MEETING
    )
    
    # Test conversation memory creation
    logger.info("Testing conversation memory creation")
    conversation_id = await memory.add(
        "Client expressed interest in ESG-focused investment opportunities",
        metadata={
            "client_id": "client_001",
            "conversation_type": "investment_consultation",
            "interests": ["esg_investing", "sustainability"],
            "follow_up_required": True,
            "timestamp": time.time() - 12 * 3600  # 12 hours ago
        },
        memory_type=EpisodicMemoryType.CONVERSATION
    )
    
    # Test feedback memory creation
    logger.info("Testing feedback memory creation")
    feedback_id = await memory.add(
        "User corrected: Email from pension fund was investment inquiry, not general request",
        metadata={
            "feedback_type": "classification_correction",
            "original_classification": "general_inquiry",
            "correct_classification": "investment_inquiry",
            "sender_type": "pension_fund",
            "learning_point": "pension_funds_investment_focused",
            "timestamp": time.time() - 6 * 3600  # 6 hours ago
        },
        memory_type=EpisodicMemoryType.FEEDBACK
    )
    
    # Test memory retrieval
    logger.info("Testing memory retrieval")
    meeting_memory = await memory.get(meeting_id)
    assert meeting_memory is not None, "Memory should be retrievable"
    assert "investment committee" in meeting_memory.content.lower(), "Content should match"
    assert meeting_memory.metadata["allocation_amount"] == 50000000, "Metadata should be preserved"
    assert meeting_memory.memory_type == EpisodicMemoryType.MEETING, "Memory type should be correct"
    
    # Test temporal search
    logger.info("Testing temporal search")
    recent_memories = await memory.search_recent(
        hours=48,  # Last 48 hours
        limit=10
    )
    assert len(recent_memories) > 0, "Should find recent memories"
    
    # Test memory type filtering
    logger.info("Testing memory type filtering")
    meeting_memories = await memory.search_by_type(
        memory_type=EpisodicMemoryType.MEETING,
        limit=5
    )
    assert len(meeting_memories) > 0, "Should find meeting memories"
    assert all(m.memory_type == EpisodicMemoryType.MEETING for m in meeting_memories), "All results should be meeting memories"
    
    # Test conversation-based search
    logger.info("Testing conversation-based search")
    conversation_memories = await memory.search_by_type(
        memory_type=EpisodicMemoryType.CONVERSATION,
        limit=5
    )
    assert len(conversation_memories) > 0, "Should find conversation memories"
    
    # Test feedback search
    logger.info("Testing feedback search")
    feedback_memories = await memory.search_by_type(
        memory_type=EpisodicMemoryType.FEEDBACK,
        limit=5
    )
    assert len(feedback_memories) > 0, "Should find feedback memories"
    
    # Test time-based filtering
    logger.info("Testing time-based filtering")
    time_filtered = await memory.search(
        "investment",
        filter={
            "must": [
                {
                    "key": "metadata.timestamp",
                    "range": {
                        "gte": time.time() - 48 * 3600,  # 48 hours ago
                        "lte": time.time()
                    }
                }
            ]
        }
    )
    assert len(time_filtered) > 0, "Time-based filtering should return results"
    
    # Test statistics
    logger.info("Testing memory statistics")
    stats = await memory.get_memory_statistics()
    assert stats["total_count"] > 0, "Should have memories in system"
    assert stats.get("meeting_count", 0) > 0, "Should have meeting memories"
    
    logger.info("Episodic memory tests completed successfully")

@pytest.mark.asyncio
@log_function()
async def test_memory_integration() -> None:
    """
    Test integration between different memory types.
    
    Validates cross-memory system functionality including data
    consistency, integration patterns, and coordinated operations
    for complete asset management workflows.
    
    Raises:
        AssertionError: If memory integration tests fail
    """
    logger.info("Testing memory system integration")
    
    # Initialize all memory types
    procedural = ProceduralMemory(max_items=100)
    semantic = SemanticMemory(max_items=100)
    episodic = EpisodicMemory(max_items=100)
    
    # Clean start for all memory types
    await procedural.clear_collection(force_delete=True)
    await semantic.clear_collection(force_delete=True)
    await episodic.clear_collection(force_delete=True)
    
    # Test coordinated data creation
    logger.info("Testing coordinated data creation across memory types")
    
    # Add investment rule
    rule_id = await procedural.add(
        "Investment proposals from top-tier firms receive priority review",
        metadata={
            "firm_tier": "top_tier",
            "priority_level": "high",
            "review_speed": "expedited"
        },
        rule_type=RuleType.INVESTMENT,
        priority=RulePriority.HIGH,
        confidence=RuleConfidence.VERIFIED
    )
    
    # Add corresponding sender knowledge
    knowledge_id = await semantic.add(
        "Apollo Global Management is a top-tier private equity firm with excellent track record",
        metadata={
            "sender_domain": "apollo.com",
            "organization": "Apollo Global Management",
            "firm_tier": "top_tier",
            "track_record": "excellent",
            "business_category": "private_equity"
        },
        knowledge_type=KnowledgeType.SENDER,
        confidence=KnowledgeConfidence.HIGH
    )
    
    # Add related experience
    experience_id = await episodic.add(
        "Apollo's last investment proposal was approved within 72 hours due to their track record",
        metadata={
            "sender_organization": "Apollo Global Management",
            "outcome": "approved",
            "processing_time": "72_hours",
            "reason": "excellent_track_record",
            "timestamp": time.time() - 7 * 24 * 3600  # 1 week ago
        },
        memory_type=EpisodicMemoryType.EXPERIENCE
    )
    
    # Test coordinated retrieval
    logger.info("Testing coordinated retrieval across memory types")
    
    # Retrieve investment rule
    investment_rule = await procedural.get(rule_id)
    assert investment_rule is not None, "Investment rule should be retrievable"
    
    # Find related sender knowledge
    apollo_knowledge = await semantic.search_by_domain("apollo.com", limit=5)
    assert len(apollo_knowledge) > 0, "Should find Apollo knowledge"
    
    # Find related experiences
    apollo_experiences = await episodic.search("Apollo", limit=5)
    assert len(apollo_experiences) > 0, "Should find Apollo experiences"
    
    # Test cross-system consistency
    logger.info("Testing cross-system data consistency")
    
    # Verify firm tier consistency
    assert investment_rule.metadata["firm_tier"] == "top_tier", "Rule should specify top-tier requirement"
    
    apollo_info = apollo_knowledge[0]
    assert apollo_info.metadata["firm_tier"] == "top_tier", "Knowledge should classify Apollo as top-tier"
    
    # Test integrated statistics
    logger.info("Testing integrated statistics")
    
    proc_stats = await procedural.get_rule_statistics()
    sem_stats = await semantic.get_knowledge_statistics()
    epi_stats = await episodic.get_memory_statistics()
    
    assert proc_stats["total_count"] > 0, "Should have procedural rules"
    assert sem_stats["total_count"] > 0, "Should have semantic knowledge"
    assert epi_stats["total_count"] > 0, "Should have episodic memories"
    
    # Test coordinated search
    logger.info("Testing coordinated search across memory types")
    
    # Search for investment-related information across all systems
    investment_rules = await procedural.search("investment", limit=5)
    investment_knowledge = await semantic.search("investment", limit=5)
    investment_experiences = await episodic.search("investment", limit=5)
    
    total_investment_items = len(investment_rules) + len(investment_knowledge) + len(investment_experiences)
    assert total_investment_items > 0, "Should find investment-related information across all systems"
    
    logger.info("Memory integration tests completed successfully")

@pytest.mark.asyncio
@log_function()
async def test_memory_performance() -> None:
    """
    Test memory system performance and scalability.
    
    Validates memory system performance under load including
    bulk operations, search performance, and resource utilization
    for enterprise-scale asset management environments.
    
    Raises:
        AssertionError: If performance tests fail
    """
    logger.info("Testing memory system performance")
    
    # Initialize memory for performance testing
    memory = SemanticMemory(max_items=1000)
    await memory.clear_collection(force_delete=True)
    
    # Test bulk insertion performance
    logger.info("Testing bulk insertion performance")
    
    start_time = time.time()
    
    # Insert 100 knowledge items
    for i in range(100):
        await memory.add(
            f"Investment firm {i} provides specialized services in asset management sector",
            metadata={
                "firm_id": f"firm_{i}",
                "specialization": "asset_management",
                "index": i
            },
            knowledge_type=KnowledgeType.DOMAIN,
            confidence=KnowledgeConfidence.MEDIUM
        )
    
    insertion_time = time.time() - start_time
    logger.info(f"Bulk insertion completed in {insertion_time:.2f} seconds")
    
    # Test search performance
    logger.info("Testing search performance")
    
    start_time = time.time()
    
    # Perform multiple searches
    for i in range(10):
        results = await memory.search(f"investment firm {i % 20}", limit=10)
        assert len(results) > 0, f"Search {i} should return results"
    
    search_time = time.time() - start_time
    logger.info(f"Multiple searches completed in {search_time:.2f} seconds")
    
    # Test memory statistics performance
    logger.info("Testing statistics performance")
    
    start_time = time.time()
    stats = await memory.get_knowledge_statistics()
    stats_time = time.time() - start_time
    
    assert stats["total_count"] >= 100, "Should have at least 100 items"
    logger.info(f"Statistics generated in {stats_time:.2f} seconds")
    
    # Performance assertions
    assert insertion_time < 30.0, "Bulk insertion should complete within 30 seconds"
    assert search_time < 10.0, "Multiple searches should complete within 10 seconds"
    assert stats_time < 5.0, "Statistics should generate within 5 seconds"
    
    logger.info("Memory performance tests completed successfully")

@log_function()
async def cleanup_collections(force_cleanup: bool = False) -> None:
    """
    Clean up test collections after testing.
    
    Args:
        force_cleanup: Whether to force cleanup without confirmation
    """
    logger.info("Cleaning up test collections")
    
    try:
        # Initialize temporary memory instances for cleanup
        procedural = ProceduralMemory(max_items=100)
        semantic = SemanticMemory(max_items=100)
        episodic = EpisodicMemory(max_items=100)
        
        # Clear all collections
        await procedural.clear_collection(force_delete=force_cleanup)
        await semantic.clear_collection(force_delete=force_cleanup)
        await episodic.clear_collection(force_delete=force_cleanup)
        
        logger.info("Test collections cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Collection cleanup failed: {e}")

@log_function()
async def run_complete_test_suite() -> Dict[str, Any]:
    """
    Run complete memory system test suite.
    
    Returns:
        Dictionary containing test execution results and metrics
    """
    logger.info("🚀 Running complete memory system test suite")
    
    test_results = {
        'start_time': datetime.now(UTC),
        'tests_run': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'test_details': [],
        'errors': []
    }
    
    # Test suite execution
    test_functions = [
        ("Procedural Memory", test_procedural_memory),
        ("Semantic Memory", test_semantic_memory),
        ("Episodic Memory", test_episodic_memory),
        ("Memory Integration", test_memory_integration),
        ("Memory Performance", test_memory_performance)
    ]
    
    for test_name, test_function in test_functions:
        logger.info(f"Running {test_name} tests...")
        test_results['tests_run'] += 1
        
        try:
            test_start = time.time()
            await test_function()
            test_duration = time.time() - test_start
            
            test_results['tests_passed'] += 1
            test_results['test_details'].append({
                'name': test_name,
                'status': 'PASSED',
                'duration': test_duration,
                'error': None
            })
            
            logger.info(f"✅ {test_name} tests passed ({test_duration:.2f}s)")
            
        except Exception as e:
            test_results['tests_failed'] += 1
            test_results['errors'].append(f"{test_name}: {str(e)}")
            test_results['test_details'].append({
                'name': test_name,
                'status': 'FAILED',
                'duration': 0,
                'error': str(e)
            })
            
            logger.error(f"❌ {test_name} tests failed: {e}")
    
    # Cleanup after tests
    try:
        await cleanup_collections(force_cleanup=True)
    except Exception as e:
        logger.error(f"Test cleanup failed: {e}")
    
    test_results['end_time'] = datetime.now(UTC)
    test_results['total_duration'] = (test_results['end_time'] - test_results['start_time']).total_seconds()
    test_results['success_rate'] = (test_results['tests_passed'] / test_results['tests_run']) * 100 if test_results['tests_run'] > 0 else 0
    
    return test_results

async def main(force_cleanup: bool = False) -> bool:
    """
    Main test execution function.
    
    Args:
        force_cleanup: Whether to force cleanup without confirmation
        
    Returns:
        True if all tests passed, False otherwise
    """
    logger.info("🎯 EmailAgent Memory System Test Suite")
    logger.info("=" * 60)
    
    try:
        # Run complete test suite
        results = await run_complete_test_suite()
        
        # Display results
        print(f"\n📊 Test Results Summary:")
        print(f"   - Tests Run: {results['tests_run']}")
        print(f"   - Tests Passed: {results['tests_passed']}")
        print(f"   - Tests Failed: {results['tests_failed']}")
        print(f"   - Success Rate: {results['success_rate']:.1f}%")
        print(f"   - Total Duration: {results['total_duration']:.2f} seconds")
        
        # Display individual test results
        print(f"\n📋 Individual Test Results:")
        for test_detail in results['test_details']:
            status_emoji = "✅" if test_detail['status'] == 'PASSED' else "❌"
            print(f"   {status_emoji} {test_detail['name']}: {test_detail['status']}")
            if test_detail['error']:
                print(f"      Error: {test_detail['error']}")
        
        # Display errors if any
        if results['errors']:
            print(f"\n❌ Errors Encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        success = results['tests_failed'] == 0
        
        if success:
            print(f"\n🎉 All memory system tests passed successfully!")
        else:
            print(f"\n⚠️  {results['tests_failed']} test(s) failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        print(f"\n❌ Test suite execution failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run memory system tests")
    parser.add_argument("--force-cleanup", action="store_true", help="Force cleanup without confirmation")
    args = parser.parse_args()
    
    success = asyncio.run(main(force_cleanup=args.force_cleanup))
    sys.exit(0 if success else 1) 
"""
Email Memory System Demonstration for EmailAgent

demonstration script showcasing the complete memory system
capabilities for private market asset management email automation. Provides
realistic data population and query demonstrations for enterprise environments.

Features:
    - Complete memory system demonstration and validation
    - Realistic asset management email scenarios and data
    - query patterns and business intelligence
    - Memory system integration and workflow demonstration
    - Performance benchmarking and optimization insights
    - error handling and logging integration

Business Context:
    Designed for asset management firms requiring
    memory systems for email automation, relationship management,
    knowledge retention, and business intelligence. Demonstrates
    real-world scenarios for investment workflows, compliance,
    and operational efficiency.

Technical Architecture:
    - Multi-modal memory system integration and coordination
    - Realistic data population with business context
    - Query pattern demonstration and performance validation
    - Memory system learning and adaptation capabilities
    - demonstration workflow and reporting

Demo Categories:
    - Procedural: Business rules and workflow automation
    - Semantic: Sender intelligence and knowledge management
    - Episodic: Conversation history and learning experiences
    - Integration: Cross-memory system coordination and insights

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

# Core logging system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

# Memory system imports
from ..memory.procedural import ProceduralMemory, RuleType, RulePriority, RuleConfidence
from ..memory.semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence
from ..memory.episodic import EpisodicMemory, EpisodicMemoryType

# Initialize logger
logger = get_logger(__name__)

class EmailMemoryDemo:
    """
    email memory system demonstration for asset management.
    
    Provides complete demonstration of memory system capabilities
    including data population, query patterns, and business intelligence
    for private market asset management email automation environments.
    
    Features:
        - Realistic asset management data population
        - query pattern demonstrations
        - Memory system integration and coordination
        - Performance benchmarking and insights
        - Business intelligence and learning capabilities
        
    Attributes:
        procedural: Business rules and workflow automation memory
        semantic: Sender intelligence and knowledge management memory
        episodic: Conversation history and learning memory
    """
    
    def __init__(self) -> None:
        """Initialize the email memory demonstration system."""
        logger.info("Initializing EmailMemoryDemo for asset management environments")
        
        self.procedural = ProceduralMemory(max_items=1000)
        self.semantic = SemanticMemory(max_items=1000)
        self.episodic = EpisodicMemory(max_items=1000)
        
        # Demo metrics and tracking
        self.demo_stats = {
            'start_time': None,
            'end_time': None,
            'procedural_rules_added': 0,
            'semantic_knowledge_added': 0,
            'episodic_memories_added': 0,
            'queries_executed': 0,
            'errors_encountered': 0
        }
        
        logger.info("EmailMemoryDemo initialized successfully")

    @log_function()
    async def setup_demo_data(self) -> None:
        """
        Populate the memory system with realistic asset management data.
        
        Creates complete demonstration data including business rules,
        sender intelligence, and conversation history for professional
        asset management email automation scenarios.
        
        Raises:
            Exception: If demo data setup fails
        """
        logger.info("🧠 Setting up demo data for email memory system...")
        self.demo_stats['start_time'] = datetime.now(UTC)
        
        try:
            # Clear existing data for clean demonstration
            logger.info("Clearing existing memory collections for clean demo")
            await self.procedural.clear_collection(force_delete=True)
            await self.semantic.clear_collection(force_delete=True)
            await self.episodic.clear_collection(force_delete=True)
            
            # Populate memory systems with realistic data
            await self._populate_procedural_memory()
            await self._populate_semantic_memory()
            await self._populate_episodic_memory()
            
            logger.info("✅ Demo data setup complete!")
            logger.info(f"Added {self.demo_stats['procedural_rules_added']} rules, "
                       f"{self.demo_stats['semantic_knowledge_added']} knowledge items, "
                       f"{self.demo_stats['episodic_memories_added']} episodic memories")
            
        except Exception as e:
            self.demo_stats['errors_encountered'] += 1
            logger.error(f"Demo data setup failed: {e}")
            raise

    @log_function()
    async def _populate_procedural_memory(self) -> None:
        """
        Add complete business rules and procedures for asset management.
        
        Populates procedural memory with investment rules, compliance procedures,
        operational standards, and decision criteria for professional
        asset management environments.
        """
        logger.info("📋 Adding procedural memory (business rules and procedures)...")
        
        # Investment decision and approval rules
        investment_rules = [
            {
                "content": "Investment committee approval required for any single investment exceeding $50M",
                "rule_type": RuleType.INVESTMENT,
                "priority": RulePriority.CRITICAL,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "threshold_amount": 50000000,
                    "approval_body": "investment_committee",
                    "sector": "all",
                    "effective_date": "2024-01-01"
                }
            },
            {
                "content": "Real estate investments require property appraisal and market analysis documentation",
                "rule_type": RuleType.INVESTMENT,
                "priority": RulePriority.HIGH,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "sector": "real_estate",
                    "required_docs": ["appraisal", "market_analysis"],
                    "compliance_requirement": True
                }
            },
            {
                "content": "Private equity fund investments require LP consent for fund size changes > 20%",
                "rule_type": RuleType.INVESTMENT,
                "priority": RulePriority.HIGH,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "sector": "private_equity",
                    "threshold_percent": 20,
                    "consent_required": "limited_partners"
                }
            }
        ]
        
        # Compliance and regulatory rules
        compliance_rules = [
            {
                "content": "All investment documents must be reviewed for anti-money laundering compliance",
                "rule_type": RuleType.COMPLIANCE,
                "priority": RulePriority.CRITICAL,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "regulation_source": "SEC_AML_Guidelines",
                    "mandatory": True,
                    "review_required": True
                }
            },
            {
                "content": "Investor communications must comply with privacy regulations and data protection",
                "rule_type": RuleType.COMPLIANCE,
                "priority": RulePriority.HIGH,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "regulation_source": "GDPR_CCPA",
                    "data_protection": True,
                    "privacy_compliance": True
                }
            }
        ]
        
        # Email classification and routing rules
        classification_rules = [
            {
                "content": "Emails containing 'due diligence', 'investment proposal', or 'fund performance' classified as investment_related",
                "rule_type": RuleType.CLASSIFICATION,
                "priority": RulePriority.MEDIUM,
                "confidence": RuleConfidence.TESTED,
                "metadata": {
                    "keywords": ["due diligence", "investment proposal", "fund performance"],
                    "target_category": "investment_related",
                    "confidence_threshold": 0.8
                }
            },
            {
                "content": "Regulatory filings and compliance notifications routed to compliance team immediately",
                "rule_type": RuleType.ROUTING,
                "priority": RulePriority.HIGH,
                "confidence": RuleConfidence.VERIFIED,
                "metadata": {
                    "target_team": "compliance",
                    "routing_speed": "immediate",
                    "notification_required": True
                }
            }
        ]
        
        # Add all rules to procedural memory
        all_rules = investment_rules + compliance_rules + classification_rules
        
        for rule_data in all_rules:
            try:
                await self.procedural.add(
                    content=rule_data["content"],
                    metadata=rule_data["metadata"],
                    rule_type=rule_data["rule_type"],
                    priority=rule_data["priority"],
                    confidence=rule_data["confidence"]
                )
                self.demo_stats['procedural_rules_added'] += 1
            except Exception as e:
                logger.error(f"Failed to add procedural rule: {e}")
                self.demo_stats['errors_encountered'] += 1
        
        logger.info(f"   Added {len(all_rules)} procedural rules")

    @log_function()
    async def _populate_semantic_memory(self) -> None:
        """
        Add complete sender intelligence and knowledge for asset management.
        
        Populates semantic memory with relationship intelligence, communication
        patterns, and domain expertise for counterparty
        management and business intelligence.
        """
        logger.info("🧠 Adding semantic memory (sender intelligence and knowledge)...")
        
        # Investment firm and counterparty knowledge
        investment_knowledge = [
            {
                "content": "Blackstone Group responds within 24 hours to investment inquiries, prefers detailed technical analysis",
                "knowledge_type": KnowledgeType.SENDER,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "sender_domain": "blackstone.com",
                    "organization": "Blackstone Group",
                    "response_pattern": "fast_business_hours",
                    "communication_style": "technical_detailed",
                    "business_category": "private_equity"
                }
            },
            {
                "content": "Apollo Global Management investment committee meets Tuesdays, decisions communicated Fridays",
                "knowledge_type": KnowledgeType.SENDER,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "sender_domain": "apollo.com",
                    "organization": "Apollo Global Management",
                    "decision_schedule": "tuesday_committee_friday_communication",
                    "business_category": "private_equity"
                }
            },
            {
                "content": "Brookfield Asset Management specializes in infrastructure and real estate with global focus",
                "knowledge_type": KnowledgeType.SENDER,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "sender_domain": "brookfield.com",
                    "organization": "Brookfield Asset Management",
                    "specialization": ["infrastructure", "real_estate"],
                    "geographic_focus": "global"
                }
            }
        ]
        
        # Email type and pattern knowledge
        email_type_knowledge = [
            {
                "content": "Investment inquiries typically include fund size, target returns, and investment timeline",
                "knowledge_type": KnowledgeType.EMAIL_TYPE,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "email_type": "investment_inquiry",
                    "typical_content": ["fund_size", "target_returns", "timeline"],
                    "classification_criteria": "mentions fund, investment, capital, returns"
                }
            },
            {
                "content": "Due diligence requests contain document lists, data room access, and review timelines",
                "knowledge_type": KnowledgeType.EMAIL_TYPE,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "email_type": "due_diligence",
                    "typical_content": ["document_lists", "data_room", "timeline"],
                    "urgency_level": "high"
                }
            }
        ]
        
        # Domain expertise and industry knowledge
        domain_knowledge = [
            {
                "content": "Real estate private equity typically requires 6-12 month due diligence for large transactions ($100M+)",
                "knowledge_type": KnowledgeType.DOMAIN,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "domain": "real_estate",
                    "expertise_area": "private_equity_due_diligence",
                    "typical_timeline": "6-12_months",
                    "transaction_threshold": 100000000
                }
            },
            {
                "content": "Infrastructure investments require regulatory approval and ESG compliance assessment",
                "knowledge_type": KnowledgeType.DOMAIN,
                "confidence": KnowledgeConfidence.HIGH,
                "metadata": {
                    "domain": "infrastructure",
                    "expertise_area": "regulatory_compliance",
                    "requirements": ["regulatory_approval", "esg_assessment"]
                }
            }
        ]
        
        # Add all knowledge to semantic memory
        all_knowledge = investment_knowledge + email_type_knowledge + domain_knowledge
        
        for knowledge_data in all_knowledge:
            try:
                await self.semantic.add(
                    content=knowledge_data["content"],
                    metadata=knowledge_data["metadata"],
                    knowledge_type=knowledge_data["knowledge_type"],
                    confidence=knowledge_data["confidence"]
                )
                self.demo_stats['semantic_knowledge_added'] += 1
            except Exception as e:
                logger.error(f"Failed to add semantic knowledge: {e}")
                self.demo_stats['errors_encountered'] += 1
        
        logger.info(f"   Added {len(all_knowledge)} knowledge items")

    @log_function()
    async def _populate_episodic_memory(self) -> None:
        """
        Add conversation history and learning experiences for asset management.
        
        Populates episodic memory with investment meeting records, decision
        audit trails, client interactions, and learning experiences for
        business intelligence and process optimization.
        """
        logger.info("📝 Adding episodic memory (conversation history and experiences)...")
        
        # Investment committee meetings and decisions
        meeting_memories = [
            {
                "content": "Investment committee approved $75M allocation to European real estate fund",
                "memory_type": EpisodicMemoryType.MEETING,
                "metadata": {
                    "meeting_type": "investment_committee",
                    "decision": "approved",
                    "allocation_amount": 75000000,
                    "asset_class": "real_estate",
                    "geographic_focus": "europe",
                    "participants": ["CIO", "portfolio_managers", "risk_team"],
                    "timestamp": time.time() - 7 * 24 * 3600  # 1 week ago
                }
            },
            {
                "content": "Due diligence meeting for infrastructure fund identified regulatory concerns requiring resolution",
                "memory_type": EpisodicMemoryType.MEETING,
                "metadata": {
                    "meeting_type": "due_diligence",
                    "asset_class": "infrastructure",
                    "concerns": ["regulatory_compliance", "permitting_issues"],
                    "action_required": "legal_review",
                    "timestamp": time.time() - 3 * 24 * 3600  # 3 days ago
                }
            }
        ]
        
        # Client conversations and interactions
        conversation_memories = [
            {
                "content": "Client expressed interest in ESG-focused investment opportunities, requested quarterly updates",
                "memory_type": EpisodicMemoryType.CONVERSATION,
                "metadata": {
                    "client_id": "client_001",
                    "conversation_type": "investment_consultation",
                    "interests": ["esg_investing", "sustainability"],
                    "requested_frequency": "quarterly",
                    "timestamp": time.time() - 5 * 24 * 3600  # 5 days ago
                }
            },
            {
                "content": "Family office requested detailed performance attribution for private credit portfolio",
                "memory_type": EpisodicMemoryType.CONVERSATION,
                "metadata": {
                    "client_type": "family_office",
                    "request_type": "performance_attribution",
                    "portfolio_focus": "private_credit",
                    "urgency": "high",
                    "timestamp": time.time() - 24 * 3600  # 1 day ago
                }
            }
        ]
        
        # User feedback and system learning
        feedback_memories = [
            {
                "content": "User corrected: Email from pension fund was investment inquiry, not general information request",
                "memory_type": EpisodicMemoryType.FEEDBACK,
                "metadata": {
                    "feedback_type": "classification_correction",
                    "original_classification": "general_inquiry",
                    "correct_classification": "investment_inquiry",
                    "sender_type": "pension_fund",
                    "learning_point": "pension_funds_investment_focused",
                    "timestamp": time.time() - 2 * 24 * 3600  # 2 days ago
                }
            }
        ]
        
        # Add all memories to episodic memory
        all_memories = meeting_memories + conversation_memories + feedback_memories
        
        for memory_data in all_memories:
            try:
                await self.episodic.add(
                    content=memory_data["content"],
                    metadata=memory_data["metadata"],
                    memory_type=memory_data["memory_type"]
                )
                self.demo_stats['episodic_memories_added'] += 1
            except Exception as e:
                logger.error(f"Failed to add episodic memory: {e}")
                self.demo_stats['errors_encountered'] += 1
        
        logger.info(f"   Added {len(all_memories)} episodic memories")

    @log_function()
    async def run_demo_queries(self) -> None:
        """
        Execute complete demonstration queries across all memory systems.
        
        Demonstrates query patterns, business intelligence
        capabilities, and memory system integration for asset management
        email automation environments.
        """
        logger.info("🔍 Running complete demo queries...")
        
        demo_sections = [
            ("Investment Decision Support", self._demo_investment_intelligence),
            ("Compliance and Regulatory", self._demo_compliance_queries),
            ("Sender Intelligence Analysis", self._demo_sender_analysis),
            ("Email Classification Patterns", self._demo_classification_queries),
            ("Business Learning and Adaptation", self._demo_learning_queries),
            ("Cross-Memory System Integration", self._demo_integration_queries)
        ]
        
        for section_name, demo_function in demo_sections:
            logger.info(f"\n--- {section_name} ---")
            try:
                await demo_function()
                self.demo_stats['queries_executed'] += 1
            except Exception as e:
                logger.error(f"Demo section '{section_name}' failed: {e}")
                self.demo_stats['errors_encountered'] += 1

    @log_function()
    async def _demo_investment_intelligence(self) -> None:
        """Demonstrate investment decision support queries."""
        logger.info("💼 Investment Decision Support Queries")
        
        # Search for investment approval rules
        investment_rules = await self.procedural.search_by_rule_type(
            rule_type=RuleType.INVESTMENT,
            limit=5
        )
        
        logger.info(f"Found {len(investment_rules)} investment rules:")
        for rule in investment_rules:
            threshold = rule.metadata.get('threshold_amount', 'N/A')
            logger.info(f"  - {rule.content[:80]}... (Threshold: ${threshold:,})")
        
        # Search for counterparty knowledge
        counterparty_knowledge = await self.semantic.search(
            query="investment committee decision timeline",
            knowledge_type=KnowledgeType.SENDER,
            limit=3
        )
        
        logger.info(f"\nFound {len(counterparty_knowledge)} counterparty insights:")
        for knowledge in counterparty_knowledge:
            org = knowledge.metadata.get('organization', 'Unknown')
            logger.info(f"  - {org}: {knowledge.content[:80]}...")

    @log_function()
    async def _demo_compliance_queries(self) -> None:
        """Demonstrate compliance and regulatory queries."""
        logger.info("⚖️ Compliance and Regulatory Queries")
        
        # Search for compliance rules
        compliance_rules = await self.procedural.search_by_rule_type(
            rule_type=RuleType.COMPLIANCE,
            min_priority=RulePriority.HIGH
        )
        
        logger.info(f"Found {len(compliance_rules)} high-priority compliance rules:")
        for rule in compliance_rules:
            source = rule.metadata.get('regulation_source', 'Unknown')
            logger.info(f"  - {source}: {rule.content[:80]}...")

    @log_function()
    async def _demo_sender_analysis(self) -> None:
        """Demonstrate sender intelligence and analysis."""
        logger.info("👥 Sender Intelligence Analysis")
        
        # Search for sender knowledge by domain
        apollo_knowledge = await self.semantic.search_by_domain(
            domain="apollo.com",
            limit=5
        )
        
        logger.info(f"Found {len(apollo_knowledge)} knowledge items about Apollo:")
        for knowledge in apollo_knowledge:
            logger.info(f"  - {knowledge.content[:80]}...")

    @log_function()
    async def _demo_classification_queries(self) -> None:
        """Demonstrate email classification pattern queries."""
        logger.info("📧 Email Classification Pattern Queries")
        
        # Search for classification rules
        classification_rules = await self.procedural.search_by_rule_type(
            rule_type=RuleType.CLASSIFICATION
        )
        
        logger.info(f"Found {len(classification_rules)} classification rules:")
        for rule in classification_rules:
            category = rule.metadata.get('target_category', 'Unknown')
            logger.info(f"  - {category}: {rule.content[:80]}...")

    @log_function()
    async def _demo_learning_queries(self) -> None:
        """Demonstrate learning and adaptation queries."""
        logger.info("🧠 Business Learning and Adaptation")
        
        # Search for feedback and learning experiences
        feedback_memories = await self.episodic.search_by_type(
            memory_type=EpisodicMemoryType.FEEDBACK,
            limit=5
        )
        
        logger.info(f"Found {len(feedback_memories)} learning experiences:")
        for memory in feedback_memories:
            feedback_type = memory.metadata.get('feedback_type', 'Unknown')
            logger.info(f"  - {feedback_type}: {memory.content[:80]}...")

    @log_function()
    async def _demo_integration_queries(self) -> None:
        """Demonstrate cross-memory system integration."""
        logger.info("🔗 Cross-Memory System Integration")
        
        # Get statistics from all memory systems
        proc_stats = await self.procedural.get_rule_statistics()
        sem_stats = await self.semantic.get_knowledge_statistics()
        epi_stats = await self.episodic.get_memory_statistics()
        
        logger.info("Memory System Statistics:")
        logger.info(f"  - Procedural Rules: {proc_stats['total_count']} total, {proc_stats['active_count']} active")
        logger.info(f"  - Semantic Knowledge: {sem_stats['total_count']} items, avg length {sem_stats['average_content_length']:.1f}")
        logger.info(f"  - Episodic Memories: {epi_stats['total_count']} memories, {epi_stats.get('conversation_count', 0)} conversations")

    @log_function()
    async def generate_demo_report(self) -> Dict[str, Any]:
        """
        Generate complete demonstration report with metrics and insights.
        
        Returns:
            Dictionary containing demo execution metrics and business insights
        """
        self.demo_stats['end_time'] = datetime.now(UTC)
        
        if self.demo_stats['start_time']:
            duration = (self.demo_stats['end_time'] - self.demo_stats['start_time']).total_seconds()
        else:
            duration = 0
        
        # Generate complete memory statistics
        try:
            memory_stats = {
                'procedural': await self.procedural.get_rule_statistics(),
                'semantic': await self.semantic.get_knowledge_statistics(),
                'episodic': await self.episodic.get_memory_statistics()
            }
        except Exception as e:
            logger.error(f"Failed to generate memory statistics: {e}")
            memory_stats = {}
        
        report = {
            'demo_execution': {
                'duration_seconds': duration,
                'queries_executed': self.demo_stats['queries_executed'],
                'errors_encountered': self.demo_stats['errors_encountered'],
                'success_rate': (self.demo_stats['queries_executed'] / 
                               max(1, self.demo_stats['queries_executed'] + self.demo_stats['errors_encountered'])) * 100
            },
            'data_population': {
                'procedural_rules': self.demo_stats['procedural_rules_added'],
                'semantic_knowledge': self.demo_stats['semantic_knowledge_added'],
                'episodic_memories': self.demo_stats['episodic_memories_added'],
                'total_items': (self.demo_stats['procedural_rules_added'] + 
                              self.demo_stats['semantic_knowledge_added'] + 
                              self.demo_stats['episodic_memories_added'])
            },
            'memory_statistics': memory_stats,
            'business_insights': {
                'investment_rules_configured': memory_stats.get('procedural', {}).get('rule_types', {}).get('investment', 0),
                'compliance_rules_active': memory_stats.get('procedural', {}).get('rule_types', {}).get('compliance', 0),
                'counterparty_knowledge_items': memory_stats.get('semantic', {}).get('sender_knowledge_count', 0),
                'learning_experiences_captured': memory_stats.get('episodic', {}).get('feedback_count', 0)
            }
        }
        
        return report

# Demonstration execution function
@log_function()
async def run_complete_demo() -> Dict[str, Any]:
    """
    Execute complete email memory system demonstration.
    
    Runs complete demonstration workflow including data setup,
    query execution, and report generation for professional
    asset management environments.
    
    Returns:
        Complete demonstration report with metrics and insights
    """
    logger.info("🚀 Starting complete email memory system demonstration")
    
    try:
        # Initialize and run demonstration
        demo = EmailMemoryDemo()
        
        # Setup demonstration data
        await demo.setup_demo_data()
        
        # Execute demonstration queries
        await demo.run_demo_queries()
        
        # Generate complete report
        report = await demo.generate_demo_report()
        
        logger.info("✅ Email memory system demonstration completed successfully")
        logger.info(f"Demo Results: {report['demo_execution']['queries_executed']} queries, "
                   f"{report['data_population']['total_items']} items, "
                   f"{report['demo_execution']['success_rate']:.1f}% success rate")
        
        return report
        
    except Exception as e:
        logger.error(f"Email memory system demonstration failed: {e}")
        raise

async def main() -> bool:
    """Main demonstration entry point."""
    logger.info("🎯 EmailAgent Memory System Demonstration")
    logger.info("=" * 60)
    
    try:
        report = await run_complete_demo()
        
        print("\n🎉 Demonstration completed successfully!")
        print(f"📊 Execution Summary:")
        print(f"   - Duration: {report['demo_execution']['duration_seconds']:.1f} seconds")
        print(f"   - Queries: {report['demo_execution']['queries_executed']}")
        print(f"   - Data Items: {report['data_population']['total_items']}")
        print(f"   - Success Rate: {report['demo_execution']['success_rate']:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"\n❌ Demonstration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
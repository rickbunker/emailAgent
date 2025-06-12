"""
Semantic Memory System for EmailAgent

semantic memory system for private market asset management environments.
Provides knowledge storage and retrieval for sender intelligence, email type classification,
and domain expertise with search and learning capabilities.

Features:
    - Sender knowledge and relationship intelligence
    - Email type classification and pattern recognition
    - Domain expertise and industry knowledge storage
    - Semantic search with business context filtering
    - Knowledge enrichment and refinement over time
    - confidence scoring and validation

Business Context:
    Designed for asset management firms requiring knowledge management
    about counterparties, communication patterns, and industry intelligence.
    Maintains semantic understanding of business relationships, email classifications,
    and operational knowledge for improved decision support and automation.

Technical Architecture:
    - Qdrant-based vector storage for semantic knowledge
    - Knowledge categorization with confidence scoring
    - Semantic search with domain-specific filtering
    - Knowledge lifecycle management and updates
    - Performance optimization for knowledge retrieval

Knowledge Types:
    - Sender: Information about email senders and counterparties
    - Email_Type: Email classification and pattern knowledge
    - Domain: Industry and domain-specific expertise
    - Process: Business process and workflow knowledge
    - Rule: Business rules and decision criteria

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, UTC
from enum import Enum

from qdrant_client.http import models

# Logging system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

from .base import BaseMemory, MemoryItem

# Initialize logger
logger = get_logger(__name__)

class KnowledgeType(Enum):
    """
    knowledge classification for semantic memory.
    
    Provides structured categorization of knowledge types for asset
    management environments with appropriate business context and
    semantic organization.
    
    Values:
        SENDER: Knowledge about email senders and counterparties
        EMAIL_TYPE: Email classification and pattern knowledge
        DOMAIN: Industry and domain-specific expertise
        PROCESS: Business process and workflow knowledge
        RULE: Business rules and decision criteria
        INSIGHT: Business insights and intelligence
        PATTERN: Communication and behavioral patterns
        UNKNOWN: Unclassified knowledge requiring review
    """
    SENDER = "sender"
    EMAIL_TYPE = "email_type"
    DOMAIN = "domain"
    PROCESS = "process"
    RULE = "rule"
    INSIGHT = "insight"
    PATTERN = "pattern"
    UNKNOWN = "unknown"

class KnowledgeConfidence(Enum):
    """
    Knowledge confidence levels for semantic memory quality assessment.
    
    Provides graduated confidence scoring for knowledge accuracy
    to support knowledge quality management and validation workflows.
    
    Values:
        HIGH: Verified knowledge from authoritative sources
        MEDIUM: Knowledge from reliable but unverified sources
        LOW: Knowledge requiring verification or review
        EXPERIMENTAL: Tentative knowledge under evaluation
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXPERIMENTAL = "experimental"

class SemanticMemory(BaseMemory):
    """
    semantic memory system for asset management environments.
    
    Provides complete knowledge storage and retrieval with semantic
    understanding designed for private market asset management firms
    requiring intelligence about counterparties, communication
    patterns, and domain expertise.
    
    Features:
        - Sender intelligence and relationship knowledge
        - Email type classification and pattern recognition
        - Domain expertise and industry knowledge management
        - Semantic search with business context filtering
        - Knowledge confidence scoring and validation
        - Knowledge enrichment and learning capabilities
        
    Business Context:
        Enables asset management firms to maintain knowledge
        bases about counterparties, communication patterns, industry
        intelligence, and operational expertise for improved decision
        support and automated processing.
        
    Technical Implementation:
        - Dedicated Qdrant collection for semantic knowledge
        - Knowledge categorization with confidence scoring
        - Vector semantic search with domain filtering
        - Knowledge lifecycle management and updates
        - audit trail and knowledge tracking
    """
    
    def __init__(
        self,
        max_items: Optional[int] = 1000,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize semantic memory system.
        
        Args:
            max_items: Maximum number of knowledge items to store (default: 1000)
            qdrant_url: Qdrant database connection URL
            embedding_model: Sentence transformer model for embeddings
        """
        super().__init__(
            max_items=max_items,
            qdrant_url=qdrant_url,
            embedding_model=embedding_model
        )
        self.collection_name = "semantic"
        logger.info(f"Initialized SemanticMemory with max_items={max_items}")
    
    @log_function()
    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        knowledge_type: KnowledgeType = KnowledgeType.UNKNOWN,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM
    ) -> str:
        """
        Add new knowledge to semantic memory with complete metadata.
        
        Creates knowledge entries with automatic categorization, confidence
        scoring, and metadata enrichment for asset management
        environments.
        
        Args:
            content: The knowledge content to store
            metadata: Additional metadata for business context
            knowledge_type: Type of knowledge for categorization
            confidence: Confidence level in the knowledge accuracy
            
        Returns:
            The ID of the created knowledge item
            
        Raises:
            ValueError: If content is empty or invalid
            
        Example:
            >>> knowledge_id = await semantic_memory.add(
            ...     content="Blackstone Group typically responds within 24 hours to investment inquiries",
            ...     metadata={
            ...         "sender_domain": "blackstone.com",
            ...         "response_pattern": "fast",
            ...         "business_category": "private_equity"
            ...     },
            ...     knowledge_type=KnowledgeType.SENDER,
            ...     confidence=KnowledgeConfidence.HIGH
            ... )
        """
        if not content or not isinstance(content, str):
            raise ValueError("Knowledge content must be a non-empty string")
        
        if metadata is None:
            metadata = {}
        
        # Set complete knowledge metadata
        metadata["type"] = "knowledge"
        metadata["knowledge_type"] = knowledge_type.value
        metadata["confidence"] = confidence.value
        metadata["created_at"] = datetime.now(UTC).isoformat()
        metadata["source"] = "semantic_memory"
        metadata["version"] = "1.0.0"
        
        logger.info(f"Adding semantic knowledge: type={knowledge_type.value}, confidence={confidence.value}")
        logger.debug(f"Knowledge content length: {len(content)}")
        
        try:
            result = await super().add(content, metadata)
            logger.info(f"Successfully added semantic knowledge: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to add semantic knowledge: {e}")
            raise
    
    @log_function()
    async def add_sender_knowledge(
        self,
        content: str,
        sender_email: str,
        sender_domain: Optional[str] = None,
        organization: Optional[str] = None,
        response_pattern: Optional[str] = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs
    ) -> str:
        """
        Add sender-specific knowledge with relationship intelligence.
        
        Specialized method for adding knowledge about email senders,
        their organizations, and communication patterns for relationship
        management and business intelligence.
        
        Args:
            content: Knowledge about the sender
            sender_email: Email address of the sender
            sender_domain: Domain of the sender's organization
            organization: Organization name
            response_pattern: Communication response patterns
            confidence: Confidence level in the knowledge
            **kwargs: Additional sender metadata
            
        Returns:
            Knowledge ID of the created sender knowledge
            
        Example:
            >>> sender_id = await semantic_memory.add_sender_knowledge(
            ...     content="Investment committee meets Tuesdays, decisions communicated Fridays",
            ...     sender_email="ic@privateequity.com",
            ...     sender_domain="privateequity.com",
            ...     organization="PE Partners LLC",
            ...     response_pattern="structured_weekly",
            ...     decision_authority="investment_committee"
            ... )
        """
        metadata = {
            "sender_email": sender_email,
            "sender_domain": sender_domain or sender_email.split('@')[1] if '@' in sender_email else None,
            "organization": organization,
            "response_pattern": response_pattern,
            **kwargs
        }
        
        logger.info(f"Adding sender knowledge for: {sender_email}")
        return await self.add(content, metadata, KnowledgeType.SENDER, confidence)
    
    @log_function()
    async def add_email_type_knowledge(
        self,
        content: str,
        email_type: str,
        classification_criteria: Optional[str] = None,
        typical_patterns: Optional[List[str]] = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs
    ) -> str:
        """
        Add email type classification knowledge.
        
        Specialized method for adding knowledge about email types,
        classification criteria, and typical patterns for improved
        email categorization and processing automation.
        
        Args:
            content: Knowledge about the email type
            email_type: Type of email (investment_inquiry, due_diligence, etc.)
            classification_criteria: Criteria for identifying this email type
            typical_patterns: List of typical patterns for this email type
            confidence: Confidence level in the knowledge
            **kwargs: Additional email type metadata
            
        Returns:
            Knowledge ID of the created email type knowledge
        """
        metadata = {
            "email_type": email_type,
            "classification_criteria": classification_criteria,
            "typical_patterns": typical_patterns or [],
            **kwargs
        }
        
        logger.info(f"Adding email type knowledge: {email_type}")
        return await self.add(content, metadata, KnowledgeType.EMAIL_TYPE, confidence)
    
    @log_function()
    async def add_domain_knowledge(
        self,
        content: str,
        domain: str,
        expertise_area: str,
        industry_context: Optional[str] = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs
    ) -> str:
        """
        Add domain-specific expertise and industry knowledge.
        
        Specialized method for adding industry expertise, domain knowledge,
        and business intelligence for improved decision support and
        context understanding.
        
        Args:
            content: Domain expertise content
            domain: Knowledge domain (real_estate, private_equity, etc.)
            expertise_area: Specific area of expertise
            industry_context: Industry context and background
            confidence: Confidence level in the knowledge
            **kwargs: Additional domain metadata
            
        Returns:
            Knowledge ID of the created domain knowledge
        """
        metadata = {
            "domain": domain,
            "expertise_area": expertise_area,
            "industry_context": industry_context,
            **kwargs
        }
        
        logger.info(f"Adding domain knowledge: {domain}/{expertise_area}")
        return await self.add(content, metadata, KnowledgeType.DOMAIN, confidence)
    
    @log_function()
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        knowledge_type: Optional[KnowledgeType] = None,
        min_confidence: Optional[KnowledgeConfidence] = None
    ) -> List[MemoryItem]:
        """
        Search semantic knowledge with complete filtering.
        
        Performs semantic search across knowledge base with knowledge type
        filtering, confidence thresholds, and business context matching
        for asset management environments.
        
        Args:
            query: The search query for semantic matching
            limit: Maximum number of results to return
            filter: Additional metadata filters to apply
            knowledge_type: Filter by specific knowledge type
            min_confidence: Minimum confidence level filter
            
        Returns:
            List of matching knowledge items ordered by relevance
            
        Example:
            >>> # Search for sender knowledge about response patterns
            >>> results = await semantic_memory.search(
            ...     query="response time communication pattern",
            ...     knowledge_type=KnowledgeType.SENDER,
            ...     min_confidence=KnowledgeConfidence.MEDIUM
            ... )
        """
        logger.info(f"Searching semantic knowledge: query='{query}', limit={limit}")
        
        try:
            # Build complete filter conditions
            filter_conditions = {
                "must": [
                    {"key": "metadata.type", "match": {"value": "knowledge"}}
                ]
            }
            
            # Knowledge type filter
            if knowledge_type:
                filter_conditions["must"].append({
                    "key": "metadata.knowledge_type",
                    "match": {"value": knowledge_type.value}
                })
            
            # Minimum confidence filter
            if min_confidence:
                confidence_values = [conf.value for conf in KnowledgeConfidence]
                min_index = confidence_values.index(min_confidence.value)
                allowed_values = confidence_values[min_index:]
                
                filter_conditions["must"].append({
                    "key": "metadata.confidence",
                    "match": {"any": allowed_values}
                })
            
            # Additional custom filters
            if filter:
                if "must" in filter:
                    filter_conditions["must"].extend(filter["must"])
                else:
                    filter_conditions["must"].append(filter)
            
            # Perform semantic search
            results = await super().search(query, limit, filter_conditions)
            
            logger.info(f"Found {len(results)} semantic knowledge items matching query")
            logger.debug(f"Knowledge search results preview: {[r.id for r in results[:3]]}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching semantic knowledge: {e}")
            return []
    
    @log_function()
    async def search_sender_knowledge(
        self,
        sender_email: str,
        limit: int = 5
    ) -> List[MemoryItem]:
        """
        Search knowledge about a specific sender.
        
        Retrieves all available knowledge about a specific email sender
        for relationship context and communication intelligence.
        
        Args:
            sender_email: Email address to search knowledge for
            limit: Maximum number of results to return
            
        Returns:
            List of knowledge items about the specified sender
        """
        logger.info(f"Searching sender knowledge for: {sender_email}")
        
        sender_filter = {
            "key": "metadata.sender_email",
            "match": {"value": sender_email}
        }
        
        return await self.search(
            query=sender_email,
            limit=limit,
            filter=sender_filter,
            knowledge_type=KnowledgeType.SENDER
        )
    
    @log_function()
    async def search_by_domain(
        self,
        domain: str,
        limit: int = 10
    ) -> List[MemoryItem]:
        """
        Search knowledge by domain or organization.
        
        Retrieves knowledge related to a specific domain or organization
        for business intelligence and relationship context.
        
        Args:
            domain: Domain or organization to search for
            limit: Maximum number of results to return
            
        Returns:
            List of knowledge items related to the domain
        """
        logger.info(f"Searching domain knowledge for: {domain}")
        
        domain_filter = {
            "must": [
                {
                    "should": [
                        {"key": "metadata.sender_domain", "match": {"value": domain}},
                        {"key": "metadata.organization", "match": {"text": domain}},
                        {"key": "metadata.domain", "match": {"value": domain}}
                    ]
                }
            ]
        }
        
        return await self.search(
            query=domain,
            limit=limit,
            filter=domain_filter
        )
    
    @log_function()
    async def get_knowledge_statistics(self) -> Dict[str, Any]:
        """
        Get complete statistics about semantic knowledge.
        
        Provides business intelligence metrics about knowledge patterns,
        types, and confidence for knowledge management and optimization.
        
        Returns:
            Dictionary containing knowledge statistics and insights
        """
        logger.info("Generating semantic knowledge statistics")
        
        try:
            # Get all knowledge for analysis
            all_knowledge = await super().search(query="*", limit=1000)
            
            if not all_knowledge:
                return {
                    "total_count": 0,
                    "knowledge_types": {},
                    "confidence_distribution": {},
                    "average_content_length": 0
                }
            
            # Initialize statistics
            stats = {
                "total_count": len(all_knowledge),
                "knowledge_types": {},
                "confidence_distribution": {},
                "sender_knowledge_count": 0,
                "domain_knowledge_count": 0,
                "average_content_length": 0,
                "top_domains": {},
                "top_organizations": {}
            }
            
            # Analyze knowledge items
            total_length = 0
            
            for knowledge in all_knowledge:
                metadata = knowledge.metadata
                
                # Content length analysis
                total_length += len(knowledge.content)
                
                # Knowledge type distribution
                knowledge_type = metadata.get("knowledge_type", "unknown")
                stats["knowledge_types"][knowledge_type] = stats["knowledge_types"].get(knowledge_type, 0) + 1
                
                # Confidence distribution
                confidence = metadata.get("confidence", "unknown")
                stats["confidence_distribution"][confidence] = stats["confidence_distribution"].get(confidence, 0) + 1
                
                # Sender and domain analysis
                if knowledge_type == "sender":
                    stats["sender_knowledge_count"] += 1
                    
                    sender_domain = metadata.get("sender_domain")
                    if sender_domain:
                        stats["top_domains"][sender_domain] = stats["top_domains"].get(sender_domain, 0) + 1
                    
                    organization = metadata.get("organization")
                    if organization:
                        stats["top_organizations"][organization] = stats["top_organizations"].get(organization, 0) + 1
                
                elif knowledge_type == "domain":
                    stats["domain_knowledge_count"] += 1
            
            # Calculate derived statistics
            stats["average_content_length"] = total_length / len(all_knowledge) if all_knowledge else 0
            
            # Find most common items
            if stats["knowledge_types"]:
                stats["most_common_type"] = max(stats["knowledge_types"], key=stats["knowledge_types"].get)
            
            if stats["top_domains"]:
                stats["most_documented_domain"] = max(stats["top_domains"], key=stats["top_domains"].get)
            
            logger.info(f"Generated statistics for {stats['total_count']} knowledge items")
            return stats
            
        except Exception as e:
            logger.error(f"Error generating knowledge statistics: {e}")
            return {
                "total_count": 0,
                "error": str(e)
            }

# Demonstration and testing functions
@log_function()
async def demo_semantic_memory() -> None:
    """
    Demonstration of semantic memory system capabilities.
    
    Showcases the semantic knowledge features including
    sender intelligence, email type classification, domain expertise,
    and knowledge search for asset management environments.
    """
    logger.info("Starting SemanticMemory demonstration")
    
    semantic_memory = SemanticMemory()
    
    try:
        # Add sample sender knowledge
        logger.info("Adding sample sender knowledge...")
        
        sender_id = await semantic_memory.add_sender_knowledge(
            content="Responds within 2 hours during business hours, prefers detailed technical analysis in investment proposals",
            sender_email="investment@blackstone.com",
            sender_domain="blackstone.com",
            organization="Blackstone Group",
            response_pattern="fast_business_hours",
            decision_authority="investment_committee",
            preferred_communication="technical_detailed"
        )
        
        # Add email type knowledge
        logger.info("Adding email type knowledge...")
        
        email_type_id = await semantic_memory.add_email_type_knowledge(
            content="Investment inquiries typically include fund size, target returns, and investment timeline",
            email_type="investment_inquiry",
            classification_criteria="mentions fund, investment, capital, returns",
            typical_patterns=["fund size", "target return", "investment timeline", "due diligence"],
            confidence=KnowledgeConfidence.HIGH
        )
        
        # Add domain knowledge
        logger.info("Adding domain expertise...")
        
        domain_id = await semantic_memory.add_domain_knowledge(
            content="Real estate private equity typically requires 6-12 month due diligence periods for large transactions ($100M+)",
            domain="real_estate",
            expertise_area="private_equity_due_diligence",
            industry_context="commercial_real_estate",
            confidence=KnowledgeConfidence.HIGH
        )
        
        logger.info("✓ Added sample semantic knowledge")
        
        # Test knowledge search
        logger.info("Testing knowledge search capabilities...")
        
        search_results = await semantic_memory.search(
            query="investment response time",
            knowledge_type=KnowledgeType.SENDER,
            limit=5
        )
        
        logger.info(f"Found {len(search_results)} results for investment response time")
        for result in search_results:
            knowledge_type = result.metadata.get("knowledge_type", "unknown")
            confidence = result.metadata.get("confidence", "unknown")
            logger.info(f"  - {knowledge_type} ({confidence}): {result.content[:80]}...")
        
        # Test sender-specific search
        logger.info("Testing sender-specific knowledge search...")
        
        sender_results = await semantic_memory.search_sender_knowledge(
            sender_email="investment@blackstone.com"
        )
        
        logger.info(f"Found {len(sender_results)} knowledge items about investment@blackstone.com")
        
        # Test domain search
        logger.info("Testing domain knowledge search...")
        
        domain_results = await semantic_memory.search_by_domain(
            domain="blackstone.com",
            limit=10
        )
        
        logger.info(f"Found {len(domain_results)} knowledge items related to blackstone.com")
        
        # Generate knowledge statistics
        logger.info("Generating knowledge statistics...")
        
        stats = await semantic_memory.get_knowledge_statistics()
        logger.info(f"Knowledge statistics:")
        logger.info(f"  - Total knowledge items: {stats['total_count']}")
        logger.info(f"  - Knowledge types: {stats['knowledge_types']}")
        logger.info(f"  - Confidence distribution: {stats['confidence_distribution']}")
        logger.info(f"  - Sender knowledge: {stats['sender_knowledge_count']}")
        logger.info(f"  - Domain knowledge: {stats['domain_knowledge_count']}")
        
        if stats.get('most_common_type'):
            logger.info(f"  - Most common type: {stats['most_common_type']}")
        
        logger.info("SemanticMemory demonstration completed successfully")
        
    except Exception as e:
        logger.error(f"SemanticMemory demonstration failed: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_semantic_memory()) 
"""
Procedural Memory System for EmailAgent

procedural memory system for private market asset management environments.
Provides rule storage, procedure management, and workflow automation with
pattern matching and business logic execution capabilities.

Features:
    - Business rule storage and management
    - Workflow procedure and automation patterns
    - Decision criteria and approval workflows
    - Compliance rule enforcement and validation
    - Process optimization and learning capabilities
    - rule confidence scoring

Business Context:
    Designed for asset management firms requiring procedural
    knowledge management for investment workflows, compliance procedures,
    operational standards, and decision automation. Maintains institutional
    knowledge about business processes and decision criteria.

Technical Architecture:
    - Qdrant-based vector storage for procedural knowledge
    - Rule categorization with priority and confidence scoring
    - Procedure search with business context filtering
    - Rule lifecycle management and versioning
    - Performance optimization for rule retrieval

Rule Types:
    - Investment: Investment decision and approval rules
    - Compliance: Regulatory and compliance procedures
    - Operational: Daily operational procedures and standards
    - Communication: Communication protocols and procedures
    - Approval: Approval workflows and decision criteria
    - Classification: Document and email classification rules

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import os

# Logging system
import sys
from datetime import UTC, datetime
from enum import Enum
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function

from .base import BaseMemory, MemoryItem

# Initialize logger
logger = get_logger(__name__)


class RuleType(Enum):
    """
    rule classification for procedural memory.

    Provides structured categorization of business rules and procedures
    for asset management environments with appropriate business context
    and workflow integration.

    Values:
        INVESTMENT: Investment decision and approval rules
        COMPLIANCE: Regulatory and compliance procedures
        OPERATIONAL: Daily operational procedures and standards
        COMMUNICATION: Communication protocols and procedures
        APPROVAL: Approval workflows and decision criteria
        CLASSIFICATION: Document and email classification rules
        ROUTING: Email routing and assignment rules
        VALIDATION: Data validation and quality rules
        UNKNOWN: Unclassified rules requiring review
    """

    INVESTMENT = "investment"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    COMMUNICATION = "communication"
    APPROVAL = "approval"
    CLASSIFICATION = "classification"
    ROUTING = "routing"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class RulePriority(Enum):
    """
    Rule priority levels for procedural memory execution.

    Provides priority classification for rule execution order
    and business process automation workflows.

    Values:
        CRITICAL: Critical rules that must be executed first
        HIGH: High priority rules for important processes
        MEDIUM: Standard priority rules for normal operations
        LOW: Low priority rules for optional processes
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleConfidence(Enum):
    """
    Rule confidence levels for procedural memory quality assessment.

    Provides graduated confidence scoring for rule accuracy
    to support rule quality management and validation workflows.

    Values:
        VERIFIED: Rules verified through testing and validation
        TESTED: Rules tested but requiring additional validation
        DRAFT: Draft rules under development and review
        EXPERIMENTAL: Experimental rules under evaluation
    """

    VERIFIED = "verified"
    TESTED = "tested"
    DRAFT = "draft"
    EXPERIMENTAL = "experimental"


class ProceduralMemory(BaseMemory):
    """
    procedural memory system for asset management environments.

    Provides complete rule storage and procedure management with
    business logic execution designed for private market asset management
    firms requiring workflow automation and decision support.

    Features:
        - Business rule storage and categorization
        - Workflow procedure and automation management
        - Decision criteria and approval workflow rules
        - Compliance rule enforcement and validation
        - Rule priority and confidence scoring
        - Procedure optimization and learning capabilities

    Business Context:
        Enables asset management firms to maintain institutional knowledge
        about business processes, decision criteria, compliance procedures,
        and operational standards for improved automation and consistency.

    Technical Implementation:
        - Dedicated Qdrant collection for procedural knowledge
        - Rule categorization with priority and confidence scoring
        - Vector semantic search with business context filtering
        - Rule lifecycle management and versioning
        - audit trail and rule execution tracking
    """

    def __init__(
        self,
        max_items: int | None = 1000,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize procedural memory system.

        Args:
            max_items: Maximum number of rules to store (default: 1000)
            qdrant_url: Qdrant database connection URL
            embedding_model: Sentence transformer model for embeddings
        """
        super().__init__(
            max_items=max_items, qdrant_url=qdrant_url, embedding_model=embedding_model
        )
        self.collection_name = "procedural"
        logger.info(f"Initialized ProceduralMemory with max_items={max_items}")

    @log_function()
    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        rule_type: RuleType = RuleType.UNKNOWN,
        priority: RulePriority = RulePriority.MEDIUM,
        confidence: RuleConfidence = RuleConfidence.DRAFT,
    ) -> str:
        """
        Add new rule or procedure to procedural memory.

        Creates procedural entries with automatic categorization, priority
        assignment, and confidence scoring for asset management
        environments.

        Args:
            content: The rule or procedure content to store
            metadata: Additional metadata for business context
            rule_type: Type of rule for categorization
            priority: Priority level for rule execution
            confidence: Confidence level in the rule accuracy

        Returns:
            The ID of the created rule item

        Raises:
            ValueError: If content is empty or invalid

        Example:
            >>> rule_id = await procedural_memory.add(
            ...     content="Investment committee approval required for deals > $50M",
            ...     metadata={
            ...         "threshold_amount": 50000000,
            ...         "approval_body": "investment_committee",
            ...         "applies_to": "all_investments"
            ...     },
            ...     rule_type=RuleType.INVESTMENT,
            ...     priority=RulePriority.CRITICAL,
            ...     confidence=RuleConfidence.VERIFIED
            ... )
        """
        if not content or not isinstance(content, str):
            raise ValueError("Rule content must be a non-empty string")

        if metadata is None:
            metadata = {}

        # Set complete rule metadata
        metadata["type"] = "rule"
        metadata["rule_type"] = rule_type.value
        metadata["priority"] = priority.value
        metadata["confidence"] = confidence.value
        metadata["created_at"] = datetime.now(UTC).isoformat()
        metadata["source"] = "procedural_memory"
        metadata["version"] = "1.0.0"
        metadata["active"] = True

        logger.info(
            f"Adding procedural rule: type={rule_type.value}, priority={priority.value}"
        )
        logger.debug(f"Rule content length: {len(content)}")

        try:
            result = await super().add(content, metadata)
            logger.info(f"Successfully added procedural rule: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to add procedural rule: {e}")
            raise

    @log_function()
    async def add_investment_rule(
        self,
        content: str,
        rule_name: str,
        threshold_amount: float | None = None,
        approval_required: bool = True,
        priority: RulePriority = RulePriority.HIGH,
        **kwargs,
    ) -> str:
        """
        Add investment-specific rule with financial criteria.

        Specialized method for adding investment decision rules,
        approval workflows, and financial thresholds for asset
        management investment processes.

        Args:
            content: Investment rule content
            rule_name: Descriptive name for the rule
            threshold_amount: Financial threshold for rule application
            approval_required: Whether approval is required
            priority: Rule priority level
            **kwargs: Additional investment rule metadata

        Returns:
            Rule ID of the created investment rule

        Example:
            >>> investment_rule_id = await procedural_memory.add_investment_rule(
            ...     content="All real estate investments require property appraisal and market analysis",
            ...     rule_name="real_estate_due_diligence",
            ...     threshold_amount=1000000,
            ...     approval_required=True,
            ...     sector="real_estate",
            ...     required_docs=["appraisal", "market_analysis"]
            ... )
        """
        metadata = {
            "rule_name": rule_name,
            "threshold_amount": threshold_amount,
            "approval_required": approval_required,
            **kwargs,
        }

        logger.info(f"Adding investment rule: {rule_name}")
        return await self.add(
            content, metadata, RuleType.INVESTMENT, priority, RuleConfidence.VERIFIED
        )

    @log_function()
    async def add_compliance_rule(
        self,
        content: str,
        rule_name: str,
        regulation_source: str,
        mandatory: bool = True,
        **kwargs,
    ) -> str:
        """
        Add compliance rule with regulatory context.

        Specialized method for adding regulatory compliance rules,
        mandatory procedures, and regulatory requirements for
        asset management compliance workflows.

        Args:
            content: Compliance rule content
            rule_name: Descriptive name for the rule
            regulation_source: Source regulation or standard
            mandatory: Whether compliance is mandatory
            **kwargs: Additional compliance rule metadata

        Returns:
            Rule ID of the created compliance rule
        """
        metadata = {
            "rule_name": rule_name,
            "regulation_source": regulation_source,
            "mandatory": mandatory,
            **kwargs,
        }

        logger.info(
            f"Adding compliance rule: {rule_name} (source: {regulation_source})"
        )
        return await self.add(
            content,
            metadata,
            RuleType.COMPLIANCE,
            RulePriority.CRITICAL if mandatory else RulePriority.HIGH,
            RuleConfidence.VERIFIED,
        )

    @log_function()
    async def add_classification_rule(
        self,
        content: str,
        rule_name: str,
        classification_criteria: str,
        target_category: str,
        confidence_threshold: float = 0.7,
        **kwargs,
    ) -> str:
        """
        Add email/document classification rule.

        Specialized method for adding classification rules for
        automated email and document categorization in asset
        management workflows.

        Args:
            content: Classification rule content
            rule_name: Descriptive name for the rule
            classification_criteria: Criteria for classification
            target_category: Target classification category
            confidence_threshold: Minimum confidence for classification
            **kwargs: Additional classification rule metadata

        Returns:
            Rule ID of the created classification rule
        """
        metadata = {
            "rule_name": rule_name,
            "classification_criteria": classification_criteria,
            "target_category": target_category,
            "confidence_threshold": confidence_threshold,
            **kwargs,
        }

        logger.info(f"Adding classification rule: {rule_name} -> {target_category}")
        return await self.add(
            content,
            metadata,
            RuleType.CLASSIFICATION,
            RulePriority.MEDIUM,
            RuleConfidence.TESTED,
        )

    @log_function()
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: dict[str, Any] | None = None,
        rule_type: RuleType | None = None,
        min_priority: RulePriority | None = None,
        min_confidence: RuleConfidence | None = None,
        active_only: bool = True,
    ) -> list[MemoryItem]:
        """
        Search procedural rules with complete filtering.

        Performs semantic search across rule base with rule type
        filtering, priority thresholds, and business context matching
        for asset management environments.

        Args:
            query: The search query for semantic matching
            limit: Maximum number of results to return
            filter: Additional metadata filters to apply
            rule_type: Filter by specific rule type
            min_priority: Minimum priority level filter
            min_confidence: Minimum confidence level filter
            active_only: Filter for active rules only

        Returns:
            List of matching rule items ordered by relevance and priority

        Example:
            >>> # Search for investment approval rules
            >>> results = await procedural_memory.search(
            ...     query="investment approval threshold",
            ...     rule_type=RuleType.INVESTMENT,
            ...     min_priority=RulePriority.HIGH
            ... )
        """
        logger.info(f"Searching procedural rules: query='{query}', limit={limit}")

        try:
            # Build complete filter conditions
            filter_conditions = {
                "must": [{"key": "metadata.type", "match": {"value": "rule"}}]
            }

            # Active rules filter
            if active_only:
                filter_conditions["must"].append(
                    {"key": "metadata.active", "match": {"value": True}}
                )

            # Rule type filter
            if rule_type:
                filter_conditions["must"].append(
                    {"key": "metadata.rule_type", "match": {"value": rule_type.value}}
                )

            # Priority filter
            if min_priority:
                priority_values = [p.value for p in RulePriority]
                min_index = priority_values.index(min_priority.value)
                allowed_values = priority_values[
                    : min_index + 1
                ]  # Higher priority = earlier in list

                filter_conditions["must"].append(
                    {"key": "metadata.priority", "match": {"any": allowed_values}}
                )

            # Confidence filter
            if min_confidence:
                confidence_values = [c.value for c in RuleConfidence]
                min_index = confidence_values.index(min_confidence.value)
                allowed_values = confidence_values[min_index:]

                filter_conditions["must"].append(
                    {"key": "metadata.confidence", "match": {"any": allowed_values}}
                )

            # Additional custom filters
            if filter:
                if "must" in filter:
                    filter_conditions["must"].extend(filter["must"])
                else:
                    filter_conditions["must"].append(filter)

            # Perform semantic search
            results = await super().search(query, limit, filter_conditions)

            # Sort by priority (critical first, then high, etc.)
            priority_order = {p.value: i for i, p in enumerate(RulePriority)}
            results.sort(
                key=lambda r: priority_order.get(r.metadata.get("priority", "low"), 999)
            )

            logger.info(f"Found {len(results)} procedural rules matching query")
            logger.debug(f"Rule search results preview: {[r.id for r in results[:3]]}")

            return results

        except Exception as e:
            logger.error(f"Error searching procedural rules: {e}")
            return []

    @log_function()
    async def search_by_rule_type(
        self,
        rule_type: RuleType,
        limit: int = 10,
        min_priority: RulePriority | None = None,
    ) -> list[MemoryItem]:
        """
        Search rules by specific type with priority filtering.

        Retrieves all rules of a specific type for workflow
        automation and decision support applications.

        Args:
            rule_type: Type of rules to search for
            limit: Maximum number of results to return
            min_priority: Minimum priority level filter

        Returns:
            List of rules of the specified type
        """
        logger.info(f"Searching rules by type: {rule_type.value}")

        return await self.search(
            query=rule_type.value,
            limit=limit,
            rule_type=rule_type,
            min_priority=min_priority,
        )

    @log_function()
    async def get_critical_rules(self, limit: int = 20) -> list[MemoryItem]:
        """
        Get all critical priority rules for workflow automation.

        Retrieves critical rules that must be executed first
        in automated workflows and decision processes.

        Args:
            limit: Maximum number of critical rules to return

        Returns:
            List of critical priority rules
        """
        logger.info("Retrieving critical priority rules")

        return await self.search(
            query="*", limit=limit, min_priority=RulePriority.CRITICAL  # Match all
        )

    @log_function()
    async def deactivate_rule(self, rule_id: str) -> bool:
        """
        Deactivate a rule without deleting it.

        Marks a rule as inactive for rule lifecycle management
        while preserving historical rule information.

        Args:
            rule_id: ID of the rule to deactivate

        Returns:
            True if rule was successfully deactivated
        """
        logger.info(f"Deactivating rule: {rule_id}")

        try:
            # Get the rule
            rule_item = await super().get_item(rule_id)
            if not rule_item:
                logger.warning(f"Rule not found for deactivation: {rule_id}")
                return False

            # Update metadata to mark as inactive
            rule_item.metadata["active"] = False
            rule_item.metadata["deactivated_at"] = datetime.now(UTC).isoformat()

            # Update in database
            await super().update_item(rule_id, rule_item)

            logger.info(f"Successfully deactivated rule: {rule_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating rule {rule_id}: {e}")
            return False

    @log_function()
    async def get_rule_statistics(self) -> dict[str, Any]:
        """
        Get complete statistics about procedural rules.

        Provides business intelligence metrics about rule patterns,
        types, and priorities for rule management and optimization.

        Returns:
            Dictionary containing rule statistics and insights
        """
        logger.info("Generating procedural rule statistics")

        try:
            # Get all rules for analysis
            all_rules = await super().search(query="*", limit=1000)

            if not all_rules:
                return {
                    "total_count": 0,
                    "rule_types": {},
                    "priority_distribution": {},
                    "confidence_distribution": {},
                    "active_count": 0,
                }

            # Initialize statistics
            stats = {
                "total_count": len(all_rules),
                "rule_types": {},
                "priority_distribution": {},
                "confidence_distribution": {},
                "active_count": 0,
                "inactive_count": 0,
                "average_content_length": 0,
                "rules_by_category": {},
            }

            # Analyze rules
            total_length = 0

            for rule in all_rules:
                metadata = rule.metadata

                # Content length analysis
                total_length += len(rule.content)

                # Active/inactive status
                if metadata.get("active", True):
                    stats["active_count"] += 1
                else:
                    stats["inactive_count"] += 1

                # Rule type distribution
                rule_type = metadata.get("rule_type", "unknown")
                stats["rule_types"][rule_type] = (
                    stats["rule_types"].get(rule_type, 0) + 1
                )

                # Priority distribution
                priority = metadata.get("priority", "medium")
                stats["priority_distribution"][priority] = (
                    stats["priority_distribution"].get(priority, 0) + 1
                )

                # Confidence distribution
                confidence = metadata.get("confidence", "draft")
                stats["confidence_distribution"][confidence] = (
                    stats["confidence_distribution"].get(confidence, 0) + 1
                )

            # Calculate derived statistics
            stats["average_content_length"] = (
                total_length / len(all_rules) if all_rules else 0
            )

            # Find most common items
            if stats["rule_types"]:
                stats["most_common_type"] = max(
                    stats["rule_types"], key=stats["rule_types"].get
                )

            if stats["priority_distribution"]:
                stats["most_common_priority"] = max(
                    stats["priority_distribution"],
                    key=stats["priority_distribution"].get,
                )

            logger.info(
                f"Generated statistics for {stats['total_count']} procedural rules"
            )
            return stats

        except Exception as e:
            logger.error(f"Error generating rule statistics: {e}")
            return {"total_count": 0, "error": str(e)}


# Demonstration and testing functions
@log_function()
async def demo_procedural_memory() -> None:
    """
    Demonstration of procedural memory system capabilities.

    Showcases the procedural rule features including
    investment rules, compliance procedures, classification rules,
    and workflow automation for asset management environments.
    """
    logger.info("Starting ProceduralMemory demonstration")

    procedural_memory = ProceduralMemory()

    try:
        # Add sample investment rules
        logger.info("Adding sample investment rules...")

        investment_rule_id = await procedural_memory.add_investment_rule(
            content="Investment committee approval required for any single investment exceeding $50M",
            rule_name="large_investment_approval",
            threshold_amount=50000000,
            approval_required=True,
            sector="all",
            approval_body="investment_committee",
        )

        # Add compliance rule
        logger.info("Adding compliance rule...")

        compliance_rule_id = await procedural_memory.add_compliance_rule(
            content="All investment documents must be reviewed for anti-money laundering compliance",
            rule_name="aml_document_review",
            regulation_source="SEC_AML_Guidelines",
            mandatory=True,
            review_required=True,
        )

        # Add classification rule
        logger.info("Adding classification rule...")

        classification_rule_id = await procedural_memory.add_classification_rule(
            content="Emails containing 'due diligence', 'investment proposal', or 'fund performance' should be classified as investment_related",
            rule_name="investment_email_classification",
            classification_criteria="keywords: due diligence, investment proposal, fund performance",
            target_category="investment_related",
            confidence_threshold=0.8,
        )

        logger.info("✓ Added sample procedural rules")

        # Test rule search
        logger.info("Testing rule search capabilities...")

        search_results = await procedural_memory.search(
            query="investment approval",
            rule_type=RuleType.INVESTMENT,
            min_priority=RulePriority.HIGH,
        )

        logger.info(f"Found {len(search_results)} investment approval rules")
        for result in search_results:
            rule_type = result.metadata.get("rule_type", "unknown")
            priority = result.metadata.get("priority", "unknown")
            logger.info(f"  - {rule_type} ({priority}): {result.content[:80]}...")

        # Test critical rules retrieval
        logger.info("Testing critical rules retrieval...")

        critical_rules = await procedural_memory.get_critical_rules(limit=10)

        logger.info(f"Found {len(critical_rules)} critical priority rules")

        # Test rule type search
        logger.info("Testing compliance rule search...")

        compliance_rules = await procedural_memory.search_by_rule_type(
            rule_type=RuleType.COMPLIANCE, limit=5
        )

        logger.info(f"Found {len(compliance_rules)} compliance rules")

        # Generate rule statistics
        logger.info("Generating rule statistics...")

        stats = await procedural_memory.get_rule_statistics()
        logger.info("Rule statistics:")
        logger.info(f"  - Total rules: {stats['total_count']}")
        logger.info(f"  - Active rules: {stats['active_count']}")
        logger.info(f"  - Rule types: {stats['rule_types']}")
        logger.info(f"  - Priority distribution: {stats['priority_distribution']}")
        logger.info(f"  - Confidence distribution: {stats['confidence_distribution']}")

        if stats.get("most_common_type"):
            logger.info(f"  - Most common type: {stats['most_common_type']}")

        # Test rule deactivation
        logger.info("Testing rule deactivation...")

        deactivation_success = await procedural_memory.deactivate_rule(
            classification_rule_id
        )
        logger.info(f"Rule deactivation successful: {deactivation_success}")

        logger.info("ProceduralMemory demonstration completed successfully")

    except Exception as e:
        logger.error(f"ProceduralMemory demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # # Standard library imports
    import asyncio

    asyncio.run(demo_procedural_memory())

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
        max_items: int | None = None,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize semantic memory system.

        Args:
            max_items: Maximum number of knowledge items to store (uses config default if None)
            qdrant_url: Qdrant database connection URL
            embedding_model: Sentence transformer model for embeddings
        """
        super().__init__(
            max_items=max_items, qdrant_url=qdrant_url, embedding_model=embedding_model
        )
        self.collection_name = "semantic"
        logger.info(f"Initialized SemanticMemory with max_items={self.max_items}")

    @log_function()
    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        knowledge_type: KnowledgeType = KnowledgeType.UNKNOWN,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
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
        metadata["content_hash"] = await self._generate_content_hash(content)

        logger.info(
            f"Adding semantic knowledge: type={knowledge_type.value}, confidence={confidence.value}"
        )
        logger.debug(f"Knowledge content length: {len(content)}")

        # Check for duplicates before adding
        duplicate_id = await self._check_for_duplicate(
            content, knowledge_type, metadata
        )
        if duplicate_id:
            logger.info(
                f"Duplicate content detected, returning existing ID: {duplicate_id}"
            )
            return duplicate_id

        # Check for conflicts with existing knowledge
        conflicts = await self._detect_conflicts(content, knowledge_type, metadata)
        if conflicts:
            # Handle conflicts based on resolution strategy
            resolution_result = await self._resolve_conflicts(
                content, knowledge_type, metadata, conflicts, confidence
            )
            if resolution_result["action"] == "reject":
                logger.warning(
                    f"Content rejected due to conflicts: {resolution_result['reason']}"
                )
                return resolution_result["existing_id"]
            elif resolution_result["action"] == "update":
                logger.info(
                    f"Updating existing knowledge due to conflicts: {resolution_result['reason']}"
                )
                # Update the existing knowledge item
                await self._update_conflicting_knowledge(resolution_result)
                return resolution_result["existing_id"]
            # If action == "add", continue with normal addition

        try:
            result = await super().add(content, metadata)
            logger.info(f"Successfully added semantic knowledge: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to add semantic knowledge: {e}")
            raise

    async def _generate_content_hash(self, content: str) -> str:
        """
        Generate a hash of the content for duplicate detection.

        Args:
            content: The content to hash

        Returns:
            SHA-256 hash of the normalized content
        """
        # # Standard library imports
        import hashlib

        # Normalize content for consistent hashing
        normalized_content = content.strip().lower()
        return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()

    async def _check_for_duplicate(
        self, content: str, knowledge_type: KnowledgeType, metadata: dict[str, Any]
    ) -> str | None:
        """
        Check if content already exists in semantic memory.

        Uses content hashing and semantic search to detect duplicates.

        Args:
            content: Content to check for duplicates
            knowledge_type: Type of knowledge being added
            metadata: Metadata for the content

        Returns:
            ID of existing duplicate if found, None otherwise
        """
        try:
            # Method 1: Content hash-based duplicate detection
            content_hash = await self._generate_content_hash(content)

            # Search for existing content with same hash
            hash_filter = {
                "key": "metadata.content_hash",
                "match": {"value": content_hash},
            }

            hash_results = await self.search(
                query=content[:50],  # Use first 50 chars as query
                limit=5,
                filter=hash_filter,
                knowledge_type=knowledge_type,
            )

            if hash_results:
                logger.debug(f"Found exact content hash match: {hash_results[0].id}")
                return hash_results[0].id

            # Method 2: Asset-specific duplicate detection for asset knowledge
            if knowledge_type == KnowledgeType.UNKNOWN and metadata.get("asset_id"):
                asset_filter = {
                    "key": "metadata.asset_id",
                    "match": {"value": metadata["asset_id"]},
                }

                asset_results = await self.search(
                    query=f"Asset: {metadata.get('deal_name', '')}",
                    limit=3,
                    filter=asset_filter,
                    knowledge_type=knowledge_type,
                )

                if asset_results:
                    logger.debug(
                        f"Found asset-specific duplicate: {asset_results[0].id}"
                    )
                    return asset_results[0].id

            # Method 3: File type duplicate detection for file validation rules
            if knowledge_type == KnowledgeType.RULE and metadata.get("file_extension"):
                file_filter = {
                    "key": "metadata.file_extension",
                    "match": {"value": metadata["file_extension"]},
                }

                file_results = await self.search(
                    query=f"file type {metadata['file_extension']}",
                    limit=3,
                    filter=file_filter,
                    knowledge_type=knowledge_type,
                )

                if file_results:
                    logger.debug(f"Found file type duplicate: {file_results[0].id}")
                    return file_results[0].id

            # No duplicates found
            return None

        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            # If duplicate checking fails, continue with adding to be safe
            return None

    async def _detect_conflicts(
        self, content: str, knowledge_type: KnowledgeType, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect conflicts with existing knowledge.

        Checks for contradictory information that would create inconsistencies
        in the knowledge base, such as same asset with different types.

        Args:
            content: Content to check for conflicts
            knowledge_type: Type of knowledge being added
            metadata: Metadata for the content

        Returns:
            List of conflict dictionaries with details about conflicting items
        """
        conflicts = []

        try:
            # Asset classification conflicts
            if metadata.get("asset_id"):
                asset_conflicts = await self._detect_asset_conflicts(
                    metadata["asset_id"], content, metadata
                )
                conflicts.extend(asset_conflicts)

            # File type rule conflicts
            if knowledge_type == KnowledgeType.RULE and metadata.get("file_extension"):
                file_conflicts = await self._detect_file_type_conflicts(
                    metadata["file_extension"], content, metadata
                )
                conflicts.extend(file_conflicts)

            # Sender information conflicts
            if knowledge_type == KnowledgeType.SENDER and metadata.get("sender_email"):
                sender_conflicts = await self._detect_sender_conflicts(
                    metadata["sender_email"], content, metadata
                )
                conflicts.extend(sender_conflicts)

            # Business rule conflicts
            if knowledge_type == KnowledgeType.RULE:
                rule_conflicts = await self._detect_rule_conflicts(content, metadata)
                conflicts.extend(rule_conflicts)

            logger.debug(f"Detected {len(conflicts)} potential conflicts")
            return conflicts

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []

    async def _detect_asset_conflicts(
        self, asset_id: str, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts in asset classification."""
        conflicts = []

        # Search for existing knowledge about this asset
        asset_filter = {"key": "metadata.asset_id", "match": {"value": asset_id}}

        existing_items = await self.search(
            query=f"Asset: {metadata.get('deal_name', '')}",
            limit=10,
            filter=asset_filter,
        )

        new_asset_type = metadata.get("asset_type")

        for item in existing_items:
            existing_type = item.metadata.get("asset_type")

            # Check for asset type conflicts
            if existing_type and new_asset_type and existing_type != new_asset_type:
                conflicts.append(
                    {
                        "type": "asset_type_conflict",
                        "asset_id": asset_id,
                        "existing_id": item.id,
                        "existing_type": existing_type,
                        "new_type": new_asset_type,
                        "existing_confidence": item.metadata.get(
                            "confidence", "unknown"
                        ),
                        "severity": "high",
                    }
                )

        return conflicts

    async def _detect_file_type_conflicts(
        self, file_extension: str, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts in file type validation rules."""
        conflicts = []

        file_filter = {
            "key": "metadata.file_extension",
            "match": {"value": file_extension},
        }

        existing_items = await self.search(
            query=f"file type {file_extension}",
            limit=5,
            filter=file_filter,
            knowledge_type=KnowledgeType.RULE,
        )

        new_is_allowed = metadata.get("is_allowed")
        new_security_level = metadata.get("security_level")

        for item in existing_items:
            existing_allowed = item.metadata.get("is_allowed")
            existing_security = item.metadata.get("security_level")

            # Check for permission conflicts
            if existing_allowed is not None and new_is_allowed is not None:
                if existing_allowed != new_is_allowed:
                    conflicts.append(
                        {
                            "type": "file_permission_conflict",
                            "file_extension": file_extension,
                            "existing_id": item.id,
                            "existing_allowed": existing_allowed,
                            "new_allowed": new_is_allowed,
                            "severity": "high",
                        }
                    )

            # Check for security level conflicts
            security_hierarchy = {
                "safe": 1,
                "standard": 2,
                "restricted": 3,
                "dangerous": 4,
            }
            if existing_security and new_security_level:
                existing_level = security_hierarchy.get(existing_security, 2)
                new_level = security_hierarchy.get(new_security_level, 2)

                if (
                    abs(existing_level - new_level) > 1
                ):  # More than one level difference
                    conflicts.append(
                        {
                            "type": "security_level_conflict",
                            "file_extension": file_extension,
                            "existing_id": item.id,
                            "existing_security": existing_security,
                            "new_security": new_security_level,
                            "severity": "medium",
                        }
                    )

        return conflicts

    async def _detect_sender_conflicts(
        self, sender_email: str, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts in sender information."""
        conflicts = []

        existing_items = await self.search_sender_knowledge(sender_email, limit=5)

        new_org = metadata.get("organization")

        for item in existing_items:
            existing_org = item.metadata.get("organization")

            # Check for organization conflicts
            if existing_org and new_org and existing_org.lower() != new_org.lower():
                conflicts.append(
                    {
                        "type": "sender_organization_conflict",
                        "sender_email": sender_email,
                        "existing_id": item.id,
                        "existing_organization": existing_org,
                        "new_organization": new_org,
                        "severity": "medium",
                    }
                )

        return conflicts

    async def _detect_rule_conflicts(
        self, content: str, metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect conflicts in business rules."""
        conflicts = []

        # This would check for contradictory business rules
        # Implementation depends on specific rule structures
        # For now, we'll focus on explicit contradictions in content

        contradiction_keywords = [
            ("always", "never"),
            ("required", "forbidden"),
            ("allowed", "prohibited"),
            ("must", "must not"),
        ]

        content_lower = content.lower()

        # Search for potentially contradictory rules
        rule_items = await self.search(
            query=content[:100],  # Use first 100 chars for similarity
            limit=10,
            knowledge_type=KnowledgeType.RULE,
        )

        for item in rule_items:
            existing_content = item.content.lower()

            # Check for explicit contradictions
            for positive, negative in contradiction_keywords:
                if positive in content_lower and negative in existing_content:
                    conflicts.append(
                        {
                            "type": "rule_contradiction",
                            "existing_id": item.id,
                            "contradiction": f"'{positive}' vs '{negative}'",
                            "severity": "high",
                        }
                    )
                elif negative in content_lower and positive in existing_content:
                    conflicts.append(
                        {
                            "type": "rule_contradiction",
                            "existing_id": item.id,
                            "contradiction": f"'{negative}' vs '{positive}'",
                            "severity": "high",
                        }
                    )

        return conflicts

    async def _resolve_conflicts(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        metadata: dict[str, Any],
        conflicts: list[dict[str, Any]],
        confidence: KnowledgeConfidence,
    ) -> dict[str, Any]:
        """
        Resolve conflicts using configurable strategies.

        Args:
            content: New content being added
            knowledge_type: Type of knowledge
            metadata: Metadata for new content
            conflicts: List of detected conflicts
            confidence: Confidence level of new content

        Returns:
            Resolution result with action to take
        """
        try:
            # Strategy 1: Confidence-based resolution
            for conflict in conflicts:
                existing_confidence = conflict.get("existing_confidence", "medium")

                # Convert confidence levels to numeric for comparison
                confidence_levels = {
                    "experimental": 1,
                    "low": 2,
                    "medium": 3,
                    "high": 4,
                }

                new_conf_level = confidence_levels.get(confidence.value, 3)
                existing_conf_level = confidence_levels.get(existing_confidence, 3)

                # High severity conflicts require manual review
                if conflict.get("severity") == "high":
                    logger.warning(f"High severity conflict detected: {conflict}")

                    # If new confidence is significantly higher, update
                    if new_conf_level > existing_conf_level + 1:
                        return {
                            "action": "update",
                            "existing_id": conflict["existing_id"],
                            "reason": f"Higher confidence ({confidence.value} vs {existing_confidence})",
                            "conflict_type": conflict["type"],
                            "new_content": content,
                            "new_metadata": metadata,
                        }
                    # If existing confidence is higher, reject new
                    elif existing_conf_level > new_conf_level:
                        return {
                            "action": "reject",
                            "existing_id": conflict["existing_id"],
                            "reason": f"Existing knowledge has higher confidence ({existing_confidence} vs {confidence.value})",
                            "conflict_type": conflict["type"],
                        }
                    # Equal confidence - log for human review
                    else:
                        logger.warning(f"Conflict requires human review: {conflict}")
                        await self._log_conflict_for_review(content, metadata, conflict)
                        return {
                            "action": "reject",
                            "existing_id": conflict["existing_id"],
                            "reason": "Equal confidence conflict - requires human review",
                            "conflict_type": conflict["type"],
                        }

            # If we get here, no blocking conflicts found
            return {"action": "add", "reason": "No blocking conflicts detected"}

        except Exception as e:
            logger.error(f"Error resolving conflicts: {e}")
            # On error, be conservative and reject
            return {
                "action": "reject",
                "reason": f"Error during conflict resolution: {e}",
                "existing_id": conflicts[0].get("existing_id") if conflicts else None,
            }

    async def _update_conflicting_knowledge(
        self, resolution_result: dict[str, Any]
    ) -> None:
        """Update existing knowledge item with new information."""
        try:
            existing_id = resolution_result["existing_id"]
            new_content = resolution_result["new_content"]
            new_metadata = resolution_result["new_metadata"]

            # Add conflict resolution metadata
            new_metadata["conflict_resolution"] = {
                "action": "updated_due_to_conflict",
                "reason": resolution_result["reason"],
                "conflict_type": resolution_result["conflict_type"],
                "updated_at": datetime.now(UTC).isoformat(),
            }

            # Update the existing item
            await super().update(existing_id, new_content, new_metadata)
            logger.info(
                f"Updated knowledge item {existing_id} due to conflict resolution"
            )

        except Exception as e:
            logger.error(f"Error updating conflicting knowledge: {e}")

    async def _log_conflict_for_review(
        self, content: str, metadata: dict[str, Any], conflict: dict[str, Any]
    ) -> None:
        """Log conflicts that require human review."""
        try:
            conflict_log = {
                "timestamp": datetime.now(UTC).isoformat(),
                "conflict_type": conflict["type"],
                "new_content": content[:200],  # First 200 chars
                "new_metadata": {
                    k: v for k, v in metadata.items() if k not in ["content_hash"]
                },
                "conflict_details": conflict,
                "status": "pending_review",
                "priority": conflict.get("severity", "medium"),
            }

            # Store in a special conflicts collection for human review
            await self.add(
                content=f"CONFLICT REVIEW NEEDED: {conflict['type']}",
                metadata=conflict_log,
                knowledge_type=KnowledgeType.PATTERN,  # Use PATTERN for meta-information
                confidence=KnowledgeConfidence.HIGH,  # High confidence that this needs review
            )

            logger.warning(f"Conflict logged for human review: {conflict['type']}")

        except Exception as e:
            logger.error(f"Error logging conflict for review: {e}")

    @log_function()
    async def add_sender_knowledge(
        self,
        content: str,
        sender_email: str,
        sender_domain: str | None = None,
        organization: str | None = None,
        response_pattern: str | None = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs,
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
            "sender_domain": (
                sender_domain or sender_email.split("@")[1]
                if "@" in sender_email
                else None
            ),
            "organization": organization,
            "response_pattern": response_pattern,
            **kwargs,
        }

        logger.info(f"Adding sender knowledge for: {sender_email}")
        return await self.add(content, metadata, KnowledgeType.SENDER, confidence)

    @log_function()
    async def add_email_type_knowledge(
        self,
        content: str,
        email_type: str,
        classification_criteria: str | None = None,
        typical_patterns: list[str] | None = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs,
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
            **kwargs,
        }

        logger.info(f"Adding email type knowledge: {email_type}")
        return await self.add(content, metadata, KnowledgeType.EMAIL_TYPE, confidence)

    @log_function()
    async def add_domain_knowledge(
        self,
        content: str,
        domain: str,
        expertise_area: str,
        industry_context: str | None = None,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs,
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
            **kwargs,
        }

        logger.info(f"Adding domain knowledge: {domain}/{expertise_area}")
        return await self.add(content, metadata, KnowledgeType.DOMAIN, confidence)

    @log_function()
    async def add_file_type_knowledge(
        self,
        file_extension: str,
        content: str,
        is_allowed: bool = True,
        asset_types: list[str] | None = None,
        document_categories: list[str] | None = None,
        security_level: str = "standard",
        success_count: int = 0,
        failure_count: int = 0,
        confidence: KnowledgeConfidence = KnowledgeConfidence.MEDIUM,
        **kwargs,
    ) -> str:
        """
        Add file type validation knowledge with security and business context.

        Stores learned knowledge about file types, their safety, business relevance,
        and processing success patterns to replace hardcoded validation rules.

        Args:
            file_extension: File extension (e.g., '.pdf', '.xlsx')
            content: Description of file type and its business purpose
            is_allowed: Whether this file type should be processed
            asset_types: Asset types where this file type is commonly used
            document_categories: Document categories this file type represents
            security_level: Security classification (safe, restricted, dangerous)
            success_count: Number of successful processing instances
            failure_count: Number of processing failures
            confidence: Confidence level in the file type knowledge
            **kwargs: Additional file type metadata

        Returns:
            Knowledge ID of the created file type knowledge

        Example:
            >>> file_type_id = await semantic_memory.add_file_type_knowledge(
            ...     file_extension=".pdf",
            ...     content="PDF documents commonly contain loan agreements, financial statements, and asset documentation",
            ...     is_allowed=True,
            ...     asset_types=["private_credit", "commercial_real_estate"],
            ...     document_categories=["loan_documents", "financial_statements"],
            ...     security_level="safe",
            ...     success_count=1250,
            ...     confidence=KnowledgeConfidence.HIGH
            ... )
        """
        if not file_extension.startswith("."):
            file_extension = "." + file_extension

        file_extension = file_extension.lower()

        metadata = {
            "file_extension": file_extension,
            "is_allowed": is_allowed,
            "asset_types": asset_types or [],
            "document_categories": document_categories or [],
            "security_level": security_level,
            "success_count": success_count,
            "failure_count": failure_count,
            "processing_rate": success_count / max(success_count + failure_count, 1),
            "last_updated": datetime.now(UTC).isoformat(),
            **kwargs,
        }

        logger.info(
            f"Adding file type knowledge: {file_extension} (allowed: {is_allowed})"
        )
        return await self.add(content, metadata, KnowledgeType.RULE, confidence)

    @log_function()
    async def get_file_type_validation(self, file_extension: str) -> dict[str, Any]:
        """
        Get file type validation decision from learned knowledge.

        Retrieves file type knowledge to determine if a file extension should
        be allowed, including confidence scoring and business context.

        Args:
            file_extension: File extension to validate (e.g., '.pdf', '.xlsx')

        Returns:
            Dictionary with validation decision and metadata:
            {
                "is_allowed": bool,
                "confidence": float,
                "security_level": str,
                "business_context": dict,
                "learning_source": str
            }

        Example:
            >>> validation = await semantic_memory.get_file_type_validation(".pdf")
            >>> if validation["is_allowed"] and validation["confidence"] > 0.7:
            ...     # Process the file
        """
        if not file_extension.startswith("."):
            file_extension = "." + file_extension

        file_extension = file_extension.lower()

        logger.info(f"Validating file type: {file_extension}")

        try:
            # Search for specific file type knowledge
            file_filter = {
                "key": "metadata.file_extension",
                "match": {"value": file_extension},
            }

            results = await self.search(
                query=f"file type {file_extension} validation security",
                limit=5,
                filter=file_filter,
                knowledge_type=KnowledgeType.RULE,
                min_confidence=KnowledgeConfidence.LOW,
            )

            if results:
                # Use the most confident result (results are now MemoryItems after tuple extraction)
                best_result_item = max(
                    results, key=lambda x: x.metadata.get("success_count", 0)
                )

                return {
                    "is_allowed": best_result_item.metadata.get("is_allowed", False),
                    "confidence": best_result_item.metadata.get("processing_rate", 0.0),
                    "security_level": best_result_item.metadata.get(
                        "security_level", "unknown"
                    ),
                    "business_context": {
                        "asset_types": best_result_item.metadata.get("asset_types", []),
                        "document_categories": best_result_item.metadata.get(
                            "document_categories", []
                        ),
                        "success_count": best_result_item.metadata.get(
                            "success_count", 0
                        ),
                        "failure_count": best_result_item.metadata.get(
                            "failure_count", 0
                        ),
                    },
                    "learning_source": "semantic_memory",
                    "knowledge_id": best_result_item.id,
                }
            else:
                # No knowledge found - return conservative default
                logger.warning(f"No knowledge found for file type: {file_extension}")
                return {
                    "is_allowed": False,
                    "confidence": 0.0,
                    "security_level": "unknown",
                    "business_context": {},
                    "learning_source": "default_conservative",
                    "knowledge_id": None,
                }

        except Exception as e:
            logger.error(f"Error validating file type {file_extension}: {e}")
            return {
                "is_allowed": False,
                "confidence": 0.0,
                "security_level": "error",
                "business_context": {},
                "learning_source": "error_fallback",
                "knowledge_id": None,
            }

    @log_function()
    async def learn_file_type_success(
        self,
        file_extension: str,
        asset_type: str | None = None,
        document_category: str | None = None,
        success: bool = True,
    ) -> str:
        """
        Learn from file processing success/failure to improve validation.

        Updates file type knowledge based on actual processing outcomes
        to continuously improve validation accuracy and business relevance.

        Args:
            file_extension: File extension that was processed
            asset_type: Asset type context of the processing
            document_category: Document category that was classified
            success: Whether the processing was successful

        Returns:
            Knowledge ID of the updated file type knowledge
        """
        if not file_extension.startswith("."):
            file_extension = "." + file_extension

        file_extension = file_extension.lower()

        logger.info(
            f"Learning from file processing: {file_extension} (success: {success})"
        )

        # Get existing knowledge
        validation = await self.get_file_type_validation(file_extension)

        if validation["knowledge_id"]:
            # Update existing knowledge - this would require implementing update_knowledge method
            # For now, we'll create new knowledge entries and let the system learn patterns
            pass

        # Create/update file type knowledge based on this processing outcome
        business_context = validation.get("business_context", {})
        asset_types = business_context.get("asset_types", [])
        document_categories = business_context.get("document_categories", [])

        if asset_type and asset_type not in asset_types:
            asset_types.append(asset_type)

        if document_category and document_category not in document_categories:
            document_categories.append(document_category)

        success_count = business_context.get("success_count", 0)
        failure_count = business_context.get("failure_count", 0)

        if success:
            success_count += 1
        else:
            failure_count += 1

        # Determine confidence based on success rate
        processing_rate = success_count / max(success_count + failure_count, 1)
        if processing_rate > 0.8:
            confidence = KnowledgeConfidence.HIGH
        elif processing_rate > 0.6:
            confidence = KnowledgeConfidence.MEDIUM
        else:
            confidence = KnowledgeConfidence.LOW

        content = f"File type {file_extension} processing: {success_count} successes, {failure_count} failures"

        return await self.add_file_type_knowledge(
            file_extension=file_extension,
            content=content,
            is_allowed=(processing_rate > 0.5),  # Allow if more successes than failures
            asset_types=asset_types,
            document_categories=document_categories,
            security_level="learned",
            success_count=success_count,
            failure_count=failure_count,
            confidence=confidence,
            learning_source="processing_outcome",
        )

    @log_function()
    async def add_asset_knowledge(
        self,
        asset_id: str,
        deal_name: str,
        asset_name: str,
        asset_type: str,
        identifiers: list[str],
        business_context: dict[str, Any],
        confidence: KnowledgeConfidence = KnowledgeConfidence.HIGH,
        **kwargs,
    ) -> str:
        """
        Add asset knowledge to semantic memory.

        Stores structured information about assets including identifiers,
        business context, and metadata for asset matching and management.

        Args:
            asset_id: Unique asset identifier
            deal_name: Human-readable deal name
            asset_name: Full formal asset name
            asset_type: Type of asset (e.g., 'private_credit')
            identifiers: List of identifiers used for matching
            business_context: Business context and metadata
            confidence: Knowledge confidence level
            **kwargs: Additional metadata

        Returns:
            Knowledge item ID for tracking

        Example:
            >>> asset_id = await semantic_memory.add_asset_knowledge(
            ...     asset_id="12345-abcd",
            ...     deal_name="Gray IV",
            ...     asset_name="Gray IV Credit Agreement",
            ...     asset_type="private_credit",
            ...     identifiers=["Gray", "Gray 4", "Gray revolver"],
            ...     business_context={"lender": "Wells Fargo", "description": "..."}
            ... )
        """
        logger.info(f"Adding asset knowledge: {deal_name} ({asset_type})")

        # Create comprehensive content for semantic search
        content_parts = [
            f"Asset: {deal_name}",
            f"Type: {asset_type}",
            f"Identifiers: {', '.join(identifiers)}",
        ]

        if business_context.get("description"):
            content_parts.append(f"Description: {business_context['description']}")

        if business_context.get("lender"):
            content_parts.append(f"Lender: {business_context['lender']}")

        if business_context.get("keywords"):
            content_parts.append(f"Keywords: {', '.join(business_context['keywords'])}")

        content = " | ".join(content_parts)

        # Build metadata for asset knowledge
        metadata = {
            "knowledge_type": KnowledgeType.RULE.value,  # Asset data is factual rule knowledge
            "knowledge_category": "asset_data",
            "confidence": confidence.value,
            "asset_id": asset_id,
            "deal_name": deal_name,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "identifiers": identifiers,
            "business_context": business_context,
            "knowledge_source": kwargs.get("knowledge_source", "manual_entry"),
            "created_date": datetime.now(UTC).isoformat(),
        }

        # Add any additional metadata
        for key, value in kwargs.items():
            if key not in metadata:
                metadata[key] = value

        knowledge_id = await self.add(
            content=content,
            metadata=metadata,
            knowledge_type=KnowledgeType.RULE,
            confidence=confidence,
        )

        logger.info(f"Successfully added asset knowledge: {knowledge_id}")
        return knowledge_id

    @log_function()
    async def search_asset_knowledge(
        self, query: str = "", limit: int = 100
    ) -> list[MemoryItem]:
        """
        Search for asset knowledge in semantic memory.

        Retrieves asset data for matching algorithms to use.

        Args:
            query: Optional search query (defaults to all assets)
            limit: Maximum number of results

        Returns:
            List of asset knowledge items
        """
        logger.info(f"Searching asset knowledge: query='{query}', limit={limit}")

        asset_filter = {
            "key": "metadata.knowledge_category",
            "match": {"value": "asset_data"},
        }

        search_query = query if query else "asset"

        return await self.search(
            query=search_query,
            limit=limit,
            filter=asset_filter,
            knowledge_type=KnowledgeType.RULE,
        )

    @log_function()
    async def add_classification_feedback(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        correct_category: str,
        asset_type: str,
        confidence: float = 0.95,
        source: str = "human_correction",
        original_prediction: str | None = None,
        **kwargs,
    ) -> str:
        """
        Add human feedback about document classification to semantic memory.

        Stores experiential knowledge from human corrections to improve future
        classification decisions. This feedback becomes part of the semantic
        knowledge base that influences classification decisions.

        Args:
            filename: Document filename that was classified
            email_subject: Email subject line context
            email_body: Email body content context
            correct_category: The correct document category per human feedback
            asset_type: Type of asset for context filtering
            confidence: Confidence in the human correction (default: 0.95)
            source: Source of the feedback (default: "human_correction")
            original_prediction: What the system originally predicted
            **kwargs: Additional metadata

        Returns:
            Knowledge item ID for tracking the feedback

        Raises:
            ValueError: If required parameters are missing or invalid

        Example:
            >>> feedback_id = await semantic_memory.add_classification_feedback(
            ...     filename="loan_agreement.pdf",
            ...     email_subject="Q4 Documentation",
            ...     email_body="Attached is the loan agreement...",
            ...     correct_category="loan_documents",
            ...     asset_type="private_credit",
            ...     original_prediction="financial_statements"
            ... )
        """
        # # Local application imports

        # Validate required parameters
        if not filename or not correct_category or not asset_type:
            raise ValueError("filename, correct_category, and asset_type are required")

        logger.info(
            f"Adding classification feedback: {filename} -> {correct_category} (asset_type: {asset_type})"
        )

        # Create comprehensive content for semantic search
        content_parts = [
            f"Document: {filename}",
            f"Correct Category: {correct_category}",
            f"Asset Type: {asset_type}",
        ]

        if email_subject:
            content_parts.append(f"Email Subject: {email_subject}")

        if original_prediction and original_prediction != correct_category:
            content_parts.append(f"System Predicted: {original_prediction} (incorrect)")

        # Add key context from email body (first 200 chars)
        if email_body:
            email_context = email_body.strip()[:200]
            if len(email_body) > 200:
                email_context += "..."
            content_parts.append(f"Email Context: {email_context}")

        content = " | ".join(content_parts)

        # Build metadata for classification feedback
        metadata = {
            "knowledge_type": KnowledgeType.PATTERN.value,
            "knowledge_category": "classification_feedback",
            "confidence": str(confidence),
            "filename": filename,
            "email_subject": email_subject,
            "email_body_hash": await self._generate_content_hash(
                email_body
            ),  # Store hash for privacy
            "correct_category": correct_category,
            "asset_type": asset_type,
            "source": source,
            "original_prediction": original_prediction,
            "feedback_date": datetime.now(UTC).isoformat(),
            "corrected_by": kwargs.get("corrected_by", "human_reviewer"),
            "review_context": kwargs.get("review_context", ""),
        }

        # Add any additional metadata
        for key, value in kwargs.items():
            if key not in metadata:
                metadata[key] = value

        # Map confidence to knowledge confidence enum
        if confidence >= 0.95:
            knowledge_confidence = KnowledgeConfidence.HIGH
        elif confidence >= 0.8:
            knowledge_confidence = KnowledgeConfidence.MEDIUM
        elif confidence >= 0.6:
            knowledge_confidence = KnowledgeConfidence.LOW
        else:
            knowledge_confidence = KnowledgeConfidence.EXPERIMENTAL

        feedback_id = await self.add(
            content=content,
            metadata=metadata,
            knowledge_type=KnowledgeType.PATTERN,
            confidence=knowledge_confidence,
        )

        logger.info(f"Successfully added classification feedback: {feedback_id}")
        return feedback_id

    @log_function()
    async def get_classification_hints(
        self, asset_type: str, document_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Get classification hints from human feedback for similar documents.

        Retrieves relevant human feedback that can inform classification decisions
        for documents with similar context, providing experiential knowledge to
        improve classification accuracy.

        Args:
            asset_type: Type of asset for context filtering
            document_context: Context about the document being classified
                            (filename, email_subject, email_body, etc.)

        Returns:
            List of classification hints with confidence scores:
            [
                {
                    "suggested_category": str,
                    "confidence": float,
                    "reason": str,
                    "similar_case": str,
                    "feedback_id": str
                }
            ]

        Example:
            >>> hints = await semantic_memory.get_classification_hints(
            ...     asset_type="private_credit",
            ...     document_context={
            ...         "filename": "credit_agreement.pdf",
            ...         "email_subject": "Loan Documentation"
            ...     }
            ... )
        """
        logger.info(
            f"Getting classification hints for asset_type: {asset_type}, context: {document_context.keys()}"
        )

        hints = []

        try:
            # Build search query from document context
            search_terms = []

            filename = document_context.get("filename", "")
            if filename:
                # Extract meaningful terms from filename
                filename_terms = filename.lower().replace("_", " ").replace("-", " ")
                search_terms.append(filename_terms)

            email_subject = document_context.get("email_subject", "")
            if email_subject:
                search_terms.append(email_subject.lower())

            email_body = document_context.get("email_body", "")
            if email_body:
                # Use first 100 characters of email body
                search_terms.append(email_body[:100].lower())

            # Create comprehensive search query
            search_query = " ".join(search_terms) if search_terms else "classification"

            # Search for similar classification feedback
            feedback_filter = {
                "must": [
                    {
                        "key": "metadata.knowledge_category",
                        "match": {"value": "classification_feedback"},
                    },
                    {"key": "metadata.asset_type", "match": {"value": asset_type}},
                ]
            }

            feedback_results = await self.search(
                query=search_query,
                limit=10,
                filter=feedback_filter,
                knowledge_type=KnowledgeType.PATTERN,
                min_confidence=KnowledgeConfidence.LOW,
            )

            # Process feedback results into hints
            category_scores = {}

            for feedback_item in feedback_results:
                try:
                    metadata = feedback_item.metadata
                    category = metadata.get("correct_category")
                    confidence = float(metadata.get("confidence", 0.5))
                    filename_match = metadata.get("filename", "")
                    original_pred = metadata.get("original_prediction", "")

                    if not category:
                        continue

                    # Calculate similarity boost based on filename matching
                    similarity_boost = 0.0
                    if filename and filename_match:
                        # Simple similarity check - can be enhanced
                        filename_words = set(filename.lower().split())
                        match_words = set(filename_match.lower().split())
                        if filename_words & match_words:  # Any common words
                            similarity_boost = 0.1

                    adjusted_confidence = min(confidence + similarity_boost, 1.0)

                    # Aggregate scores by category
                    if category in category_scores:
                        category_scores[category]["confidence"] = max(
                            category_scores[category]["confidence"], adjusted_confidence
                        )
                        category_scores[category]["count"] += 1
                        category_scores[category]["examples"].append(filename_match)
                    else:
                        category_scores[category] = {
                            "confidence": adjusted_confidence,
                            "count": 1,
                            "examples": [filename_match],
                            "original_prediction": original_pred,
                            "feedback_id": feedback_item.id,
                        }

                except Exception as e:
                    logger.debug(f"Error processing feedback item: {e}")
                    continue

            # Convert to hints format and sort by confidence
            for category, score_data in category_scores.items():
                # Boost confidence based on multiple examples
                count_boost = min(score_data["count"] * 0.05, 0.2)
                final_confidence = min(score_data["confidence"] + count_boost, 1.0)

                reason_parts = [f"Based on {score_data['count']} similar case(s)"]
                if score_data["examples"]:
                    example = score_data["examples"][0]
                    reason_parts.append(f"similar to '{example}'")

                if score_data["original_prediction"]:
                    reason_parts.append(
                        f"often confused with '{score_data['original_prediction']}'"
                    )

                hints.append(
                    {
                        "suggested_category": category,
                        "confidence": final_confidence,
                        "reason": "; ".join(reason_parts),
                        "similar_case": (
                            score_data["examples"][0] if score_data["examples"] else ""
                        ),
                        "feedback_id": score_data["feedback_id"],
                        "example_count": score_data["count"],
                    }
                )

            # Sort by confidence (highest first)
            hints.sort(key=lambda x: x["confidence"], reverse=True)

            logger.info(
                f"Generated {len(hints)} classification hints for asset_type: {asset_type}"
            )

            return hints[:5]  # Return top 5 hints

        except Exception as e:
            logger.error(f"Failed to get classification hints: {e}")
            return []

    @log_function()
    async def store_human_correction(
        self,
        original_prediction: str,
        human_correction: str,
        metadata: dict[str, Any],
    ) -> str:
        """
        Store a human correction with complete context metadata.

        Stores human corrections as experiential knowledge that can influence
        future decisions. This is a general-purpose method for any type of
        human correction beyond just document classification.

        Args:
            original_prediction: What the system originally predicted
            human_correction: What the human corrected it to
            metadata: Complete context metadata about the correction

        Returns:
            Knowledge item ID for tracking the correction

        Raises:
            ValueError: If required parameters are missing

        Example:
            >>> correction_id = await semantic_memory.store_human_correction(
            ...     original_prediction="financial_statements",
            ...     human_correction="loan_documents",
            ...     metadata={
            ...         "filename": "agreement.pdf",
            ...         "asset_type": "private_credit",
            ...         "corrected_by": "analyst_jane",
            ...         "correction_reason": "Document contains loan terms, not financials"
            ...     }
            ... )
        """
        if not original_prediction or not human_correction:
            raise ValueError("original_prediction and human_correction are required")

        if not metadata:
            metadata = {}

        logger.info(
            f"Storing human correction: {original_prediction} -> {human_correction}"
        )

        # Create content describing the correction
        content = f"Human Correction: {original_prediction} → {human_correction}"

        # Add context if available
        if metadata.get("filename"):
            content += f" | Document: {metadata['filename']}"

        if metadata.get("asset_type"):
            content += f" | Asset Type: {metadata['asset_type']}"

        if metadata.get("correction_reason"):
            content += f" | Reason: {metadata['correction_reason']}"

        # Enhance metadata for correction tracking
        correction_metadata = {
            "knowledge_type": KnowledgeType.INSIGHT.value,
            "knowledge_category": "human_correction",
            "original_prediction": original_prediction,
            "human_correction": human_correction,
            "correction_date": datetime.now(UTC).isoformat(),
            "confidence": "high",  # Human corrections are high confidence
            "source": "human_correction",
        }

        # Merge with provided metadata
        correction_metadata.update(metadata)

        correction_id = await self.add(
            content=content,
            metadata=correction_metadata,
            knowledge_type=KnowledgeType.INSIGHT,
            confidence=KnowledgeConfidence.HIGH,
        )

        logger.info(f"Successfully stored human correction: {correction_id}")
        return correction_id

    @log_function()
    async def get_asset_feedback(
        self, asset_id: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get human feedback related to a specific asset.

        Retrieves all human feedback, corrections, and experiential knowledge
        related to a specific asset to inform decision-making.

        Args:
            asset_id: Unique identifier of the asset
            context: Optional context to filter feedback (e.g., document_type)

        Returns:
            List of feedback items with metadata:
            [
                {
                    "feedback_type": str,
                    "content": str,
                    "confidence": float,
                    "date": str,
                    "source": str,
                    "metadata": dict
                }
            ]

        Example:
            >>> feedback = await semantic_memory.get_asset_feedback(
            ...     asset_id="12345-abcd",
            ...     context={"document_type": "loan_documents"}
            ... )
        """
        if not asset_id:
            raise ValueError("asset_id is required")

        logger.info(f"Getting asset feedback for: {asset_id}")

        feedback_items = []

        try:
            # Search for feedback related to this asset
            asset_filter = {
                "must": [
                    {"key": "metadata.asset_id", "match": {"value": asset_id}},
                    {
                        "key": "metadata.knowledge_category",
                        "match": {
                            "any": [
                                "classification_feedback",
                                "human_correction",
                                "asset_feedback",
                            ]
                        },
                    },
                ]
            }

            # Add context filters if provided
            if context:
                for key, value in context.items():
                    asset_filter["must"].append(
                        {"key": f"metadata.{key}", "match": {"value": value}}
                    )

            feedback_results = await self.search(
                query=f"asset {asset_id}",
                limit=50,
                filter=asset_filter,
                min_confidence=KnowledgeConfidence.LOW,
            )

            # Process results into feedback format
            for item in feedback_results:
                try:
                    metadata = item.metadata
                    feedback_type = metadata.get("knowledge_category", "unknown")

                    feedback_item = {
                        "feedback_id": item.id,
                        "feedback_type": feedback_type,
                        "content": item.content,
                        "confidence": metadata.get("confidence", "medium"),
                        "date": metadata.get(
                            "feedback_date",
                            metadata.get("correction_date", metadata.get("created_at")),
                        ),
                        "source": metadata.get("source", "unknown"),
                        "metadata": metadata,
                    }

                    # Add type-specific information
                    if feedback_type == "classification_feedback":
                        feedback_item.update(
                            {
                                "document_category": metadata.get("correct_category"),
                                "filename": metadata.get("filename"),
                                "original_prediction": metadata.get(
                                    "original_prediction"
                                ),
                            }
                        )
                    elif feedback_type == "human_correction":
                        feedback_item.update(
                            {
                                "correction": f"{metadata.get('original_prediction')} → {metadata.get('human_correction')}",
                                "reason": metadata.get("correction_reason"),
                            }
                        )

                    feedback_items.append(feedback_item)

                except Exception as e:
                    logger.debug(f"Error processing feedback item: {e}")
                    continue

            # Sort by date (most recent first)
            feedback_items.sort(key=lambda x: x.get("date", ""), reverse=True)

            logger.info(
                f"Retrieved {len(feedback_items)} feedback items for asset: {asset_id}"
            )

            return feedback_items

        except Exception as e:
            logger.error(f"Failed to get asset feedback: {e}")
            return []

    @log_function()
    async def load_knowledge_base(
        self, knowledge_base_path: str = "knowledge"
    ) -> dict[str, int]:
        """
        Load initial knowledge from JSON knowledge base files.

        Initializes semantic memory with bootstrap knowledge from the knowledge
        directory, replacing hardcoded rules with learned patterns.

        Args:
            knowledge_base_path: Path to the knowledge base directory

        Returns:
            Dictionary with loading results:
            {
                "file_types_loaded": int,
                "total_knowledge_items": int,
                "errors": list[str]
            }

        Example:
            >>> results = await semantic_memory.load_knowledge_base("knowledge")
            >>> print(f"Loaded {results['file_types_loaded']} file type validations")
        """
        # # Standard library imports
        import json
        from pathlib import Path

        logger.info("Loading knowledge base from: %s", knowledge_base_path)

        results = {"file_types_loaded": 0, "total_knowledge_items": 0, "errors": []}

        knowledge_path = Path(knowledge_base_path)
        if not knowledge_path.exists():
            error_msg = f"Knowledge base path not found: {knowledge_base_path}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            return results

        # Check if knowledge base has already been loaded
        try:
            bootstrap_filter = {
                "key": "metadata.knowledge_source",
                "match": {"value": "knowledge_base_bootstrap"},
            }

            existing_bootstrap = await self.search(
                query="knowledge base bootstrap", limit=5, filter=bootstrap_filter
            )

            if existing_bootstrap:
                logger.info(
                    f"Knowledge base already loaded ({len(existing_bootstrap)} bootstrap items found), skipping"
                )
                return {
                    "file_types_loaded": 0,
                    "total_knowledge_items": 0,
                    "errors": [],
                    "status": "already_loaded",
                }
        except Exception as e:
            logger.warning(f"Could not check for existing bootstrap items: {e}")
            # Continue with loading to be safe

        # Load file type validation knowledge
        file_validation_path = knowledge_path / "file_type_validation.json"
        if file_validation_path.exists():
            try:
                with open(file_validation_path, encoding="utf-8") as f:
                    file_validation_data = json.load(f)

                validation_config = file_validation_data.get("file_type_validation", {})

                # Load safe file types
                safe_types = validation_config.get("safe_file_types", {})
                for ext, config in safe_types.items():
                    try:
                        # Map confidence strings to enums
                        confidence_mapping = {
                            "high": KnowledgeConfidence.HIGH,
                            "medium": KnowledgeConfidence.MEDIUM,
                            "low": KnowledgeConfidence.LOW,
                        }
                        confidence = confidence_mapping.get(
                            config.get("confidence", "medium"),
                            KnowledgeConfidence.MEDIUM,
                        )

                        knowledge_id = await self.add_file_type_knowledge(
                            file_extension=ext,
                            content=config.get(
                                "content", f"File type {ext} validation rule"
                            ),
                            is_allowed=config.get("is_allowed", True),
                            asset_types=config.get("asset_types", []),
                            document_categories=config.get("document_categories", []),
                            security_level=config.get("security_level", "safe"),
                            success_count=config.get("success_count", 0),
                            failure_count=config.get("failure_count", 0),
                            confidence=confidence,
                            business_context=config.get("business_context", ""),
                            knowledge_source="knowledge_base_bootstrap",
                        )

                        results["file_types_loaded"] += 1
                        results["total_knowledge_items"] += 1

                        logger.debug(
                            "Loaded safe file type: %s -> %s", ext, knowledge_id[:8]
                        )

                    except Exception as e:
                        error_msg = f"Failed to load safe file type {ext}: {e}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)

                # Load restricted file types
                restricted_types = validation_config.get("restricted_file_types", {})
                for ext, config in restricted_types.items():
                    try:
                        confidence_mapping = {
                            "high": KnowledgeConfidence.HIGH,
                            "medium": KnowledgeConfidence.MEDIUM,
                            "low": KnowledgeConfidence.LOW,
                        }
                        confidence = confidence_mapping.get(
                            config.get("confidence", "medium"),
                            KnowledgeConfidence.MEDIUM,
                        )

                        knowledge_id = await self.add_file_type_knowledge(
                            file_extension=ext,
                            content=config.get(
                                "content", f"File type {ext} restriction rule"
                            ),
                            is_allowed=config.get("is_allowed", False),
                            asset_types=config.get("asset_types", []),
                            document_categories=config.get("document_categories", []),
                            security_level=config.get("security_level", "restricted"),
                            success_count=config.get("success_count", 0),
                            failure_count=config.get("failure_count", 0),
                            confidence=confidence,
                            business_context=config.get("business_context", ""),
                            knowledge_source="knowledge_base_bootstrap",
                        )

                        results["file_types_loaded"] += 1
                        results["total_knowledge_items"] += 1

                        logger.debug(
                            "Loaded restricted file type: %s -> %s",
                            ext,
                            knowledge_id[:8],
                        )

                    except Exception as e:
                        error_msg = f"Failed to load restricted file type {ext}: {e}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)

                # Load dangerous file types
                dangerous_types = validation_config.get("dangerous_file_types", {})
                for ext, config in dangerous_types.items():
                    try:
                        confidence_mapping = {
                            "high": KnowledgeConfidence.HIGH,
                            "medium": KnowledgeConfidence.MEDIUM,
                            "low": KnowledgeConfidence.LOW,
                        }
                        confidence = confidence_mapping.get(
                            config.get("confidence", "high"), KnowledgeConfidence.HIGH
                        )

                        knowledge_id = await self.add_file_type_knowledge(
                            file_extension=ext,
                            content=config.get(
                                "content", f"File type {ext} security prohibition"
                            ),
                            is_allowed=config.get("is_allowed", False),
                            asset_types=config.get("asset_types", []),
                            document_categories=config.get("document_categories", []),
                            security_level=config.get("security_level", "dangerous"),
                            success_count=config.get("success_count", 0),
                            failure_count=config.get("failure_count", 0),
                            confidence=confidence,
                            business_context=config.get("business_context", ""),
                            knowledge_source="knowledge_base_bootstrap",
                        )

                        results["file_types_loaded"] += 1
                        results["total_knowledge_items"] += 1

                        logger.debug(
                            "Loaded dangerous file type: %s -> %s",
                            ext,
                            knowledge_id[:8],
                        )

                    except Exception as e:
                        error_msg = f"Failed to load dangerous file type {ext}: {e}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)

                logger.info(
                    "File type validation knowledge loading complete: %d types loaded",
                    results["file_types_loaded"],
                )

            except Exception as e:
                error_msg = f"Failed to load file type validation knowledge: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        else:
            logger.warning(
                "File type validation knowledge file not found: %s",
                file_validation_path,
            )

        # Load asset data for semantic memory
        asset_data_path = knowledge_path / "asset_data.json"
        if asset_data_path.exists():
            try:
                logger.info("Loading asset data from: %s", asset_data_path)
                with open(asset_data_path) as f:
                    asset_data = json.load(f)

                assets = asset_data.get("assets", [])
                for asset in assets:
                    try:
                        asset_id = await self.add_asset_knowledge(
                            asset_id=asset.get("asset_id"),
                            deal_name=asset.get("deal_name"),
                            asset_name=asset.get("asset_name"),
                            asset_type=asset.get("asset_type"),
                            identifiers=asset.get("identifiers", []),
                            business_context=asset.get("business_context", {}),
                            confidence=KnowledgeConfidence.HIGH,
                            knowledge_source="knowledge_base_bootstrap",
                        )

                        results["asset_data_loaded"] = (
                            results.get("asset_data_loaded", 0) + 1
                        )
                        results["total_knowledge_items"] += 1

                        logger.debug(
                            "Loaded asset: %s -> %s",
                            asset.get("deal_name"),
                            asset_id[:8],
                        )

                    except Exception as e:
                        error_msg = f"Failed to load asset {asset.get('deal_name', 'unknown')}: {e}"
                        logger.warning(error_msg)
                        results["errors"].append(error_msg)

                logger.info(
                    "Asset data loading complete: %d assets loaded",
                    results.get("asset_data_loaded", 0),
                )

            except Exception as e:
                error_msg = f"Failed to load asset data: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        else:
            logger.warning("Asset data file not found: %s", asset_data_path)

        # Future: Load other knowledge base files here
        # - classification_patterns.json for document classification
        # - business_rules.json for business logic

        logger.info(
            "Knowledge base loading complete: %d total items loaded, %d errors",
            results["total_knowledge_items"],
            len(results["errors"]),
        )

        return results

    @log_function()
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: dict[str, Any] | None = None,
        knowledge_type: KnowledgeType | None = None,
        min_confidence: KnowledgeConfidence | None = None,
    ) -> list[MemoryItem]:
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
                "must": [{"key": "metadata.type", "match": {"value": "knowledge"}}]
            }

            # Knowledge type filter
            if knowledge_type:
                filter_conditions["must"].append(
                    {
                        "key": "metadata.knowledge_type",
                        "match": {"value": knowledge_type.value},
                    }
                )

            # Minimum confidence filter
            if min_confidence:
                # Define confidence levels in order from lowest to highest
                confidence_hierarchy = [
                    KnowledgeConfidence.EXPERIMENTAL,
                    KnowledgeConfidence.LOW,
                    KnowledgeConfidence.MEDIUM,
                    KnowledgeConfidence.HIGH,
                ]
                confidence_values = [conf.value for conf in confidence_hierarchy]
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
            search_results = await super().search(query, limit, filter_conditions)

            # Extract MemoryItems from tuples (BaseMemory.search returns tuples of (MemoryItem, score))
            results = [item for item, score in search_results]

            logger.info(f"Found {len(results)} semantic knowledge items matching query")
            logger.debug(
                f"Knowledge search results preview: {[r.id for r in results[:3]]}"
            )

            return results

        except Exception as e:
            logger.error(f"Error searching semantic knowledge: {e}")
            return []

    @log_function()
    async def search_sender_knowledge(
        self, sender_email: str, limit: int = 5
    ) -> list[MemoryItem]:
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
            "match": {"value": sender_email},
        }

        return await self.search(
            query=sender_email,
            limit=limit,
            filter=sender_filter,
            knowledge_type=KnowledgeType.SENDER,
        )

    @log_function()
    async def search_by_domain(self, domain: str, limit: int = 10) -> list[MemoryItem]:
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
                        {"key": "metadata.domain", "match": {"value": domain}},
                    ]
                }
            ]
        }

        return await self.search(query=domain, limit=limit, filter=domain_filter)

    @log_function()
    async def get_knowledge_statistics(self) -> dict[str, Any]:
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
            search_results = await super().search(query="*", limit=1000)

            # Extract MemoryItems from tuples (BaseMemory.search returns tuples of (MemoryItem, score))
            all_knowledge = [item for item, score in search_results]

            if not all_knowledge:
                return {
                    "total_count": 0,
                    "knowledge_types": {},
                    "confidence_distribution": {},
                    "average_content_length": 0,
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
                "top_organizations": {},
            }

            # Analyze knowledge items
            total_length = 0

            for knowledge in all_knowledge:
                metadata = knowledge.metadata

                # Content length analysis
                total_length += len(knowledge.content)

                # Knowledge type distribution
                knowledge_type = metadata.get("knowledge_type", "unknown")
                stats["knowledge_types"][knowledge_type] = (
                    stats["knowledge_types"].get(knowledge_type, 0) + 1
                )

                # Confidence distribution
                confidence = metadata.get("confidence", "unknown")
                stats["confidence_distribution"][confidence] = (
                    stats["confidence_distribution"].get(confidence, 0) + 1
                )

                # Sender and domain analysis
                if knowledge_type == "sender":
                    stats["sender_knowledge_count"] += 1

                    sender_domain = metadata.get("sender_domain")
                    if sender_domain:
                        stats["top_domains"][sender_domain] = (
                            stats["top_domains"].get(sender_domain, 0) + 1
                        )

                    organization = metadata.get("organization")
                    if organization:
                        stats["top_organizations"][organization] = (
                            stats["top_organizations"].get(organization, 0) + 1
                        )

                elif knowledge_type == "domain":
                    stats["domain_knowledge_count"] += 1

            # Calculate derived statistics
            stats["average_content_length"] = (
                total_length / len(all_knowledge) if all_knowledge else 0
            )

            # Find most common items
            if stats["knowledge_types"]:
                stats["most_common_type"] = max(
                    stats["knowledge_types"], key=stats["knowledge_types"].get
                )

            if stats["top_domains"]:
                stats["most_documented_domain"] = max(
                    stats["top_domains"], key=stats["top_domains"].get
                )

            logger.info(
                f"Generated statistics for {stats['total_count']} knowledge items"
            )
            return stats

        except Exception as e:
            logger.error(f"Error generating knowledge statistics: {e}")
            return {"total_count": 0, "error": str(e)}


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

        _sender_id = await semantic_memory.add_sender_knowledge(
            content="Responds within 2 hours during business hours, prefers detailed technical analysis in investment proposals",
            sender_email="investment@blackstone.com",
            sender_domain="blackstone.com",
            organization="Blackstone Group",
            response_pattern="fast_business_hours",
            decision_authority="investment_committee",
            preferred_communication="technical_detailed",
        )

        # Add email type knowledge
        logger.info("Adding email type knowledge...")

        _email_type_id = await semantic_memory.add_email_type_knowledge(
            content="Investment inquiries typically include fund size, target returns, and investment timeline",
            email_type="investment_inquiry",
            classification_criteria="mentions fund, investment, capital, returns",
            typical_patterns=[
                "fund size",
                "target return",
                "investment timeline",
                "due diligence",
            ],
            confidence=KnowledgeConfidence.HIGH,
        )

        # Add domain knowledge
        logger.info("Adding domain expertise...")

        _domain_id = await semantic_memory.add_domain_knowledge(
            content="Real estate private equity typically requires 6-12 month due diligence periods for large transactions ($100M+)",
            domain="real_estate",
            expertise_area="private_equity_due_diligence",
            industry_context="commercial_real_estate",
            confidence=KnowledgeConfidence.HIGH,
        )

        logger.info("✓ Added sample semantic knowledge")

        # Test knowledge search
        logger.info("Testing knowledge search capabilities...")

        search_results = await semantic_memory.search(
            query="investment response time",
            knowledge_type=KnowledgeType.SENDER,
            limit=5,
        )

        logger.info(f"Found {len(search_results)} results for investment response time")
        for result in search_results:
            knowledge_type = result.metadata.get("knowledge_type", "unknown")
            confidence = result.metadata.get("confidence", "unknown")
            logger.info(
                f"  - {knowledge_type} ({confidence}): {result.content[:80]}..."
            )

        # Test sender-specific search
        logger.info("Testing sender-specific knowledge search...")

        sender_results = await semantic_memory.search_sender_knowledge(
            sender_email="investment@blackstone.com"
        )

        logger.info(
            f"Found {len(sender_results)} knowledge items about investment@blackstone.com"
        )

        # Test domain search
        logger.info("Testing domain knowledge search...")

        domain_results = await semantic_memory.search_by_domain(
            domain="blackstone.com", limit=10
        )

        logger.info(
            f"Found {len(domain_results)} knowledge items related to blackstone.com"
        )

        # Generate knowledge statistics
        logger.info("Generating knowledge statistics...")

        stats = await semantic_memory.get_knowledge_statistics()
        logger.info("Knowledge statistics:")
        logger.info(f"  - Total knowledge items: {stats['total_count']}")
        logger.info(f"  - Knowledge types: {stats['knowledge_types']}")
        logger.info(f"  - Confidence distribution: {stats['confidence_distribution']}")
        logger.info(f"  - Sender knowledge: {stats['sender_knowledge_count']}")
        logger.info(f"  - Domain knowledge: {stats['domain_knowledge_count']}")

        if stats.get("most_common_type"):
            logger.info(f"  - Most common type: {stats['most_common_type']}")

        logger.info("SemanticMemory demonstration completed successfully")

    except Exception as e:
        logger.error(f"SemanticMemory demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # # Standard library imports
    import asyncio

    asyncio.run(demo_semantic_memory())

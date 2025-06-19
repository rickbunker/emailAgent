"""
Episodic Memory System for EmailAgent

episodic memory system for private market asset management environments.
Provides conversation history storage, event tracking, and temporal context management
with search and retrieval capabilities for business intelligence.

Features:
    - Conversation history and event tracking
    - Temporal context management with timestamps
    - Time-based search and filtering capabilities
    - Business context categorization and tagging
    - Interaction pattern analysis and insights
    - feedback and learning integration

Business Context:
    Designed for asset management firms requiring complete conversation
    and interaction tracking across client communications, deal discussions,
    investment committee meetings, and operational workflows. Maintains
    temporal context for relationship management and decision support.

Technical Architecture:
    - Qdrant-based vector storage for semantic search
    - Temporal indexing with timestamp-based filtering
    - Conversation categorization with business context
    - Memory item lifecycle management
    - Performance optimization for time-series queries

Memory Types:
    - Conversation: Email conversations and communications
    - Meeting: Investment committee and client meetings
    - Decision: Investment decisions and rationale
    - Feedback: User feedback and system learning
    - Event: Business events and milestone tracking

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
from utils.config import config
from utils.logging_system import get_logger, log_function

from .base import BaseMemory, MemoryItem

# Initialize logger
logger = get_logger(__name__)


class EpisodicMemoryType(Enum):
    """
    episodic memory classification for business context.

    Provides structured categorization of episodic memories for asset
    management environments with appropriate business context and
    workflow integration.

    Values:
        CONVERSATION: Email conversations and communications
        MEETING: Investment committee and client meetings
        DECISION: Investment decisions and rationale tracking
        FEEDBACK: User feedback and system learning events
        EVENT: Business events and milestone tracking
        EXTRACTION: Data extraction and processing events
        ERROR: Error conditions and system issues
        UNKNOWN: Unclassified episodic memories
    """

    CONVERSATION = "conversation"
    MEETING = "meeting"
    DECISION = "decision"
    FEEDBACK = "feedback"
    EVENT = "event"
    EXTRACTION = "extraction"
    ERROR = "error"
    UNKNOWN = "unknown"


class EpisodicMemory(BaseMemory):
    """
    episodic memory system for asset management environments.

    Provides complete conversation history and event tracking with
    temporal context management designed for private market asset management
    firms requiring interaction and decision tracking.

    Features:
        - Conversation history with temporal context
        - Business event tracking and categorization
        - Time-based search and filtering capabilities
        - Interaction pattern analysis and insights
        - feedback integration and learning
        - Decision audit trail and rationale tracking

    Business Context:
        Enables asset management firms to maintain complete records
        of client interactions, investment decisions, committee discussions,
        and operational events with temporal context for compliance,
        relationship management, and business intelligence.

    Technical Implementation:
        - Dedicated Qdrant collection for episodic memories
        - Temporal indexing with timestamp-based queries
        - Semantic search with business context filtering
        - Memory lifecycle management and retention policies
        - Performance optimization for time-series operations
    """

    def __init__(
        self,
        max_items: int | None = None,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize episodic memory system.

        Args:
            max_items: Maximum number of episodic memories to store (uses config default if None)
            qdrant_url: Qdrant database connection URL
            embedding_model: Sentence transformer model for embeddings
        """
        super().__init__(
            max_items=max_items, qdrant_url=qdrant_url, embedding_model=embedding_model
        )
        self.collection_name = "episodic"
        logger.info(f"Initialized EpisodicMemory with max_items={max_items}")

    @log_function()
    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        memory_type: EpisodicMemoryType = EpisodicMemoryType.CONVERSATION,
    ) -> str:
        """
        Add a new episodic memory with complete metadata.

        Creates episodic memory entries with automatic timestamp generation,
        business context categorization, and metadata enrichment for
        asset management environments.

        Args:
            content: The memory content to store (conversation, event, etc.)
            metadata: Additional metadata for business context
            memory_type: Type of episodic memory for categorization

        Returns:
            The ID of the created memory item

        Raises:
            ValueError: If content is empty or invalid

        Example:
            >>> memory_id = await episodic_memory.add(
            ...     content="Discussion about Series A funding round",
            ...     metadata={
            ...         "participants": ["john@fund.com", "ceo@startup.com"],
            ...         "deal_id": "DEAL_2024_001",
            ...         "stage": "due_diligence"
            ...     },
            ...     memory_type=EpisodicMemoryType.MEETING
            ... )
        """
        if not content or not isinstance(content, str):
            raise ValueError("Memory content must be a non-empty string")

        if metadata is None:
            metadata = {}

        # Set default memory type if not specified in metadata
        if "type" not in metadata:
            metadata["type"] = memory_type.value

        # Add complete temporal metadata
        current_timestamp = datetime.now(UTC).timestamp()
        metadata.setdefault("timestamp", current_timestamp)
        metadata.setdefault("iso_timestamp", datetime.now(UTC).isoformat())
        metadata.setdefault("date", datetime.now(UTC).strftime("%Y-%m-%d"))
        metadata.setdefault("hour", datetime.now(UTC).hour)

        # Add system metadata for tracking
        metadata.setdefault("source", "episodic_memory")
        metadata.setdefault("version", "1.0.0")

        logger.info(
            f"Adding episodic memory: type={memory_type.value}, content_length={len(content)}"
        )
        logger.debug(f"Memory metadata keys: {list(metadata.keys())}")

        try:
            result = await super().add(content, metadata)
            logger.info(f"Successfully added episodic memory: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to add episodic memory: {e}")
            raise

    @log_function()
    async def add_conversation(
        self,
        content: str,
        participants: list[str],
        subject: str | None = None,
        email_id: str | None = None,
        **kwargs,
    ) -> str:
        """
        Add conversation-specific episodic memory.

        Specialized method for adding email conversations and communications
        with participant tracking and conversation context for relationship
        management and business intelligence.

        Args:
            content: Conversation content or summary
            participants: List of participant email addresses
            subject: Email subject or conversation topic
            email_id: Associated email message identifier
            **kwargs: Additional conversation metadata

        Returns:
            Memory ID of the created conversation record

        Example:
            >>> conv_id = await episodic_memory.add_conversation(
            ...     content="Discussed Q3 portfolio performance and allocation strategy",
            ...     participants=["portfolio@fund.com", "investor@pension.com"],
            ...     subject="Q3 Portfolio Review",
            ...     category="investor_relations"
            ... )
        """
        metadata = {
            "participants": participants,
            "participant_count": len(participants),
            **kwargs,
        }

        if subject:
            metadata["subject"] = subject
        if email_id:
            metadata["email_id"] = email_id

        logger.info(f"Adding conversation memory with {len(participants)} participants")
        return await self.add(content, metadata, EpisodicMemoryType.CONVERSATION)

    @log_function()
    async def add_decision(
        self,
        content: str,
        decision_type: str,
        decision_maker: str,
        rationale: str | None = None,
        **kwargs,
    ) -> str:
        """
        Add investment decision episodic memory.

        Specialized method for tracking investment decisions, rationale,
        and decision-making context for compliance and audit trail
        requirements in asset management environments.

        Args:
            content: Decision content and outcome
            decision_type: Type of decision (investment, allocation, exit, etc.)
            decision_maker: Individual or committee making the decision
            rationale: Decision rationale and supporting analysis
            **kwargs: Additional decision metadata

        Returns:
            Memory ID of the created decision record

        Example:
            >>> decision_id = await episodic_memory.add_decision(
            ...     content="Approved $50M investment in PropTech Series B",
            ...     decision_type="investment_approval",
            ...     decision_maker="Investment Committee",
            ...     rationale="Strong market position and experienced team",
            ...     deal_value=50000000,
            ...     sector="proptech"
            ... )
        """
        metadata = {
            "decision_type": decision_type,
            "decision_maker": decision_maker,
            **kwargs,
        }

        if rationale:
            metadata["rationale"] = rationale

        logger.info(
            f"Adding decision memory: type={decision_type}, maker={decision_maker}"
        )
        return await self.add(content, metadata, EpisodicMemoryType.DECISION)

    @log_function()
    async def add_feedback(
        self,
        content: str,
        feedback_type: str,
        source: str,
        sentiment: str | None = None,
        **kwargs,
    ) -> str:
        """
        Add user feedback episodic memory.

        Specialized method for capturing user feedback, system learning
        events, and performance insights for continuous improvement
        in asset management workflows.

        Args:
            content: Feedback content and details
            feedback_type: Type of feedback (positive, negative, suggestion, etc.)
            source: Source of feedback (user, system, automated analysis)
            sentiment: Sentiment analysis result (positive, negative, neutral)
            **kwargs: Additional feedback metadata

        Returns:
            Memory ID of the created feedback record
        """
        metadata = {"feedback_type": feedback_type, "source": source, **kwargs}

        if sentiment:
            metadata["sentiment"] = sentiment

        logger.info(f"Adding feedback memory: type={feedback_type}, source={source}")
        return await self.add(content, metadata, EpisodicMemoryType.FEEDBACK)

    @log_function()
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: dict[str, Any] | None = None,
        time_range: dict[str, float] | None = None,
        memory_type: EpisodicMemoryType | None = None,
    ) -> list[MemoryItem]:
        """
        Search episodic memories with complete filtering.

        Performs semantic search across episodic memories with temporal
        filtering, business context categorization, and relevance ranking
        for asset management environments.

        Args:
            query: The search query for semantic matching
            limit: Maximum number of results to return
            filter: Additional metadata filters to apply
            time_range: Time range filter with 'start' and 'end' timestamps
            memory_type: Filter by specific episodic memory type

        Returns:
            List of matching episodic memory items ordered by relevance

        Example:
            >>> # Search for investment decisions in the last quarter
            >>> results = await episodic_memory.search(
            ...     query="investment approval",
            ...     memory_type=EpisodicMemoryType.DECISION,
            ...     time_range={
            ...         "start": (datetime.now() - timedelta(days=90)).timestamp(),
            ...         "end": datetime.now().timestamp()
            ...     }
            ... )
        """
        logger.info(f"Searching episodic memories: query='{query}', limit={limit}")

        try:
            # Build complete filter conditions
            filter_conditions = {"must": []}

            # Memory type filter
            if memory_type:
                filter_conditions["must"].append(
                    {"key": "metadata.type", "match": {"value": memory_type.value}}
                )

            # Time range filter
            if time_range:
                start_time = time_range.get("start", 0)
                end_time = time_range.get("end", datetime.now(UTC).timestamp())

                time_filter = {
                    "key": "metadata.timestamp",
                    "range": {"gte": start_time, "lte": end_time},
                }
                filter_conditions["must"].append(time_filter)
                logger.debug(f"Applied time range filter: {start_time} to {end_time}")

            # Additional custom filters
            if filter:
                if "must" in filter:
                    filter_conditions["must"].extend(filter["must"])
                else:
                    filter_conditions["must"].append(filter)

            # Use combined filter or None if no conditions
            search_filter = filter_conditions if filter_conditions["must"] else None

            # Perform semantic search - returns list[tuple[MemoryItem, float]]
            search_results = await super().search(query, limit, search_filter)

            # Extract MemoryItems from tuples
            results = []
            for memory_item, _similarity_score in search_results:
                results.append(memory_item)

            logger.info(f"Found {len(results)} episodic memories matching query")
            logger.debug(f"Search results preview: {[r.id for r in results[:3]]}")

            return results

        except Exception as e:
            logger.error(f"Error searching episodic memories: {e}")
            return []

    @log_function()
    async def search_by_participants(
        self,
        participant_email: str,
        limit: int = 10,
        time_range: dict[str, float] | None = None,
    ) -> list[MemoryItem]:
        """
        Search episodic memories by participant involvement.

        Finds all episodic memories involving a specific participant
        for relationship tracking and interaction history analysis.

        Args:
            participant_email: Email address of participant to search for
            limit: Maximum number of results to return
            time_range: Optional time range for temporal filtering

        Returns:
            List of episodic memories involving the specified participant

        Example:
            >>> # Find all interactions with a specific investor
            >>> interactions = await episodic_memory.search_by_participants(
            ...     participant_email="investor@pension.com",
            ...     limit=20
            ... )
        """
        logger.info(f"Searching episodic memories by participant: {participant_email}")

        try:
            # Build participant filter
            participant_filter = {
                "key": "metadata.participants",
                "match": {"any": [participant_email]},
            }

            # Combine with time range if provided
            filter_conditions = {"must": [participant_filter]}

            if time_range:
                time_filter = {
                    "key": "metadata.timestamp",
                    "range": {
                        "gte": time_range.get("start", 0),
                        "lte": time_range.get("end", datetime.now(UTC).timestamp()),
                    },
                }
                filter_conditions["must"].append(time_filter)

            # Search with participant filter
            results = await super().search(
                query=participant_email, limit=limit, filter=filter_conditions
            )

            logger.info(f"Found {len(results)} memories involving {participant_email}")
            return results

        except Exception as e:
            logger.error(f"Error searching by participant {participant_email}: {e}")
            return []

    @log_function()
    async def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 10,
        memory_type: EpisodicMemoryType | None = None,
    ) -> list[MemoryItem]:
        """
        Retrieve recent episodic memories within specified time window.

        Gets the most recent episodic memories for operational context
        and current activity tracking in asset management workflows.

        Args:
            hours: Number of hours back to search (default: 24)
            limit: Maximum number of results to return
            memory_type: Optional filter by memory type

        Returns:
            List of recent episodic memories ordered by recency

        Example:
            >>> # Get recent investment decisions
            >>> recent_decisions = await episodic_memory.get_recent_memories(
            ...     hours=168,  # Last week
            ...     memory_type=EpisodicMemoryType.DECISION
            ... )
        """
        logger.info(f"Retrieving recent memories: {hours} hours, type={memory_type}")

        try:
            # Calculate time threshold
            cutoff_time = datetime.now(UTC).timestamp() - (hours * 3600)

            time_range = {"start": cutoff_time, "end": datetime.now(UTC).timestamp()}

            # Search with time range filter
            results = await self.search(
                query="*",  # Match all
                limit=limit,
                time_range=time_range,
                memory_type=memory_type,
            )

            logger.info(f"Found {len(results)} recent memories in last {hours} hours")
            return results

        except Exception as e:
            logger.error(f"Error retrieving recent memories: {e}")
            return []

    @log_function()
    async def get_memory_statistics(self) -> dict[str, Any]:
        """
        Get complete statistics about episodic memory usage.

        Provides business intelligence metrics about memory patterns,
        types, and usage for performance monitoring and optimization.

        Returns:
            Dictionary containing memory usage statistics and insights

        Example:
            >>> stats = await episodic_memory.get_memory_statistics()
            >>> print(f"Total memories: {stats['total_count']}")
            >>> print(f"Most active type: {stats['most_common_type']}")
        """
        logger.info("Generating episodic memory statistics")

        try:
            # Get all memories for analysis
            all_memories = await super().search(query="*", limit=1000)

            if not all_memories:
                return {
                    "total_count": 0,
                    "memory_types": {},
                    "daily_activity": {},
                    "average_content_length": 0,
                }

            # Initialize statistics
            stats = {
                "total_count": len(all_memories),
                "memory_types": {},
                "daily_activity": {},
                "hourly_distribution": {},
                "participant_activity": {},
                "average_content_length": 0,
                "oldest_memory": None,
                "newest_memory": None,
            }

            # Analyze memories
            total_length = 0
            timestamps = []

            for memory in all_memories:
                metadata = memory.metadata

                # Content length analysis
                total_length += len(memory.content)

                # Memory type distribution
                memory_type = metadata.get("type", "unknown")
                stats["memory_types"][memory_type] = (
                    stats["memory_types"].get(memory_type, 0) + 1
                )

                # Temporal analysis
                timestamp = metadata.get("timestamp")
                if timestamp:
                    timestamps.append(timestamp)

                    # Daily activity
                    date = metadata.get("date", "unknown")
                    stats["daily_activity"][date] = (
                        stats["daily_activity"].get(date, 0) + 1
                    )

                    # Hourly distribution
                    hour = metadata.get("hour", 0)
                    stats["hourly_distribution"][hour] = (
                        stats["hourly_distribution"].get(hour, 0) + 1
                    )

                # Participant activity
                participants = metadata.get("participants", [])
                for participant in participants:
                    stats["participant_activity"][participant] = (
                        stats["participant_activity"].get(participant, 0) + 1
                    )

            # Calculate derived statistics
            stats["average_content_length"] = (
                total_length / len(all_memories) if all_memories else 0
            )

            if timestamps:
                stats["oldest_memory"] = datetime.fromtimestamp(
                    min(timestamps), UTC
                ).isoformat()
                stats["newest_memory"] = datetime.fromtimestamp(
                    max(timestamps), UTC
                ).isoformat()

            # Find most common type
            if stats["memory_types"]:
                stats["most_common_type"] = max(
                    stats["memory_types"], key=stats["memory_types"].get
                )

            # Find most active participant
            if stats["participant_activity"]:
                stats["most_active_participant"] = max(
                    stats["participant_activity"], key=stats["participant_activity"].get
                )

            logger.info(
                f"Generated statistics for {stats['total_count']} episodic memories"
            )
            return stats

        except Exception as e:
            logger.error(f"Error generating memory statistics: {e}")
            return {"total_count": 0, "error": str(e)}

    @log_function()
    async def get_classification_experiences(
        self, similar_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Get classification experiences similar to the current context.

        Retrieves past classification decisions and outcomes from episodic memory
        to support current classification decisions with experiential learning.

        Args:
            similar_context: Context dictionary containing asset_type, document_type, etc.

        Returns:
            List of similar classification experiences with outcomes

        Raises:
            ValueError: If similar_context is empty or invalid

        Example:
            >>> experiences = await episodic_memory.get_classification_experiences({
            ...     "asset_type": "CRE",
            ...     "document_type": "financial_statements",
            ...     "sender_domain": "propertymanagement.com"
            ... })
        """
        if not similar_context or not isinstance(similar_context, dict):
            raise ValueError("Similar context must be a non-empty dictionary")

        logger.info(
            f"Getting classification experiences for context: {list(similar_context.keys())}"
        )

        try:
            # Build search query from context
            query_parts = []
            if "asset_type" in similar_context:
                query_parts.append(f"asset type {similar_context['asset_type']}")
            if "document_type" in similar_context:
                query_parts.append(
                    f"document classification {similar_context['document_type']}"
                )
            if "sender_domain" in similar_context:
                query_parts.append(f"sender {similar_context['sender_domain']}")

            search_query = (
                " ".join(query_parts) if query_parts else "classification experience"
            )

            # Search for classification experiences
            experiences = await self.search(
                query=search_query,
                limit=config.episodic_search_limit,
                memory_type=EpisodicMemoryType.DECISION,
                filter={
                    "key": "metadata.decision_type",
                    "match": {"value": "document_classification"},
                },
            )

            # Process and rank experiences by similarity
            processed_experiences = []
            for experience in experiences:
                try:
                    metadata = experience.metadata

                    # Calculate context similarity score
                    similarity_score = self._calculate_context_similarity(
                        similar_context, metadata
                    )

                    experience_data = {
                        "experience_id": experience.id,
                        "content": experience.content,
                        "decision_outcome": metadata.get("decision_outcome", "unknown"),
                        "classification_result": metadata.get("classification_result"),
                        "confidence_score": metadata.get("confidence_score", 0.0),
                        "asset_type": metadata.get("asset_type"),
                        "document_category": metadata.get("document_category"),
                        "sender_info": metadata.get("sender_info", {}),
                        "timestamp": metadata.get("timestamp"),
                        "success": metadata.get("success", True),
                        "similarity_score": similarity_score,
                        "context_match": similarity_score
                        > config.context_similarity_threshold,
                    }

                    processed_experiences.append(experience_data)

                except Exception as e:
                    logger.debug(f"Error processing classification experience: {e}")
                    continue

            # Sort by similarity score
            processed_experiences.sort(
                key=lambda x: x["similarity_score"], reverse=True
            )

            logger.info(
                f"Found {len(processed_experiences)} classification experiences"
            )
            return processed_experiences

        except Exception as e:
            logger.error(f"Failed to get classification experiences: {e}")
            return []

    @log_function()
    async def get_asset_experiences(
        self, matching_criteria: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Get asset-related experiences matching specific criteria.

        Retrieves past asset identification and processing experiences
        to support current asset recognition and context understanding.

        Args:
            matching_criteria: Criteria dictionary for asset matching

        Returns:
            List of matching asset experiences with outcomes

        Raises:
            ValueError: If matching_criteria is empty or invalid

        Example:
            >>> experiences = await episodic_memory.get_asset_experiences({
            ...     "asset_type": "PE",
            ...     "sector": "technology",
            ...     "deal_stage": "due_diligence"
            ... })
        """
        if not matching_criteria or not isinstance(matching_criteria, dict):
            raise ValueError("Matching criteria must be a non-empty dictionary")

        logger.info(
            f"Getting asset experiences for criteria: {list(matching_criteria.keys())}"
        )

        try:
            # Build search query from criteria
            query_parts = []
            if "asset_type" in matching_criteria:
                query_parts.append(f"asset {matching_criteria['asset_type']}")
            if "sector" in matching_criteria:
                query_parts.append(f"sector {matching_criteria['sector']}")
            if "deal_stage" in matching_criteria:
                query_parts.append(f"stage {matching_criteria['deal_stage']}")

            search_query = " ".join(query_parts) if query_parts else "asset experience"

            # Search for asset-related experiences
            asset_experiences = await self.search(
                query=search_query,
                limit=config.episodic_search_limit,
                filter={
                    "should": [
                        {
                            "key": "metadata.decision_type",
                            "match": {"value": "asset_identification"},
                        },
                        {"key": "metadata.type", "match": {"value": "conversation"}},
                        {
                            "key": "metadata.category",
                            "match": {"value": "asset_processing"},
                        },
                    ]
                },
            )

            # Process asset experiences
            processed_experiences = []
            for experience in asset_experiences:
                try:
                    metadata = experience.metadata

                    # Calculate criteria match score
                    match_score = self._calculate_criteria_match(
                        matching_criteria, metadata
                    )

                    experience_data = {
                        "experience_id": experience.id,
                        "content": experience.content,
                        "asset_id": metadata.get("asset_id"),
                        "asset_type": metadata.get("asset_type"),
                        "deal_name": metadata.get("deal_name"),
                        "sector": metadata.get("sector"),
                        "deal_stage": metadata.get("deal_stage"),
                        "outcome": metadata.get("outcome", "unknown"),
                        "success": metadata.get("success", True),
                        "confidence": metadata.get("confidence", 0.0),
                        "timestamp": metadata.get("timestamp"),
                        "participants": metadata.get("participants", []),
                        "match_score": match_score,
                        "criteria_match": match_score > config.criteria_match_threshold,
                    }

                    processed_experiences.append(experience_data)

                except Exception as e:
                    logger.debug(f"Error processing asset experience: {e}")
                    continue

            # Sort by match score
            processed_experiences.sort(key=lambda x: x["match_score"], reverse=True)

            logger.info(f"Found {len(processed_experiences)} asset experiences")
            return processed_experiences

        except Exception as e:
            logger.error(f"Failed to get asset experiences: {e}")
            return []

    @log_function()
    async def record_decision_outcome(
        self,
        decision: dict[str, Any],
        outcome: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        """
        Record the outcome of a decision for future learning.

        Stores decision outcomes in episodic memory to build experiential
        knowledge for improved future decision making.

        Args:
            decision: Dictionary containing decision details
            outcome: Dictionary containing outcome results
            metadata: Additional metadata about the decision context

        Returns:
            Memory ID of the recorded decision outcome

        Raises:
            ValueError: If required parameters are missing or invalid

        Example:
            >>> outcome_id = await episodic_memory.record_decision_outcome(
            ...     decision={
            ...         "type": "document_classification",
            ...         "result": "financial_statements",
            ...         "confidence": 0.89
            ...     },
            ...     outcome={
            ...         "human_verified": True,
            ...         "correct": True,
            ...         "processing_time": 2.1
            ...     },
            ...     metadata={
            ...         "asset_type": "CRE",
            ...         "file_type": "pdf"
            ...     }
            ... )
        """
        if not decision or not isinstance(decision, dict):
            raise ValueError("Decision must be a non-empty dictionary")

        if not outcome or not isinstance(outcome, dict):
            raise ValueError("Outcome must be a non-empty dictionary")

        logger.info(f"Recording decision outcome: {decision.get('type', 'unknown')}")

        try:
            # Create comprehensive content for the decision outcome
            content_parts = []

            decision_type = decision.get("type", "unknown")
            content_parts.append(f"Decision type: {decision_type}")

            if "result" in decision:
                content_parts.append(f"Decision result: {decision['result']}")

            if "confidence" in decision:
                content_parts.append(f"Confidence: {decision['confidence']}")

            # Add outcome information
            if "correct" in outcome:
                status = "successful" if outcome["correct"] else "incorrect"
                content_parts.append(f"Outcome: {status}")

            if "human_verified" in outcome:
                verification = "verified" if outcome["human_verified"] else "unverified"
                content_parts.append(f"Human verification: {verification}")

            content = ". ".join(content_parts)

            # Prepare metadata for storage (excluding decision_type to avoid duplicate)
            outcome_metadata = {
                "decision_result": decision.get("result"),
                "decision_confidence": decision.get("confidence", 0.0),
                "outcome_correct": outcome.get("correct", True),
                "outcome_verified": outcome.get("human_verified", False),
                "processing_time": outcome.get("processing_time", 0.0),
                "success": outcome.get("correct", True),
                **metadata,
            }

            # Record as decision memory
            memory_id = await self.add_decision(
                content=content,
                decision_type=decision_type,
                decision_maker="system",
                rationale=f"Recorded outcome for learning: {outcome.get('correct', 'unknown')} result",
                **outcome_metadata,
            )

            logger.info(f"Decision outcome recorded: {memory_id[:8]}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to record decision outcome: {e}")
            raise

    @log_function()
    async def find_similar_cases(
        self, current_context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Find similar cases from past experiences for pattern recognition.

        Searches episodic memory for cases similar to the current context
        to identify patterns and provide decision support.

        Args:
            current_context: Current situation context for similarity matching

        Returns:
            List of similar cases with similarity scores and outcomes

        Raises:
            ValueError: If current_context is empty or invalid

        Example:
            >>> similar_cases = await episodic_memory.find_similar_cases({
            ...     "document_type": "lease_agreement",
            ...     "asset_type": "CRE",
            ...     "sender_type": "property_management",
            ...     "file_size": 2048000
            ... })
        """
        if not current_context or not isinstance(current_context, dict):
            raise ValueError("Current context must be a non-empty dictionary")

        logger.info(
            f"Finding similar cases for context: {list(current_context.keys())}"
        )

        try:
            # Build comprehensive search query
            query_parts = []
            for key, value in current_context.items():
                if isinstance(value, str):
                    query_parts.append(f"{key} {value}")
                elif isinstance(value, (int, float)):
                    query_parts.append(f"{key}")

            search_query = " ".join(query_parts)

            # Search across all memory types for similar cases
            similar_memories = await self.search(
                query=search_query,
                limit=config.episodic_search_limit * 2,  # Cast wider net for similarity
            )

            # Process and rank similar cases
            similar_cases = []
            for memory in similar_memories:
                try:
                    metadata = memory.metadata

                    # Calculate comprehensive similarity score
                    similarity_score = self._calculate_comprehensive_similarity(
                        current_context, metadata, memory.content
                    )

                    # Only include cases with meaningful similarity
                    if similarity_score > config.similarity_threshold:
                        case_data = {
                            "case_id": memory.id,
                            "content": memory.content,
                            "memory_type": metadata.get("type", "unknown"),
                            "context": {
                                key: metadata.get(key)
                                for key in current_context.keys()
                                if key in metadata
                            },
                            "outcome": metadata.get("outcome", "unknown"),
                            "success": metadata.get("success", True),
                            "timestamp": metadata.get("timestamp"),
                            "similarity_score": similarity_score,
                            "match_factors": self._identify_match_factors(
                                current_context, metadata
                            ),
                        }

                        similar_cases.append(case_data)

                except Exception as e:
                    logger.debug(f"Error processing similar case: {e}")
                    continue

            # Sort by similarity score
            similar_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Limit to most relevant cases
            top_cases = similar_cases[: config.max_similar_cases]

            logger.info(
                f"Found {len(top_cases)} similar cases (from {len(similar_memories)} searched)"
            )
            return top_cases

        except Exception as e:
            logger.error(f"Failed to find similar cases: {e}")
            return []

    @log_function()
    async def get_success_patterns(self, decision_type: str) -> dict[str, Any]:
        """
        Get success patterns for a specific decision type.

        Analyzes past decisions to identify patterns that lead to successful outcomes
        for improved decision making and pattern recognition.

        Args:
            decision_type: Type of decision to analyze patterns for

        Returns:
            Dictionary containing success patterns and insights

        Raises:
            ValueError: If decision_type is empty or invalid

        Example:
            >>> patterns = await episodic_memory.get_success_patterns("document_classification")
            >>> print(patterns['success_rate'])  # 0.87
            >>> print(patterns['key_factors'])   # ['high_confidence', 'verified_sender']
        """
        if not decision_type or not isinstance(decision_type, str):
            raise ValueError("Decision type must be a non-empty string")

        decision_type = decision_type.strip()
        logger.info(f"Analyzing success patterns for decision type: {decision_type}")

        try:
            # Search for decisions of the specified type
            decision_memories = await self.search(
                query=f"decision {decision_type}",
                limit=config.pattern_analysis_limit,
                memory_type=EpisodicMemoryType.DECISION,
                filter={
                    "key": "metadata.decision_type",
                    "match": {"value": decision_type},
                },
            )

            if not decision_memories:
                logger.info(f"No decisions found for type: {decision_type}")
                return {
                    "decision_type": decision_type,
                    "total_decisions": 0,
                    "success_rate": 0.0,
                    "patterns": {},
                    "key_factors": [],
                    "recommendations": [],
                }

            # Analyze success patterns
            successful_decisions = []
            failed_decisions = []

            for memory in decision_memories:
                metadata = memory.metadata
                is_successful = metadata.get("success", True) and metadata.get(
                    "outcome_correct", True
                )

                if is_successful:
                    successful_decisions.append(memory)
                else:
                    failed_decisions.append(memory)

            # Calculate success metrics
            total_decisions = len(decision_memories)
            successful_count = len(successful_decisions)
            success_rate = (
                successful_count / total_decisions if total_decisions > 0 else 0.0
            )

            # Identify success patterns
            success_patterns = self._analyze_decision_patterns(
                successful_decisions, "success"
            )
            failure_patterns = self._analyze_decision_patterns(
                failed_decisions, "failure"
            )

            # Extract key success factors
            key_factors = self._extract_key_factors(success_patterns, failure_patterns)

            # Generate recommendations
            recommendations = self._generate_pattern_recommendations(
                success_patterns, failure_patterns, decision_type
            )

            patterns_result = {
                "decision_type": decision_type,
                "total_decisions": total_decisions,
                "successful_decisions": successful_count,
                "failed_decisions": len(failed_decisions),
                "success_rate": success_rate,
                "success_patterns": success_patterns,
                "failure_patterns": failure_patterns,
                "key_factors": key_factors,
                "recommendations": recommendations,
                "confidence": (
                    "high"
                    if total_decisions >= 10
                    else "medium" if total_decisions >= 5 else "low"
                ),
            }

            logger.info(
                f"Success pattern analysis complete: {success_rate:.2%} success rate from {total_decisions} decisions"
            )
            return patterns_result

        except Exception as e:
            logger.error(f"Failed to analyze success patterns for {decision_type}: {e}")
            return {
                "decision_type": decision_type,
                "total_decisions": 0,
                "success_rate": 0.0,
                "error": str(e),
            }

    def _calculate_context_similarity(
        self, context1: dict[str, Any], context2: dict[str, Any]
    ) -> float:
        """Calculate similarity score between two contexts."""
        if not context1 or not context2:
            return 0.0

        matching_keys = set(context1.keys()) & set(context2.keys())
        if not matching_keys:
            return 0.0

        matches = 0
        total_comparisons = 0

        for key in matching_keys:
            val1, val2 = context1[key], context2[key]
            total_comparisons += 1

            if val1 == val2:
                matches += 1
            elif isinstance(val1, str) and isinstance(val2, str):
                # Partial string matching
                if val1.lower() in val2.lower() or val2.lower() in val1.lower():
                    matches += 0.5

        return matches / total_comparisons if total_comparisons > 0 else 0.0

    def _calculate_criteria_match(
        self, criteria: dict[str, Any], metadata: dict[str, Any]
    ) -> float:
        """Calculate how well metadata matches given criteria."""
        if not criteria:
            return 0.0

        total_criteria = len(criteria)
        matches = 0.0

        for key, expected_value in criteria.items():
            if key in metadata:
                actual_value = metadata[key]
                if actual_value == expected_value:
                    matches += 1.0
                elif isinstance(expected_value, str) and isinstance(actual_value, str):
                    if expected_value.lower() in actual_value.lower():
                        matches += 0.7

        return matches / total_criteria if total_criteria > 0 else 0.0

    def _calculate_comprehensive_similarity(
        self, context: dict[str, Any], metadata: dict[str, Any], content: str
    ) -> float:
        """Calculate comprehensive similarity including context, metadata, and content."""
        # Context similarity (40% weight)
        context_sim = self._calculate_context_similarity(context, metadata) * 0.4

        # Content similarity (30% weight) - simple keyword matching
        content_sim = 0.0
        context_keywords = [
            str(v).lower() for v in context.values() if isinstance(v, (str, int, float))
        ]
        content_lower = content.lower()

        if context_keywords:
            keyword_matches = sum(
                1 for keyword in context_keywords if keyword in content_lower
            )
            content_sim = (keyword_matches / len(context_keywords)) * 0.3

        # Metadata relevance (30% weight)
        metadata_sim = (
            len(set(context.keys()) & set(metadata.keys())) / len(context.keys()) * 0.3
        )

        return context_sim + content_sim + metadata_sim

    def _identify_match_factors(
        self, context: dict[str, Any], metadata: dict[str, Any]
    ) -> list[str]:
        """Identify specific factors that contributed to the match."""
        factors = []

        for key in context.keys():
            if key in metadata and context[key] == metadata[key]:
                factors.append(f"exact_{key}_match")
            elif key in metadata:
                factors.append(f"partial_{key}_match")

        return factors

    def _analyze_decision_patterns(
        self, decisions: list[MemoryItem], pattern_type: str
    ) -> dict[str, Any]:
        """Analyze patterns in a set of decisions."""
        if not decisions:
            return {}

        patterns = {
            "count": len(decisions),
            "common_attributes": {},
            "confidence_distribution": {},
            "temporal_patterns": {},
        }

        # Analyze common attributes
        attribute_counts = {}
        confidence_values = []

        for decision in decisions:
            metadata = decision.metadata

            # Track confidence values
            if "decision_confidence" in metadata:
                confidence_values.append(metadata["decision_confidence"])

            # Count attribute occurrences
            for key, value in metadata.items():
                if isinstance(value, (str, int, bool)):
                    attr_key = f"{key}:{value}"
                    attribute_counts[attr_key] = attribute_counts.get(attr_key, 0) + 1

        # Find most common attributes
        if attribute_counts:
            total_decisions = len(decisions)
            patterns["common_attributes"] = {
                attr: count / total_decisions
                for attr, count in attribute_counts.items()
                if count / total_decisions > 0.5  # Appears in >50% of cases
            }

        # Confidence distribution
        if confidence_values:
            patterns["confidence_distribution"] = {
                "mean": sum(confidence_values) / len(confidence_values),
                "min": min(confidence_values),
                "max": max(confidence_values),
                "count": len(confidence_values),
            }

        return patterns

    def _extract_key_factors(
        self, success_patterns: dict[str, Any], failure_patterns: dict[str, Any]
    ) -> list[str]:
        """Extract key factors that differentiate success from failure."""
        key_factors = []

        success_attrs = success_patterns.get("common_attributes", {})
        failure_attrs = failure_patterns.get("common_attributes", {})

        # Find attributes more common in successes
        for attr, success_rate in success_attrs.items():
            failure_rate = failure_attrs.get(attr, 0.0)
            if success_rate > failure_rate + 0.2:  # 20% higher in successes
                key_factors.append(attr)

        return key_factors

    def _generate_pattern_recommendations(
        self,
        success_patterns: dict[str, Any],
        failure_patterns: dict[str, Any],
        decision_type: str,
    ) -> list[str]:
        """Generate actionable recommendations based on patterns."""
        recommendations = []

        # Confidence-based recommendations
        success_conf = success_patterns.get("confidence_distribution", {})
        failure_conf = failure_patterns.get("confidence_distribution", {})

        if success_conf.get("mean", 0) > failure_conf.get("mean", 0):
            recommendations.append(
                f"Higher confidence scores correlate with success in {decision_type} decisions"
            )

        # Attribute-based recommendations
        success_attrs = success_patterns.get("common_attributes", {})
        for attr, rate in success_attrs.items():
            if rate > 0.7:  # Very common in successes
                recommendations.append(f"Consider prioritizing cases with {attr}")

        if not recommendations:
            recommendations.append(
                f"Insufficient data for specific recommendations in {decision_type}"
            )

        return recommendations


# Demonstration and testing functions
@log_function()
async def demo_episodic_memory() -> None:
    """
    Demonstration of episodic memory system capabilities.

    Showcases the episodic memory features including
    conversation tracking, decision recording, temporal search,
    and business intelligence for asset management environments.
    """
    logger.info("Starting EpisodicMemory demonstration")

    episodic_memory = EpisodicMemory()

    try:
        # Add sample conversations
        logger.info("Adding sample conversations and events...")

        # Investment meeting conversation
        _conv_id = await episodic_memory.add_conversation(
            content="Discussed Series B investment opportunity in PropTech startup. Strong team with proven track record in real estate technology. Market size estimated at $50B with 15% CAGR.",
            participants=["ic@fund.com", "analyst@fund.com", "ceo@proptech.com"],
            subject="PropTech Series B Due Diligence",
            category="investment_opportunity",
            sector="proptech",
            stage="series_b",
        )

        # Investment decision
        _decision_id = await episodic_memory.add_decision(
            content="Investment Committee approved $25M Series B investment in PropTech startup",
            decision_type="investment_approval",
            decision_maker="Investment Committee",
            rationale="Strong market position, experienced team, and clear path to profitability",
            deal_value=25000000,
            sector="proptech",
            approved=True,
        )

        # Client feedback
        _feedback_id = await episodic_memory.add_feedback(
            content="Portfolio performance exceeded expectations in Q3. Particularly impressed with PropTech allocation strategy.",
            feedback_type="positive",
            source="institutional_investor",
            sentiment="positive",
            quarter="Q3_2024",
        )

        logger.info("✓ Added sample episodic memories")

        # Test semantic search
        logger.info("Testing semantic search capabilities...")

        search_results = await episodic_memory.search(
            query="PropTech investment decision", limit=5
        )

        logger.info(f"Found {len(search_results)} results for PropTech search")
        for result in search_results:
            memory_type = result.metadata.get("type", "unknown")
            logger.info(f"  - {memory_type}: {result.content[:100]}...")

        # Test participant search
        logger.info("Testing participant-based search...")

        participant_results = await episodic_memory.search_by_participants(
            participant_email="ic@fund.com", limit=10
        )

        logger.info(f"Found {len(participant_results)} memories involving ic@fund.com")

        # Test decision type filtering
        logger.info("Testing decision type filtering...")

        decision_results = await episodic_memory.search(
            query="investment", memory_type=EpisodicMemoryType.DECISION, limit=5
        )

        logger.info(f"Found {len(decision_results)} investment decisions")

        # Test recent memories
        logger.info("Testing recent memories retrieval...")

        recent_memories = await episodic_memory.get_recent_memories(hours=24, limit=10)

        logger.info(f"Found {len(recent_memories)} recent memories in last 24 hours")

        # Generate statistics
        logger.info("Generating memory statistics...")

        stats = await episodic_memory.get_memory_statistics()
        logger.info("Memory statistics:")
        logger.info(f"  - Total memories: {stats['total_count']}")
        logger.info(f"  - Memory types: {stats['memory_types']}")
        logger.info(
            f"  - Average content length: {stats['average_content_length']:.1f} chars"
        )

        if stats.get("most_common_type"):
            logger.info(f"  - Most common type: {stats['most_common_type']}")

        logger.info("EpisodicMemory demonstration completed successfully")

    except Exception as e:
        logger.error(f"EpisodicMemory demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # # Standard library imports
    import asyncio

    asyncio.run(demo_episodic_memory())

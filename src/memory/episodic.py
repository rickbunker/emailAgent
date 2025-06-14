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
        max_items: int | None = 1000,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize episodic memory system.

        Args:
            max_items: Maximum number of episodic memories to store (default: 1000)
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

            # Perform semantic search
            results = await super().search(query, limit, search_filter)

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

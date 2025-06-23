"""
Episodic learning module for the asset management system.

This module implements episodic memory functionality that:
1. Learns from past classification decisions and their outcomes
2. Stores experiences of successful and failed identifications
3. Provides confidence adjustments based on historical patterns
4. Enables continuous improvement over time

This is critical for the system to improve based on human feedback
and real-world usage patterns.
"""

# # Standard library imports
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

# # Local application imports
from src.asset_management.core.data_models import (
    AssetMatch,
    CategoryMatch,
    ClassificationContext,
    IdentificationContext,
)
from src.asset_management.core.exceptions import MemorySystemError
from src.memory.episodic import EpisodicMemory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


@dataclass
class Decision:
    """Represents a decision made by the system."""

    decision_type: str  # 'asset_identification' or 'document_classification'
    context: dict[str, Any]  # Original context
    result: dict[str, Any]  # What the system decided
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    decision_id: str = field(default_factory=lambda: str(datetime.now(UTC).timestamp()))


@dataclass
class Outcome:
    """Represents the outcome of a decision."""

    success: bool
    feedback_type: str  # 'human_correction', 'auto_validation', 'system_error'
    correct_result: Optional[dict[str, Any]] = None
    error_details: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class EpisodicLearner:
    """
    Service for learning from past experiences.

    This integrates with the episodic memory system to:
    - Record decisions and their outcomes
    - Learn patterns from successes and failures
    - Provide confidence adjustments based on history
    - Enable continuous improvement
    """

    def __init__(self, episodic_memory: Optional[EpisodicMemory] = None):
        """
        Initialize the episodic learner.

        Args:
            episodic_memory: Episodic memory instance. If not provided,
                           creates a new one.
        """
        self.memory = episodic_memory or self._create_episodic_memory()
        self.learning_enabled = getattr(config, "episodic_learning_enabled", True)
        self.confidence_boost_threshold = getattr(
            config, "episodic_confidence_boost_threshold", 0.8
        )
        logger.info(
            f"Episodic learner initialized " f"(learning: {self.learning_enabled})"
        )

    def _create_episodic_memory(self) -> EpisodicMemory:
        """Create a new episodic memory instance."""
        try:
            # # Third-party imports
            from qdrant_client import QdrantClient

            client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
            return EpisodicMemory(
                qdrant_client=client,
                collection_name="episodic",
                max_items=getattr(config, "episodic_memory_max_items", 100000),
            )
        except Exception as e:
            logger.error(f"Failed to create episodic memory: {e}")
            raise MemorySystemError(
                "Could not initialize episodic memory", details={"error": str(e)}
            )

    @log_function()
    async def record_identification_decision(
        self, context: IdentificationContext, result: Optional[AssetMatch]
    ) -> str:
        """
        Record an asset identification decision.

        Args:
            context: The identification context
            result: The asset match result (or None)

        Returns:
            Decision ID for future reference
        """
        if not self.learning_enabled:
            return ""

        decision = Decision(
            decision_type="asset_identification",
            context={
                "filename": context.filename,
                "sender_email": context.sender_email,
                "email_subject": context.email_subject,
                "email_body": context.email_body,
            },
            result=(
                {
                    "matched": result is not None,
                    "asset_id": result.asset_id if result else None,
                    "asset_name": result.asset_name if result else None,
                    "confidence": result.confidence if result else 0.0,
                    "match_source": result.match_source if result else None,
                }
                if result
                else {"matched": False}
            ),
            confidence=result.confidence if result else 0.0,
        )

        # Store in episodic memory
        metadata = {
            "decision_id": decision.decision_id,
            "result": decision.result,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp.isoformat(),
            "type": "asset_identification",
        }
        await self.memory.add(
            content=json.dumps(decision.context),
            metadata=metadata,
        )

        logger.info(
            f"Recorded identification decision: {decision.decision_id} "
            f"(matched: {decision.result.get('matched')})"
        )

        return decision.decision_id

    @log_function()
    async def record_classification_decision(
        self, context: ClassificationContext, result: Optional[CategoryMatch]
    ) -> str:
        """
        Record a document classification decision.

        Args:
            context: The classification context
            result: The category match result (or None)

        Returns:
            Decision ID for future reference
        """
        if not self.learning_enabled:
            return ""

        decision = Decision(
            decision_type="document_classification",
            context={
                "filename": context.filename,
                "asset_type": context.asset_type.value,
                "asset_id": context.asset_id,
                "email_subject": context.email_subject,
                "email_body": context.email_body,
            },
            result=(
                {
                    "classified": result is not None,
                    "category": result.category.value if result else None,
                    "confidence": result.confidence if result else 0.0,
                    "match_source": result.match_source if result else None,
                }
                if result
                else {"classified": False}
            ),
            confidence=result.confidence if result else 0.0,
        )

        # Store in episodic memory
        metadata = {
            "decision_id": decision.decision_id,
            "result": decision.result,
            "confidence": decision.confidence,
            "timestamp": decision.timestamp.isoformat(),
            "type": "document_classification",
        }
        await self.memory.add(
            content=json.dumps(decision.context),
            metadata=metadata,
        )

        logger.info(
            f"Recorded classification decision: {decision.decision_id} "
            f"(classified: {decision.result.get('classified')})"
        )

        return decision.decision_id

    @log_function()
    async def record_outcome(self, decision_id: str, outcome: Outcome) -> None:
        """
        Record the outcome of a previous decision.

        This is called when we learn whether a decision was correct,
        either through human feedback or automatic validation.

        Args:
            decision_id: ID of the original decision
            outcome: The outcome information
        """
        if not self.learning_enabled:
            return

        # Store outcome in episodic memory
        await self.memory.record_decision_outcome(
            decision={"decision_id": decision_id, "type": "update"},
            outcome={
                "success": outcome.success,
                "feedback_type": outcome.feedback_type,
                "correct_result": outcome.correct_result,
                "error_details": outcome.error_details,
                "timestamp": outcome.timestamp.isoformat(),
            },
            metadata={"outcome_recorded": True, "learning_applied": True},
        )

        logger.info(
            f"Recorded outcome for decision {decision_id}: "
            f"success={outcome.success}, type={outcome.feedback_type}"
        )

    @log_function()
    async def get_identification_confidence_adjustment(
        self, context: IdentificationContext, proposed_match: Optional[AssetMatch]
    ) -> float:
        """
        Get confidence adjustment based on past experiences.

        Args:
            context: Current identification context
            proposed_match: The match being considered

        Returns:
            Confidence adjustment (-1.0 to 1.0)
        """
        if not self.learning_enabled or not proposed_match:
            return 0.0

        try:
            # Find similar past cases
            similar_cases = await self.memory.find_similar_cases(
                {
                    "filename": context.filename,
                    "asset_match": proposed_match.asset_id,
                    "match_source": proposed_match.match_source,
                }
            )

            if not similar_cases:
                return 0.0

            # Calculate adjustment based on past success rate
            successful = sum(
                1
                for case in similar_cases
                if case.get("metadata", {}).get("outcome", {}).get("success", False)
            )
            total = len(similar_cases)

            if total < 3:  # Not enough history
                return 0.0

            success_rate = successful / total

            # Boost confidence if high success rate
            if success_rate >= self.confidence_boost_threshold:
                adjustment = min(0.2, (success_rate - 0.5) * 0.4)
                logger.info(
                    f"Episodic boost: +{adjustment:.2f} "
                    f"(success rate: {success_rate:.2f})"
                )
                return adjustment

            # Reduce confidence if low success rate
            elif success_rate < 0.3:
                adjustment = max(-0.2, (success_rate - 0.5) * 0.4)
                logger.info(
                    f"Episodic penalty: {adjustment:.2f} "
                    f"(success rate: {success_rate:.2f})"
                )
                return adjustment

            return 0.0

        except Exception as e:
            logger.error(f"Error getting confidence adjustment: {e}")
            return 0.0

    @log_function()
    async def get_classification_confidence_adjustment(
        self, context: ClassificationContext, proposed_category: Optional[CategoryMatch]
    ) -> float:
        """
        Get confidence adjustment for document classification.

        Args:
            context: Current classification context
            proposed_category: The category being considered

        Returns:
            Confidence adjustment (-1.0 to 1.0)
        """
        if not self.learning_enabled or not proposed_category:
            return 0.0

        try:
            # Find similar past cases
            similar_cases = await self.memory.find_similar_cases(
                {
                    "filename_pattern": context.filename,
                    "asset_type": context.asset_type.value,
                    "category": proposed_category.category.value,
                }
            )

            if not similar_cases:
                return 0.0

            # Calculate adjustment based on past success rate
            successful = sum(
                1
                for case in similar_cases
                if case.get("metadata", {}).get("outcome", {}).get("success", False)
            )
            total = len(similar_cases)

            if total < 3:  # Not enough history
                return 0.0

            success_rate = successful / total

            # Apply adjustment based on success rate
            if success_rate >= self.confidence_boost_threshold:
                return min(0.15, (success_rate - 0.5) * 0.3)
            elif success_rate < 0.3:
                return max(-0.15, (success_rate - 0.5) * 0.3)

            return 0.0

        except Exception as e:
            logger.error(f"Error getting classification adjustment: {e}")
            return 0.0

    async def get_learning_stats(self) -> dict[str, Any]:
        """Get statistics about the learning system."""
        try:
            # Get success patterns
            identification_patterns = await self.memory.get_success_patterns(
                "asset_identification"
            )
            classification_patterns = await self.memory.get_success_patterns(
                "document_classification"
            )

            return {
                "learning_enabled": self.learning_enabled,
                "total_decisions": len(identification_patterns)
                + len(classification_patterns),
                "identification_patterns": len(identification_patterns),
                "classification_patterns": len(classification_patterns),
                "confidence_boost_threshold": self.confidence_boost_threshold,
            }
        except Exception as e:
            logger.error(f"Error getting learning stats: {e}")
            return {"error": str(e)}

"""
Relevance Filter Node - Determines if emails contain investment-related content.

This node queries memory systems for patterns and rules rather than hardcoding
business logic. All decision criteria come from semantic and procedural memory.
"""

# # Standard library imports
from typing import Any

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class RelevanceFilterNode:
    """
    Analyzes emails to determine relevance using memory-driven patterns.

    Queries semantic memory for keywords/patterns and procedural memory for rules.
    """

    def __init__(self, semantic_memory=None, procedural_memory=None) -> None:
        """
        Initialize the relevance filter with memory system connections.

        Args:
            semantic_memory: Semantic memory system for patterns/keywords
            procedural_memory: Procedural memory system for rules/thresholds
        """
        self.semantic_memory = semantic_memory
        self.procedural_memory = procedural_memory
        self.relevance_threshold = config.relevance_threshold

        logger.info(
            f"Relevance filter initialized (threshold: {self.relevance_threshold})"
        )

    @log_function()
    async def evaluate_relevance(
        self, email_data: dict[str, Any]
    ) -> tuple[str, float, dict[str, Any]]:
        """
        Evaluate email relevance using memory-driven patterns.

        Args:
            email_data: Email metadata including subject, sender, body, attachments

        Returns:
            Tuple of (classification, confidence_score, reasoning)

        Raises:
            ValueError: If email_data is malformed
        """
        if not email_data or "subject" not in email_data:
            raise ValueError("Invalid email_data: missing required fields")

        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body = email_data.get("body", "")
        attachments = email_data.get("attachments", [])

        logger.info(f"Evaluating relevance: {subject[:50]}...")

        reasoning = {"decision_factors": [], "confidence_factors": [], "flags": []}

        # For now, use simple heuristics until memory systems are connected
        # TODO: Replace with memory queries once semantic/procedural memory is integrated
        relevance_score = await self._simple_relevance_check(
            subject, sender, body, attachments, reasoning
        )

        # Determine classification based on score
        if relevance_score >= self.relevance_threshold:
            classification = "relevant"
            reasoning["confidence_factors"].append(
                f"Score {relevance_score:.2f} >= threshold {self.relevance_threshold}"
            )
        elif relevance_score >= config.low_confidence_threshold:
            classification = "uncertain"
            reasoning["flags"].append(f"Low confidence: {relevance_score:.2f}")
        else:
            classification = "irrelevant"
            reasoning["confidence_factors"].append(
                f"Score {relevance_score:.2f} below threshold"
            )

        # Check for obvious spam patterns (basic protection)
        if await self._is_obvious_spam(subject, body, sender):
            classification = "spam"
            relevance_score = 0.1
            reasoning["flags"].append("Obvious spam detected")

        logger.info(
            f"Classification: {classification} (confidence: {relevance_score:.2f})"
        )

        return classification, relevance_score, reasoning

    async def _simple_relevance_check(
        self,
        subject: str,
        sender: str,
        body: str,
        attachments: list[dict[str, Any]],
        reasoning: dict[str, Any],
    ) -> float:
        """
        Simple relevance check until memory systems are integrated.

        This is a placeholder that will be replaced with memory queries.
        """
        score = 0.0

        # Basic keyword matching (will be replaced with semantic memory queries)
        investment_terms = [
            "fund",
            "financial",
            "statement",
            "report",
            "investment",
            "asset",
            "portfolio",
        ]

        subject_lower = subject.lower()
        body_lower = body.lower()

        # Check subject for investment terms
        subject_matches = sum(1 for term in investment_terms if term in subject_lower)
        if subject_matches > 0:
            score += 0.3
            reasoning["decision_factors"].append(
                f"Investment terms in subject: {subject_matches}"
            )

        # Check body for investment terms
        body_matches = sum(1 for term in investment_terms if term in body_lower)
        if body_matches > 0:
            score += 0.2
            reasoning["decision_factors"].append(
                f"Investment terms in body: {body_matches}"
            )

        # Check attachments
        if attachments:
            relevant_extensions = [".pdf", ".xlsx", ".xls", ".docx"]
            relevant_attachments = sum(
                1
                for att in attachments
                if any(
                    att.get("filename", "").lower().endswith(ext)
                    for ext in relevant_extensions
                )
            )
            if relevant_attachments > 0:
                score += 0.4
                reasoning["decision_factors"].append(
                    f"Relevant attachments: {relevant_attachments}"
                )

        # Boost for trusted domains (basic check)
        if any(
            domain in sender.lower()
            for domain in [".gov", ".edu", "investor", "finance"]
        ):
            score += 0.2
            reasoning["decision_factors"].append("Trusted sender domain")

        return min(score, 1.0)  # Cap at 1.0

    async def _is_obvious_spam(self, subject: str, body: str, sender: str) -> bool:
        """
        Basic spam detection until procedural memory rules are available.

        This will be replaced with procedural memory queries.
        """
        combined_text = f"{subject} {body} {sender}".lower()

        # Very obvious spam indicators
        spam_terms = ["you've won", "lottery", "viagra", "casino", "nigerian prince"]

        return any(term in combined_text for term in spam_terms)

    async def query_semantic_patterns(
        self, email_data: dict[str, Any]
    ) -> dict[str, float]:
        """
        Query semantic memory for investment-related patterns.

        TODO: Implement when semantic memory is available.

        Args:
            email_data: Email content to analyze

        Returns:
            Dictionary of pattern matches with confidence scores
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, using fallback")
            return {}

        # This will query semantic memory for:
        # - Investment keywords and phrases
        # - Known sender patterns
        # - Document type indicators
        # - Historical classification patterns

        return {}

    async def query_procedural_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Query procedural memory for decision rules and thresholds.

        TODO: Implement when procedural memory is available.

        Args:
            context: Current evaluation context

        Returns:
            Dictionary of applicable rules and thresholds
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return {"thresholds": {"relevance": self.relevance_threshold}}

        # This will query procedural memory for:
        # - Dynamic threshold adjustments
        # - Scoring weights for different factors
        # - Conditional rules based on context
        # - Learned decision patterns from feedback

        return {}

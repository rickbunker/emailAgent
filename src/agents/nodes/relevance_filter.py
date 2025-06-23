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

    def __init__(self, memory_systems=None) -> None:
        """
        Initialize the relevance filter with memory system connections.

        Args:
            memory_systems: Dictionary with all memory systems (semantic, procedural, etc.)
        """
        if memory_systems:
            self.semantic_memory = memory_systems.get("semantic")
            self.procedural_memory = memory_systems.get("procedural")
        else:
            # Initialize simplified memory systems directly
            # # Local application imports
            from src.memory import create_memory_systems

            systems = create_memory_systems()
            self.semantic_memory = systems["semantic"]
            self.procedural_memory = systems["procedural"]

        self.relevance_threshold = config.relevance_threshold

        logger.info(
            f"✅ Relevance filter initialized with simple memory systems (threshold: {self.relevance_threshold})"
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

        # Use memory systems for relevance evaluation
        relevance_score = await self._memory_driven_relevance_check(
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

    async def _memory_driven_relevance_check(
        self,
        subject: str,
        sender: str,
        body: str,
        attachments: list[dict[str, Any]],
        reasoning: dict[str, Any],
    ) -> float:
        """
        Memory-driven relevance check using simple memory systems.

        Uses procedural memory for rules and semantic memory for patterns.
        """
        score = 0.0

        # Get relevance rules from procedural memory
        relevance_rules = self.procedural_memory.get_relevance_rules()

        # Combine all text for analysis
        combined_text = f"{subject} {body}".lower()

        # Apply each relevance rule
        for rule in relevance_rules:
            rule_score = 0.0
            patterns = rule.get("patterns", [])
            weight = rule.get("weight", 0.5)

            # Check how many patterns match
            pattern_matches = sum(
                1 for pattern in patterns if pattern.lower() in combined_text
            )

            if pattern_matches > 0:
                # Calculate rule score based on pattern matches
                rule_score = min(pattern_matches * 0.2, weight)
                score += rule_score
                reasoning["decision_factors"].append(
                    f"{rule.get('description', 'Rule')}: {pattern_matches} patterns matched (score: {rule_score:.2f})"
                )

        # Check document categories from semantic memory
        doc_categories = self.semantic_memory.search_document_categories(combined_text)
        if doc_categories:
            category_score = 0.0
            for doc_cat in doc_categories[:2]:  # Top 2 categories
                cat_score = doc_cat.get("score", 0.0) * 0.3
                category_score += cat_score
                reasoning["decision_factors"].append(
                    f"Document category '{doc_cat['category']}' match (score: {cat_score:.2f})"
                )
            score += category_score

        # Check attachments using semantic memory file rules
        if attachments:
            attachment_score = 0.0
            relevant_count = 0

            for attachment in attachments:
                filename = attachment.get("filename", "")
                file_ext = filename.lower().split(".")[-1] if "." in filename else ""

                file_rules = self.semantic_memory.get_file_type_rules(file_ext)
                if file_rules and file_rules.get("allowed", False):
                    attachment_score += 0.2
                    relevant_count += 1

            if relevant_count > 0:
                score += attachment_score
                reasoning["decision_factors"].append(
                    f"Relevant attachments: {relevant_count} (score: {attachment_score:.2f})"
                )

        # Check sender trust (simple domain check for now)
        if any(
            domain in sender.lower()
            for domain in [".gov", ".edu", "investor", "finance", "capital"]
        ):
            score += 0.15
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

        Args:
            email_data: Email content to analyze

        Returns:
            Dictionary of pattern matches with confidence scores
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, using fallback")
            return {}

        patterns = {}

        # Combine email content for analysis
        content = f"{email_data.get('subject', '')} {email_data.get('body', '')}"

        # Query document categories
        doc_categories = self.semantic_memory.search_document_categories(content)
        for doc_cat in doc_categories:
            patterns[f"doc_category_{doc_cat['category']}"] = doc_cat.get("score", 0.0)

        # Query asset profiles
        asset_profiles = self.semantic_memory.search_asset_profiles(content)
        for asset in asset_profiles:
            patterns[f"asset_profile_{asset['asset_id']}"] = asset.get("score", 0.0)

        logger.debug(f"Found {len(patterns)} semantic patterns")
        return patterns

    async def query_procedural_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Query procedural memory for decision rules and thresholds.

        Args:
            context: Current evaluation context

        Returns:
            Dictionary of applicable rules and thresholds
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return {"thresholds": {"relevance": self.relevance_threshold}}

        rules = {
            "thresholds": {"relevance": self.relevance_threshold},
            "relevance_rules": self.procedural_memory.get_relevance_rules(),
            "file_processing_rules": self.procedural_memory.get_file_processing_rules(),
        }

        logger.debug(
            f"Retrieved {len(rules['relevance_rules'])} relevance rules from procedural memory"
        )
        return rules

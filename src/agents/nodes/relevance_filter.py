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
            memory_systems: Dictionary with all memory systems (semantic, procedural, episodic)
        """
        if memory_systems:
            self.semantic_memory = memory_systems.get("semantic")
            self.procedural_memory = memory_systems.get("procedural")
            self.episodic_memory = memory_systems.get("episodic")
        else:
            # Initialize simplified memory systems directly
            # # Local application imports
            from src.memory import create_memory_systems

            systems = create_memory_systems()
            self.semantic_memory = systems["semantic"]
            self.procedural_memory = systems["procedural"]
            self.episodic_memory = systems["episodic"]

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
        logger.info(
            f"🚨 EVALUATE_RELEVANCE CALLED - sender: {sender}, attachments: {len(attachments)}"
        )

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

        Uses procedural memory for rules, semantic memory for patterns,
        and episodic memory for learned sender patterns.
        """
        logger.info(
            f"🔍 ENTERING _memory_driven_relevance_check for sender: {sender}, subject: {subject[:30]}..."
        )
        score = 0.0

        # Check episodic memory for learned sender patterns FIRST
        episodic_adjustment = await self._check_episodic_sender_patterns(
            sender, reasoning
        )
        score += episodic_adjustment

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
                # Apply full rule weight when patterns match - the weight represents the importance of this rule type
                rule_score = weight
                score += rule_score
                reasoning["decision_factors"].append(
                    f"{rule.get('description', 'Rule')}: {pattern_matches} patterns matched (score: {rule_score:.2f})"
                )

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

    async def _check_episodic_sender_patterns(
        self, sender: str, reasoning: dict[str, Any]
    ) -> float:
        """
        Check episodic memory for learned sender patterns from human feedback.

        This method ONLY uses human feedback to influence future decisions,
        NOT the system's own processing history, to avoid reinforcing mistakes.

        Args:
            sender: Email sender address
            reasoning: Reasoning dict to append decision factors

        Returns:
            Score adjustment based on human feedback learning (0.0 to 0.5)
        """
        if not self.episodic_memory or not sender:
            logger.info(
                f"Episodic memory check skipped: episodic_memory={bool(self.episodic_memory)}, sender='{sender}'"
            )
            return 0.0

        try:
            logger.info(f"Checking human feedback patterns for sender: {sender}")

            # Query ONLY human feedback patterns, NOT processing history
            feedback_patterns = self.episodic_memory.search_human_feedback_patterns(
                sender=sender, limit=10
            )
            logger.info(
                f"Found {len(feedback_patterns)} human feedback records for sender: {sender}"
            )

            if not feedback_patterns:
                logger.info(f"No human feedback found for sender: {sender}")
                return 0.0

            # Analyze human corrections for this sender
            relevance_corrections = 0
            irrelevance_corrections = 0
            total_impact = 0.0

            for feedback in feedback_patterns:
                feedback_type = feedback.get("feedback_type", "")
                corrected_decision = feedback.get("corrected_decision", "").lower()
                original_decision = feedback.get("original_decision", "").lower()
                confidence_impact = feedback.get("confidence_impact", 0.0)

                logger.debug(
                    f"Human feedback: {original_decision} -> {corrected_decision}, impact: {confidence_impact}"
                )

                # Track corrections related to relevance
                if "relevance" in feedback_type.lower():
                    total_impact += abs(confidence_impact)

                    if (
                        corrected_decision == "relevant"
                        and original_decision == "irrelevant"
                    ):
                        relevance_corrections += 1
                    elif (
                        corrected_decision == "irrelevant"
                        and original_decision == "relevant"
                    ):
                        irrelevance_corrections += 1

            if relevance_corrections == 0 and irrelevance_corrections == 0:
                logger.info(
                    f"No relevance-related human feedback found for sender: {sender}"
                )
                return 0.0

            total_corrections = relevance_corrections + irrelevance_corrections
            avg_impact = (
                total_impact / total_corrections if total_corrections > 0 else 0.0
            )

            logger.info(
                f"Human feedback analysis: {relevance_corrections} relevance corrections, {irrelevance_corrections} irrelevance corrections, avg_impact: {avg_impact:.2f}"
            )

            # Calculate episodic adjustment based on human feedback patterns
            episodic_score = 0.0

            if (
                relevance_corrections > irrelevance_corrections
                and total_corrections >= 2
            ):
                # Humans have consistently corrected this sender to "relevant"
                episodic_score = min(
                    avg_impact * 0.4, 0.4
                )  # Up to 0.4 boost based on human feedback
                reasoning["decision_factors"].append(
                    f"Human feedback: sender {sender} corrected to relevant {relevance_corrections}/{total_corrections} times (score: +{episodic_score:.2f})"
                )
                logger.info(
                    f"Applied positive human feedback adjustment: +{episodic_score:.2f}"
                )

            elif (
                irrelevance_corrections > relevance_corrections
                and total_corrections >= 2
            ):
                # Humans have consistently corrected this sender to "irrelevant"
                episodic_score = -min(
                    avg_impact * 0.3, 0.3
                )  # Up to -0.3 penalty based on human feedback
                reasoning["decision_factors"].append(
                    f"Human feedback: sender {sender} corrected to irrelevant {irrelevance_corrections}/{total_corrections} times (score: {episodic_score:.2f})"
                )
                logger.info(
                    f"Applied negative human feedback adjustment: {episodic_score:.2f}"
                )

            else:
                logger.info(
                    "Human feedback pattern inconclusive or insufficient, no adjustment applied"
                )

            return episodic_score

        except Exception as e:
            logger.error(f"Failed to check human feedback patterns: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return 0.0

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

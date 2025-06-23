"""
Asset Matcher Node - Matches email attachments to specific investment assets.

This node queries procedural memory for HOW to perform matching (algorithms, weights)
and semantic memory for WHAT to match against (asset profiles, relationships).
"""

# # Standard library imports
# Standard library imports
from typing import Any

# # Local application imports
# Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AssetMatcherNode:
    """
    Matches relevant attachments to specific investment assets using memory-driven logic.

    Separates HOW (procedural memory) from WHAT (semantic memory).
    """

    def __init__(self, memory_systems=None) -> None:
        """
        Initialize asset matcher with memory system connections.

        Args:
            memory_systems: Dictionary with all memory systems (semantic, procedural, episodic)
        """
        if memory_systems:
            self.semantic_memory = memory_systems.get("semantic")
            self.procedural_memory = memory_systems.get("procedural")
            self.episodic_memory = memory_systems.get("episodic")
        else:
            # Initialize memory systems directly if not provided
            # # Local application imports
            from src.memory import create_memory_systems

            systems = create_memory_systems()
            self.semantic_memory = systems["semantic"]
            self.procedural_memory = systems["procedural"]
            self.episodic_memory = systems["episodic"]

        self.asset_match_threshold = config.requires_review_threshold

        logger.info(
            f"Asset matcher initialized (threshold: {self.asset_match_threshold})"
        )

    @log_function()
    async def match_attachments_to_assets(
        self, email_data: dict[str, Any], attachments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Match attachments to specific investment assets.

        Args:
            email_data: Email metadata (subject, sender, body)
            attachments: List of attachment metadata

        Returns:
            List of attachment matches with asset IDs and confidence scores

        Raises:
            ValueError: If input data is malformed
        """
        if not attachments:
            logger.info("No attachments to match")
            return []

        logger.info(f"Matching {len(attachments)} attachments to assets")

        # Get matching algorithms from procedural memory
        matching_rules = await self.query_matching_procedures(email_data)

        # Get asset data from semantic memory
        available_assets = await self.query_asset_profiles(email_data)

        # Get similar cases from episodic memory
        similar_cases = await self.query_similar_cases(email_data)

        matches = []
        for attachment in attachments:
            attachment_matches = await self._match_single_attachment(
                attachment, email_data, matching_rules, available_assets, similar_cases
            )
            matches.extend(attachment_matches)

        # Record processing in episodic memory
        await self._record_matching_session(email_data, attachments, matches)

        logger.info(f"Generated {len(matches)} asset matches")

        # Return in expected format with additional metadata
        return {
            "matches": matches,
            "decision_factors": [f"Processed {len(attachments)} attachments"],
            "memory_queries": [
                f"Queried {len(available_assets)} assets from semantic memory"
            ],
            "rule_applications": [f"Applied {len(matching_rules)} matching rules"],
            "confidence_factors": [f"Generated {len(matches)} matches"],
        }

    async def _match_single_attachment(
        self,
        attachment: dict[str, Any],
        email_data: dict[str, Any],
        matching_rules: list[dict[str, Any]],
        available_assets: list[dict[str, Any]],
        similar_cases: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Match a single attachment to assets using memory-driven logic.

        Args:
            attachment: Attachment metadata
            email_data: Email context
            matching_rules: Rules from procedural memory
            available_assets: Asset profiles from semantic memory
            similar_cases: Similar processing cases from episodic memory

        Returns:
            List of matches for this attachment
        """
        filename = attachment.get("filename", "")
        matches = []

        logger.info(f"Matching attachment: {filename}")

        # Calculate matches using memory-driven logic
        asset_scores = await self._calculate_asset_scores(
            attachment, email_data, matching_rules, available_assets, similar_cases
        )

        # Create match objects for high-confidence matches
        for asset_id, score_data in asset_scores.items():
            if score_data["confidence"] >= self.asset_match_threshold:
                matches.append(
                    {
                        "attachment_filename": filename,
                        "asset_id": asset_id,
                        "confidence": score_data["confidence"],
                        "reasoning": {
                            "match_factors": score_data["match_factors"],
                            "confidence_factors": score_data["confidence_factors"],
                            "rule_matches": score_data["rule_matches"],
                        },
                    }
                )

        logger.info(f"Found {len(matches)} matches for {filename}")
        return matches

    async def _calculate_asset_scores(
        self,
        attachment: dict[str, Any],
        email_data: dict[str, Any],
        matching_rules: list[dict[str, Any]],
        available_assets: list[dict[str, Any]],
        similar_cases: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate confidence scores for each asset using memory-driven rules.

        Args:
            attachment: Attachment metadata
            email_data: Email context
            matching_rules: Procedural memory rules
            available_assets: Semantic memory assets
            similar_cases: Episodic memory cases

        Returns:
            Dictionary mapping asset_id to score data
        """
        filename = attachment.get("filename", "").lower()
        subject = email_data.get("subject", "").lower()
        sender = email_data.get("sender", "").lower()

        asset_scores = {}

        for asset_data in available_assets:
            asset_id = asset_data["asset_id"]
            profile = asset_data["profile"]

            score_data = {
                "confidence": 0.0,
                "match_factors": [],
                "confidence_factors": [],
                "rule_matches": [],
            }

            # Apply each matching rule from procedural memory
            for rule in matching_rules:
                rule_score = self._apply_matching_rule(
                    rule, attachment, email_data, profile
                )

                if rule_score > 0:
                    weighted_score = rule_score * rule.get("weight", 0.5)
                    score_data["confidence"] += weighted_score
                    score_data["rule_matches"].append(
                        {
                            "rule_id": rule.get("rule_id", "unknown"),
                            "score": rule_score,
                            "weight": rule.get("weight", 0.5),
                            "weighted_score": weighted_score,
                        }
                    )
                    logger.debug(
                        f"Rule {rule.get('rule_id')} for {asset_id}: score={rule_score:.2f}, weighted={weighted_score:.2f}"
                    )
                else:
                    logger.debug(f"Rule {rule.get('rule_id')} for {asset_id}: no match")

            # Apply episodic memory learning
            episodic_adjustment = self._apply_episodic_learning(
                asset_id, sender, similar_cases
            )
            score_data["confidence"] += episodic_adjustment

            if episodic_adjustment != 0:
                score_data["confidence_factors"].append(
                    f"Episodic learning adjustment: {episodic_adjustment:+.2f}"
                )

            # Cap confidence at 1.0
            score_data["confidence"] = min(score_data["confidence"], 1.0)

            # Add detailed reasoning
            if score_data["confidence"] > 0:
                score_data["match_factors"].append(
                    f"Asset: {profile.get('name', asset_id)}"
                )
                if score_data["rule_matches"]:
                    score_data["confidence_factors"].append(
                        f"Rule matches: {len(score_data['rule_matches'])}"
                    )

            # Debug logging for final scores
            logger.debug(
                f"Final score for {asset_id} ({profile.get('name', 'unknown')}): {score_data['confidence']:.2f} (threshold: {self.asset_match_threshold})"
            )

            asset_scores[asset_id] = score_data

        return asset_scores

    def _apply_matching_rule(
        self,
        rule: dict[str, Any],
        attachment: dict[str, Any],
        email_data: dict[str, Any],
        asset_profile: dict[str, Any],
    ) -> float:
        """
        Apply a single matching rule from procedural memory.

        Args:
            rule: Matching rule from procedural memory
            attachment: Attachment metadata
            email_data: Email context
            asset_profile: Asset profile from semantic memory

        Returns:
            Rule match score (0.0 to 1.0)
        """
        rule_id = rule.get("rule_id", "")
        filename = attachment.get("filename", "").lower().replace("_", " ")
        subject = email_data.get("subject", "").lower()
        combined_text = f"{filename} {subject}"

        if rule_id == "exact_name_match":
            # Check for exact asset name matches or significant word overlap
            asset_name = asset_profile.get("name", "").lower()
            if asset_name:
                # Full name match gets maximum score
                if asset_name in combined_text:
                    return rule.get("confidence", 0.95)

                # Partial name match: check for significant word overlap
                asset_words = set(asset_name.split())
                text_words = set(combined_text.split())
                common_words = asset_words.intersection(text_words)

                # If we have 2+ significant words in common, give partial score
                if len(common_words) >= 2:
                    overlap_ratio = len(common_words) / len(asset_words)
                    return overlap_ratio * rule.get("confidence", 0.95)

        elif rule_id == "keyword_match":
            # Check for asset keyword matches
            keywords = asset_profile.get("keywords", [])
            if not keywords:
                return 0.0

            matches = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in combined_text:
                    matches += 1
                    matched_keywords.append(keyword)

            if matches > 0:
                # More generous scoring: boost score for multiple matches
                match_ratio = matches / len(keywords)
                base_score = match_ratio * rule.get("confidence", 0.8)

                # Bonus for multiple keyword matches
                if matches >= 2:
                    base_score = min(base_score * 1.3, 1.0)

                logger.debug(
                    f"Keyword matches for {asset_profile.get('name', 'unknown')}: {matched_keywords} ({matches}/{len(keywords)} = {match_ratio:.2f}, score: {base_score:.2f})"
                )
                return base_score

        return 0.0

    def _apply_episodic_learning(
        self,
        asset_id: str,
        sender: str,
        similar_cases: list[dict[str, Any]],
    ) -> float:
        """
        Apply learning from episodic memory to adjust confidence.

        Args:
            asset_id: Asset ID being matched
            sender: Email sender
            similar_cases: Similar cases from episodic memory

        Returns:
            Confidence adjustment (-0.3 to +0.3)
        """
        if not similar_cases:
            return 0.0

        # Look for cases with same sender and asset
        sender_asset_cases = [
            case
            for case in similar_cases
            if case.get("sender", "").lower() == sender.lower()
            and case.get("asset_id") == asset_id
        ]

        if sender_asset_cases:
            # Positive adjustment if this sender-asset combo worked before
            avg_confidence = sum(
                case.get("confidence", 0) for case in sender_asset_cases
            ) / len(sender_asset_cases)
            if avg_confidence > 0.7:
                return 0.2  # Boost confidence
            elif avg_confidence < 0.3:
                return -0.2  # Reduce confidence

        return 0.0

    async def query_matching_procedures(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query procedural memory for asset matching algorithms and rules.

        Args:
            context: Email and attachment context

        Returns:
            List of matching procedures and weights
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return self._get_default_matching_rules()

        try:
            matching_rules = self.procedural_memory.get_asset_matching_rules()
            logger.info(
                f"Retrieved {len(matching_rules)} matching rules from procedural memory"
            )
            return matching_rules
        except Exception as e:
            logger.error(f"Failed to query procedural memory: {e}")
            return self._get_default_matching_rules()

    async def query_asset_profiles(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query semantic memory for asset profiles and relationships.

        Args:
            context: Email context for filtering relevant assets

        Returns:
            List of asset profiles with keywords and patterns
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, using defaults")
            return []

        try:
            # Search for assets based on email content
            search_terms = self._extract_search_terms(context)
            all_results = []

            for term in search_terms[:3]:  # Limit to top 3 search terms
                results = self.semantic_memory.search_asset_profiles(term, limit=5)
                all_results.extend(results)

            # Remove duplicates by asset_id
            unique_assets = {}
            for result in all_results:
                asset_id = result["asset_id"]
                if (
                    asset_id not in unique_assets
                    or result["score"] > unique_assets[asset_id]["score"]
                ):
                    unique_assets[asset_id] = result

            asset_list = list(unique_assets.values())
            logger.info(
                f"Retrieved {len(asset_list)} asset profiles from semantic memory"
            )
            return asset_list

        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []

    async def query_similar_cases(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query episodic memory for similar processing cases.

        Args:
            context: Email context

        Returns:
            List of similar processing cases
        """
        if not self.episodic_memory:
            logger.info("Episodic memory not available")
            return []

        try:
            sender = context.get("sender", "")
            similar_cases = self.episodic_memory.search_similar_cases(
                sender=sender, limit=10
            )
            logger.info(
                f"Retrieved {len(similar_cases)} similar cases from episodic memory"
            )
            return similar_cases
        except Exception as e:
            logger.error(f"Failed to query episodic memory: {e}")
            return []

    def _extract_search_terms(self, context: dict[str, Any]) -> list[str]:
        """
        Extract search terms from email context.

        Args:
            context: Email context

        Returns:
            List of search terms
        """
        terms = []

        # Extract from subject
        subject = context.get("subject", "")
        if subject:
            # Simple keyword extraction
            words = subject.lower().split()
            important_words = [w for w in words if len(w) > 3 and w.isalpha()]
            terms.extend(important_words[:5])

        # Extract from sender domain
        sender = context.get("sender", "")
        if "@" in sender:
            domain = sender.split("@")[1]
            terms.append(domain)

        return terms

    async def _record_matching_session(
        self,
        email_data: dict[str, Any],
        attachments: list[dict[str, Any]],
        matches: list[dict[str, Any]],
    ):
        """
        Record the matching session in episodic memory.

        Args:
            email_data: Email context
            attachments: Processed attachments
            matches: Generated matches
        """
        if not self.episodic_memory:
            return

        try:
            email_id = email_data.get("id", "unknown")
            sender = email_data.get("sender", "")
            subject = email_data.get("subject", "")

            for match in matches:
                self.episodic_memory.add_processing_record(
                    email_id=email_id,
                    sender=sender,
                    subject=subject,
                    asset_id=match["asset_id"],
                    category="asset_match",
                    confidence=match["confidence"],
                    decision="matched",
                    metadata={
                        "filename": match["attachment_filename"],
                        "reasoning": match["reasoning"],
                        "attachment_count": len(attachments),
                    },
                )

            logger.info(f"Recorded {len(matches)} matches in episodic memory")
        except Exception as e:
            logger.error(f"Failed to record in episodic memory: {e}")

    def _get_default_matching_rules(self) -> list[dict[str, Any]]:
        """Default matching rules when procedural memory is unavailable."""
        return [
            {
                "rule_id": "exact_name_match",
                "description": "Exact asset name in filename or subject",
                "weight": 0.9,
                "confidence": 0.95,
            },
            {
                "rule_id": "keyword_match",
                "description": "Asset keywords in content",
                "weight": 0.7,
                "confidence": 0.8,
            },
        ]

"""
Asset Matcher Node - Matches email attachments to specific investment assets.

This node queries procedural memory for HOW to perform matching (algorithms, weights)
and semantic memory for WHAT to match against (asset profiles, relationships).
"""

# # Standard library imports
import re
from datetime import datetime
from difflib import SequenceMatcher

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

        # Get threshold from procedural memory (memory-driven architecture)
        try:
            if self.procedural_memory:
                thresholds = self.procedural_memory.data.get("thresholds", {})
                self.asset_match_threshold = thresholds.get(
                    "asset_match_threshold", config.requires_review_threshold
                )
            else:
                self.asset_match_threshold = config.requires_review_threshold
        except Exception:
            self.asset_match_threshold = config.requires_review_threshold

        logger.info(
            f"Asset matcher initialized (threshold: {self.asset_match_threshold})"
        )

    @log_function()
    async def match_attachments_to_assets(
        self, email_data: dict[str, Any], attachments: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Match attachments to specific investment assets.

        Args:
            email_data: Email metadata (subject, sender, body)
            attachments: List of attachment metadata

        Returns:
            Dictionary containing matches and processing metadata

        Raises:
            ValueError: If input data is malformed
        """
        # DEBUG: Log the complete email context
        logger.info("🔍 === ASSET MATCHING DEBUG START ===")
        logger.info("🔍 EMAIL CONTEXT:")
        logger.info(f"🔍   Sender: {email_data.get('sender', 'N/A')}")
        logger.info(f"🔍   Subject: {email_data.get('subject', 'N/A')}")
        logger.info(f"🔍   Body: {email_data.get('body', 'N/A')[:200]}...")
        logger.info(f"🔍   Attachment Count: {len(attachments)}")

        for i, att in enumerate(attachments):
            logger.info(f"🔍   Attachment {i+1}: {att.get('filename', 'N/A')}")

        if not attachments:
            logger.info("No attachments to match")
            return {
                "matches": [],
                "decision_factors": ["No attachments to match"],
                "memory_queries": [],
                "rule_applications": [],
                "confidence_factors": [],
            }

        logger.info(f"Matching {len(attachments)} attachments to assets")

        # Get matching algorithms from procedural memory
        matching_rules = await self.query_matching_procedures(email_data)
        logger.info(
            f"🔍 Retrieved {len(matching_rules)} matching rules from procedural memory"
        )

        # Get asset data from semantic memory - include attachments in context
        context_with_attachments = {**email_data, "attachments": attachments}
        available_assets = await self.query_asset_profiles(context_with_attachments)
        logger.info(
            f"🔍 Retrieved {len(available_assets)} asset profiles from semantic memory"
        )

        # Get similar cases from episodic memory
        similar_cases = await self.query_similar_cases(email_data)
        logger.info(
            f"🔍 Retrieved {len(similar_cases)} similar cases from episodic memory"
        )

        matches = []
        for i, attachment in enumerate(attachments):
            logger.info(
                f"🔍 === PROCESSING ATTACHMENT {i+1}/{len(attachments)}: {attachment.get('filename', 'N/A')} ==="
            )
            attachment_matches = await self._match_single_attachment(
                attachment, email_data, matching_rules, available_assets, similar_cases
            )
            matches.extend(attachment_matches)
            logger.info(
                f"🔍 Attachment {i+1} generated {len(attachment_matches)} matches"
            )

        # Record matching session in episodic memory for learning
        await self._record_matching_session(email_data, attachments, matches)

        logger.info("🔍 === FINAL RESULTS ===")
        logger.info(f"🔍 Total matches generated: {len(matches)}")
        for match in matches:
            logger.info(
                f"🔍   {match['attachment_filename']} -> {match['asset_id']} (confidence: {match['confidence']:.3f})"
            )
        logger.info("🔍 === ASSET MATCHING DEBUG END ===")

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

        logger.info(f"🔍 SINGLE ATTACHMENT MATCHING: {filename}")
        logger.info(f"🔍   Email Sender: {email_data.get('sender', 'N/A')}")
        logger.info(f"🔍   Email Subject: {email_data.get('subject', 'N/A')}")
        logger.info(f"🔍   Email Body Preview: {email_data.get('body', 'N/A')[:100]}...")

        # Calculate matches using memory-driven logic
        asset_scores = await self._calculate_asset_scores(
            attachment, email_data, matching_rules, available_assets, similar_cases
        )

        logger.info(f"🔍 ASSET SCORES FOR {filename}:")
        for asset_id, score_data in asset_scores.items():
            logger.info(f"🔍   {asset_id}: {score_data['confidence']:.3f}")

        # ATTACHMENT-CENTRIC: Only return the BEST match for each attachment
        best_match = None
        best_score = 0.0

        for asset_id, score_data in asset_scores.items():
            if (
                score_data["confidence"] >= self.asset_match_threshold
                and score_data["confidence"] > best_score
            ):
                best_score = score_data["confidence"]
                best_match = {
                    "attachment_filename": filename,
                    "asset_id": asset_id,
                    "confidence": score_data["confidence"],
                    "reasoning": {
                        "match_factors": score_data["match_factors"],
                        "confidence_factors": score_data["confidence_factors"],
                        "rule_matches": score_data["rule_matches"],
                    },
                }

        if best_match:
            logger.info(
                f"🔍 BEST MATCH for {filename}: {best_match['asset_id']} (confidence: {best_match['confidence']:.3f})"
            )
            return [best_match]  # Return list with single best match
        else:
            logger.info(
                f"🔍 NO MATCHES above threshold ({self.asset_match_threshold}) for {filename}"
            )
            # If no confident matches, route to HUMAN_REVIEW_QUEUE with detailed reasoning
            logger.info("🔍 No confident matches found - routing to HUMAN_REVIEW_QUEUE")

            # Capture detailed reasoning about what was tried and why it failed
            fallback_reasoning = []

            # Include information about all assets that were considered
            for asset_id, scores in asset_scores.items():
                if asset_id == "HUMAN_REVIEW_QUEUE":
                    continue

                confidence = scores.get("confidence", 0.0)
                reasoning_details = scores.get("decision_reasoning", [])

                fallback_reasoning.append(
                    {
                        "rule_id": "asset_consideration",
                        "rule_name": f"Asset Consideration: {asset_id}",
                        "rule_type": "asset_matching",
                        "asset_id": asset_id,
                        "confidence": confidence,
                        "score": confidence,  # Add score field for frontend compatibility
                        "threshold": self.asset_match_threshold,
                        "result": "rejected",
                        "reason": f"Confidence {confidence:.3f} below threshold {self.asset_match_threshold}",
                        "evidence_examined": reasoning_details,
                        "memory_source": f"semantic_memory.asset_profiles.{asset_id}",
                        "memory_items": [
                            {
                                "type": "semantic_memory",
                                "source": f"asset_profiles.{asset_id}",
                                "description": f"Asset profile data for {asset_id}",
                                "content": {"confidence_achieved": confidence},
                            }
                        ],
                        "evidence": {
                            "confidence_achieved": confidence,
                            "threshold_required": self.asset_match_threshold,
                            "confidence_gap": self.asset_match_threshold - confidence,
                        },
                        "contributing_factors": [
                            f"Asset {asset_id} achieved confidence of {confidence:.3f}",
                            f"Required threshold is {self.asset_match_threshold}",
                            f"Confidence gap: {self.asset_match_threshold - confidence:.3f}",
                        ],
                    }
                )

            # Add general fallback reasoning
            highest_conf = max(
                [
                    scores.get("confidence", 0.0)
                    for asset_id, scores in asset_scores.items()
                    if asset_id != "HUMAN_REVIEW_QUEUE"
                ],
                default=0.0,
            )
            fallback_reasoning.append(
                {
                    "rule_id": "human_review_fallback",
                    "rule_name": "Human Review Fallback",
                    "rule_type": "fallback_routing",
                    "result": "triggered",
                    "score": 0.1,  # Add score field for frontend compatibility
                    "reason": f"No asset achieved confidence ≥ {self.asset_match_threshold} - automatic human review required",
                    "total_assets_considered": len(
                        [a for a in asset_scores if a != "HUMAN_REVIEW_QUEUE"]
                    ),
                    "highest_confidence": highest_conf,
                    "memory_source": "procedural_memory.matching_rules.fallback_policy",
                    "memory_items": [
                        {
                            "type": "procedural_memory",
                            "source": "matching_rules.fallback_policy",
                            "description": "Automatic fallback when no asset matches meet the confidence threshold",
                            "content": {
                                "threshold": self.asset_match_threshold,
                                "action": "route_to_human_review",
                            },
                        }
                    ],
                    "evidence": {
                        "threshold": self.asset_match_threshold,
                        "highest_confidence_found": highest_conf,
                        "confidence_gap": self.asset_match_threshold - highest_conf,
                    },
                    "contributing_factors": [
                        f"No asset exceeded confidence threshold of {self.asset_match_threshold}",
                        f"Highest confidence found was {highest_conf:.3f}",
                        "Automatic routing to human review queue",
                    ],
                }
            )

            # Create a single match for this attachment to route to HUMAN_REVIEW_QUEUE
            return [
                {
                    "attachment_filename": attachment.get("filename"),
                    "attachment_path": attachment.get("path"),
                    "attachment_size": attachment.get("size"),
                    "attachment_type": attachment.get("content_type"),
                    "asset_id": "HUMAN_REVIEW_QUEUE",
                    "confidence": 0.1,  # Low confidence indicates fallback
                    "reasoning": "Automatic fallback - no confident asset match found",
                    "decision_reasoning": fallback_reasoning,  # Include detailed reasoning
                    "match_factors": ["human_review_fallback"],
                    "confidence_factors": [
                        f"No asset exceeded threshold {self.asset_match_threshold}"
                    ],
                    "rule_matches": ["human_review_fallback"],
                }
            ]

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
        sender = email_data.get("sender", "").lower()
        filename = attachment.get("filename", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        logger.info(f"🔍 === CALCULATING SCORES FOR {filename} ===")
        logger.info("🔍 INPUT DATA:")
        logger.info(f"🔍   Sender: '{sender}'")
        logger.info(f"🔍   Subject: '{subject}'")
        logger.info(f"🔍   Body: '{body[:150]}...'")
        logger.info(f"🔍   Filename: '{filename}'")
        logger.info(f"🔍   Available Assets: {len(available_assets)}")
        logger.info(f"🔍   Matching Rules: {len(matching_rules)}")

        asset_scores = {}

        for asset_data in available_assets:
            asset_id = asset_data["asset_id"]
            profile = asset_data["profile"]
            asset_name = profile.get("name", "unknown")

            logger.info(f"🔍 --- SCORING ASSET: {asset_id} ({asset_name}) ---")

            score_data = {
                "confidence": 0.0,
                "match_factors": [],
                "confidence_factors": [],
                "rule_matches": [],
                "decision_reasoning": [],  # Initialize reasoning storage
            }

            # Apply each matching rule from procedural memory
            for rule in matching_rules:
                rule_id = rule.get("rule_id", "unknown")
                logger.info(f"🔍   Applying rule: {rule_id}")

                rule_score, reasoning = self._apply_matching_rule(
                    rule, attachment, email_data, profile, asset_id
                )

                # Store detailed reasoning for this rule
                score_data["decision_reasoning"].append(reasoning)

                if rule_score > 0:
                    weight = rule.get("weight", 1.0)
                    weighted_score = rule_score * weight
                    score_data["confidence"] += weighted_score
                    score_data["rule_matches"].append(
                        {
                            "rule_id": rule_id,
                            "score": rule_score,
                            "weight": weight,
                            "weighted_score": weighted_score,
                        }
                    )
                    logger.info(
                        f"🔍     ✓ {rule_id}: raw_score={rule_score:.3f}, weight={weight:.2f}, weighted={weighted_score:.3f}"
                    )
                else:
                    logger.info(f"🔍     ✗ {rule_id}: score=0.000")

            # Apply episodic learning adjustments
            episodic_adjustment = self._apply_episodic_learning(
                asset_id, email_data.get("sender", ""), similar_cases
            )
            if episodic_adjustment != 0:
                logger.info(f"🔍   📚 Episodic adjustment: {episodic_adjustment:+.3f}")
                score_data["confidence"] += episodic_adjustment
                score_data["confidence_factors"].append(
                    f"Adjustment based on {len(similar_cases)} similar cases: {episodic_adjustment:+.3f}"
                )

                # Add episodic reasoning to decision breakdown
                score_data["decision_reasoning"].append(
                    {
                        "rule_id": "episodic_learning",
                        "rule_name": "Learning from Similar Cases",
                        "score": episodic_adjustment,
                        "memory_items": [
                            {
                                "type": "episodic_memory",
                                "source": "similar_cases",
                                "content": [
                                    {
                                        "sender": case.get("sender", ""),
                                        "asset_id": case.get("asset_id", ""),
                                        "confidence": case.get("confidence", 0),
                                    }
                                    for case in similar_cases[:3]
                                ],  # Truncate for readability
                                "description": f"Similar cases for sender and asset combination ({len(similar_cases)} total)",
                            }
                        ],
                        "evidence": {
                            "similar_cases_count": len(similar_cases),
                            "adjustment": episodic_adjustment,
                        },
                        "contributing_factors": [
                            f"Adjustment based on {len(similar_cases)} similar cases: {episodic_adjustment:+.3f}"
                        ],
                    }
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

            # Store comprehensive scoring details
            score_data.update(
                {
                    "asset_id": asset_id,
                    "asset_name": profile.get("name", asset_id),
                    "final_score": score_data["confidence"],
                    "base_average": score_data["confidence"],
                    "episodic_adjustment": episodic_adjustment,
                    "rules_applied": len(score_data["rule_matches"]),
                    "cumulative_score": score_data["confidence"],
                    "profile": profile,  # Include full profile for reference
                }
            )

            # Debug logging for final scores
            logger.info(
                f"🔍   FINAL SCORE for {asset_id}: {score_data['confidence']:.3f} (threshold: {self.asset_match_threshold})"
            )

            asset_scores[asset_id] = score_data

        return asset_scores

    def _apply_matching_rule(
        self,
        rule: dict[str, Any],
        attachment: dict[str, Any],
        email_data: dict[str, Any],
        asset_profile: dict[str, Any],
        asset_id: str,
    ) -> tuple[float, dict[str, Any]]:
        """
        Apply a single matching rule and return score with detailed reasoning.

        Args:
            rule: Matching rule from procedural memory
            attachment: Attachment data
            email_data: Email context
            asset_profile: Asset profile from semantic memory
            asset_id: Asset identifier

        Returns:
            Tuple of (score, reasoning_details)
        """
        rule_id = rule.get("rule_id", "unknown")
        filename = attachment.get("filename", "")
        combined_text = self._get_combined_text(attachment, email_data)

        # Initialize reasoning details
        reasoning = {
            "rule_id": rule_id,
            "rule_name": rule.get("name", rule_id),
            "score": 0.0,
            "memory_items": [],
            "evidence": {},
            "contributing_factors": [],
        }

        logger.info(
            f"🔍     Applying rule: {rule_id} (weight: {rule.get('weight', 1.0)})"
        )

        if rule_id == "file_name_patterns":
            # Check filename patterns in asset profile
            patterns = asset_profile.get("filename_patterns", [])
            reasoning["memory_items"] = [
                {
                    "type": "semantic_memory",
                    "source": f"asset_profiles.{asset_id}.filename_patterns",
                    "content": patterns,
                    "description": f"Filename patterns for {asset_profile.get('name', asset_id)}",
                }
            ]

            if patterns:
                for pattern in patterns:
                    if pattern in filename:
                        score = rule.get("confidence", 0.8)
                        reasoning["score"] = score
                        reasoning["evidence"]["matched_pattern"] = pattern
                        reasoning["evidence"]["filename"] = filename
                        reasoning["contributing_factors"].append(
                            f"Filename '{filename}' matches pattern '{pattern}'"
                        )
                        logger.info(
                            f"🔍       ✓ Pattern match: '{pattern}' found in filename '{filename}', score={score:.3f}"
                        )
                        return score, reasoning

                reasoning["contributing_factors"].append(
                    f"No patterns matched filename '{filename}'"
                )
                logger.info(f"🔍       ✗ No patterns matched filename: {filename}")
            else:
                reasoning["contributing_factors"].append(
                    "No filename patterns defined in asset profile"
                )
                logger.info(
                    f"🔍       ✗ No filename patterns defined for {asset_profile.get('name', 'unknown')}"
                )

        elif rule_id == "asset_name_in_content":
            # Check if asset name appears in content
            asset_name = asset_profile.get("name", "")
            reasoning["memory_items"] = [
                {
                    "type": "semantic_memory",
                    "source": f"asset_profiles.{asset_id}.name",
                    "content": asset_name,
                    "description": f"Official name of asset {asset_id}",
                }
            ]
            reasoning["evidence"]["asset_name"] = asset_name
            reasoning["evidence"]["combined_text_preview"] = (
                combined_text[:200] + "..."
                if len(combined_text) > 200
                else combined_text
            )

            if asset_name:
                # Full name match gets maximum score
                if asset_name in combined_text:
                    score = rule.get("confidence", 0.95)
                    reasoning["score"] = score
                    reasoning["contributing_factors"].append(
                        f"Full asset name '{asset_name}' found in content"
                    )
                    logger.info(f"🔍       ✓ Full name match found! Score: {score:.3f}")
                    return score, reasoning

                # Partial name match: check for significant word overlap
                asset_words = set(asset_name.split())
                text_words = set(combined_text.split())
                common_words = asset_words.intersection(text_words)

                reasoning["evidence"]["asset_words"] = list(asset_words)
                reasoning["evidence"]["common_words"] = list(common_words)

                logger.info(f"🔍       Asset words: {sorted(asset_words)}")
                logger.info(
                    f"🔍       Text words: {sorted(list(text_words)[:10])}... (showing first 10)"
                )
                logger.info(f"🔍       Common words: {sorted(common_words)}")

                # If we have 2+ significant words in common, give partial score
                if len(common_words) >= 2:
                    overlap_ratio = len(common_words) / len(asset_words)
                    score = overlap_ratio * rule.get("confidence", 0.95)
                    reasoning["score"] = score
                    reasoning["contributing_factors"].append(
                        f"Partial name match: {len(common_words)}/{len(asset_words)} words overlap (ratio: {overlap_ratio:.1%})"
                    )
                    logger.info(
                        f"🔍       ✓ Partial name match: {len(common_words)}/{len(asset_words)} words, ratio={overlap_ratio:.3f}, score={score:.3f}"
                    )
                    return score, reasoning
                else:
                    reasoning["contributing_factors"].append(
                        f"Insufficient word overlap: {len(common_words)}/{len(asset_words)} words"
                    )
                    logger.info(
                        f"🔍       ✗ Insufficient word overlap: {len(common_words)}/{len(asset_words)}"
                    )

        elif rule_id == "sender_asset_association":
            # Check if sender is known to be associated with this asset using semantic memory
            sender = email_data.get("sender", "").lower()
            reasoning["evidence"]["sender"] = sender

            logger.info(f"🔍       Checking sender association for: '{sender}'")

            # Query semantic memory for sender mappings
            try:
                sender_mapping = self.semantic_memory.get_sender_mapping(sender)
                reasoning["memory_items"] = [
                    {
                        "type": "semantic_memory",
                        "source": f"sender_mappings.{sender}",
                        "content": sender_mapping,
                        "description": f"Sender mapping configuration for {sender}",
                    }
                ]
                reasoning["evidence"]["sender_mapping"] = sender_mapping

                logger.info(f"🔍       Sender mapping result: {sender_mapping}")

                if sender_mapping and asset_id in sender_mapping.get("asset_ids", []):
                    # Sender is associated with this asset
                    score = rule.get("confidence", 0.3)
                    reasoning["score"] = score
                    reasoning["contributing_factors"].append(
                        f"Sender '{sender}' is mapped to asset '{asset_profile.get('name', '')} (asset_id: {asset_id}), score={score:.3f}"
                    )
                    logger.info(
                        f"🔍       ✓ Sender association found: {sender} -> {asset_profile.get('name', '')} (asset_id: {asset_id}), score={score:.3f}"
                    )
                    return score, reasoning
                else:
                    reasoning["contributing_factors"].append(
                        f"Sender '{sender}' not mapped to asset '{asset_id}'"
                    )
                    logger.info(
                        f"🔍       ✗ No sender association: {sender} -> {asset_id}"
                    )
            except Exception as e:
                logger.warning(f"🔍       Could not query sender mappings: {e}")
                reasoning["contributing_factors"].append(
                    f"Error querying sender mappings: {e}"
                )

                # Fallback to old hardcoded logic
                logger.info("🔍       Using fallback hardcoded sender logic")
                reasoning["memory_items"].append(
                    {
                        "type": "procedural_memory",
                        "source": "hardcoded_fallback_logic",
                        "content": "rick@bunker.us -> i3 assets",
                        "description": "Hardcoded fallback sender association rules",
                    }
                )

                if sender == "rick@bunker.us" and asset_profile.get(
                    "name", ""
                ).lower().startswith("i3"):
                    if "i3" in filename:
                        score = rule.get("confidence", 0.9)
                        reasoning["score"] = score
                        reasoning["contributing_factors"].append(
                            f"Hardcoded rule: {sender} + 'i3' in filename matches i3 assets"
                        )
                        logger.info(
                            f"🔍       ✓ Fallback sender + content match: {sender} -> {asset_profile.get('name', '')} (filename: {attachment.get('filename', '')}), score={score:.3f}"
                        )
                        return score, reasoning
                    else:
                        reasoning["score"] = 0.1
                        reasoning["contributing_factors"].append(
                            f"Partial fallback match: {sender} matches but no 'i3' in filename"
                        )
                        logger.info(
                            "🔍       ◐ Partial fallback match (sender ok, no i3 in filename): score=0.1"
                        )
                        return 0.1, reasoning

            return 0.0, reasoning

        elif rule_id == "keyword_match":
            # Check for asset keyword matches with both exact and fuzzy matching
            keywords = asset_profile.get("keywords", [])
            reasoning["memory_items"] = [
                {
                    "type": "semantic_memory",
                    "source": f"asset_profiles.{asset_id}.keywords",
                    "content": keywords,
                    "description": f"Keywords for asset {asset_profile.get('name', asset_id)}",
                }
            ]
            reasoning["evidence"]["keywords"] = keywords
            reasoning["evidence"]["combined_text_preview"] = (
                combined_text[:300] + "..."
                if len(combined_text) > 300
                else combined_text
            )

            logger.info(f"🔍       Asset keywords: {keywords}")

            if not keywords:
                reasoning["contributing_factors"].append(
                    "No keywords defined in asset profile"
                )
                logger.info(
                    f"🔍       ✗ No keywords found for {asset_profile.get('name', 'unknown')}"
                )
                return 0.0, reasoning

            exact_matches = 0
            fuzzy_matches = 0
            matched_keywords = []
            fuzzy_matched_keywords = []
            total_exact_score = 0.0
            total_fuzzy_score = 0.0
            keyword_details = []

            for keyword in keywords:
                keyword_detail = {
                    "keyword": keyword,
                    "match_type": "none",
                    "score": 0.0,
                    "matched_text": "",
                }

                # Try exact match first (fastest and most reliable)
                if keyword.lower() in combined_text:
                    exact_matches += 1
                    matched_keywords.append(keyword)
                    # Give full credit for exact match
                    total_exact_score += 1.0
                    keyword_detail.update(
                        {"match_type": "exact", "score": 1.0, "matched_text": keyword}
                    )
                    logger.info(
                        f"🔍       ✓ Keyword '{keyword}' found EXACTLY in combined text"
                    )
                else:
                    # Try fuzzy matching for typos, abbreviations, case variations
                    fuzzy_result = fuzzy_keyword_match(
                        keyword,
                        combined_text,
                        exact_threshold=0.9,
                        partial_threshold=0.7,
                    )

                    if fuzzy_result["score"] > 0:
                        fuzzy_matches += 1
                        fuzzy_matched_keywords.append(
                            f"{keyword}~{fuzzy_result['matched_text']}"
                        )
                        # Use the actual fuzzy score (0.7-1.0)
                        total_fuzzy_score += fuzzy_result["score"]
                        keyword_detail.update(
                            {
                                "match_type": "fuzzy",
                                "score": fuzzy_result["score"],
                                "matched_text": fuzzy_result["matched_text"],
                            }
                        )
                        logger.info(
                            f"🔍       ✓ Keyword '{keyword}' found via FUZZY match: '{fuzzy_result['matched_text']}' "
                            f"(similarity: {fuzzy_result['score']:.3f}, type: {fuzzy_result['match_type']})"
                        )
                    else:
                        logger.info(
                            f"🔍       ✗ Keyword '{keyword}' NOT found (exact or fuzzy)"
                        )

                keyword_details.append(keyword_detail)

            reasoning["evidence"]["keyword_analysis"] = keyword_details
            reasoning["evidence"]["exact_matches"] = matched_keywords
            reasoning["evidence"]["fuzzy_matches"] = fuzzy_matched_keywords

            # Calculate composite score with improved algorithm
            if exact_matches > 0 or fuzzy_matches > 0:
                # New scoring algorithm: reward strong matches more generously
                # Instead of requiring all keywords, focus on the strength of matches found

                # Calculate average match strength
                total_matches = exact_matches + fuzzy_matches
                if total_matches > 0:
                    # Average exact score (1.0 for exact matches)
                    avg_exact_score = (
                        total_exact_score / max(exact_matches, 1)
                        if exact_matches > 0
                        else 0.0
                    )
                    # Average fuzzy score (0.7-1.0 for fuzzy matches)
                    avg_fuzzy_score = (
                        total_fuzzy_score / max(fuzzy_matches, 1)
                        if fuzzy_matches > 0
                        else 0.0
                    )

                    # Combine exact and fuzzy scores with weighting
                    if exact_matches > 0 and fuzzy_matches > 0:
                        # Both types found: weighted average
                        combined_score = (
                            exact_matches * avg_exact_score
                            + fuzzy_matches * avg_fuzzy_score * 0.8
                        ) / total_matches
                    elif exact_matches > 0:
                        # Only exact matches: full credit
                        combined_score = avg_exact_score
                    else:
                        # Only fuzzy matches: discounted credit
                        combined_score = avg_fuzzy_score * 0.8

                    # Apply coverage bonus: having matches is more important than matching everything
                    coverage_ratio = total_matches / len(keywords)
                    if coverage_ratio >= 0.5:
                        # 50%+ coverage: full score
                        coverage_multiplier = 1.0
                    elif coverage_ratio >= 0.25:
                        # 25-50% coverage: modest penalty
                        coverage_multiplier = 0.9
                    else:
                        # <25% coverage: larger penalty but still viable
                        coverage_multiplier = 0.7

                    # Calculate final score
                    base_score = (
                        combined_score
                        * coverage_multiplier
                        * rule.get("confidence", 0.8)
                    )

                    # Bonus for multiple keyword matches (any type)
                    if total_matches >= 2:
                        base_score = min(base_score * 1.2, 1.0)

                    # Special bonus for single strong exact matches (common with proper names)
                    elif exact_matches == 1 and avg_exact_score >= 1.0:
                        base_score = min(base_score * 1.1, 1.0)

                    # Update reasoning with detailed scoring breakdown
                    reasoning["score"] = base_score
                    reasoning["evidence"]["scoring_details"] = {
                        "total_keywords": len(keywords),
                        "exact_matches": exact_matches,
                        "fuzzy_matches": fuzzy_matches,
                        "coverage_ratio": coverage_ratio,
                        "coverage_multiplier": coverage_multiplier,
                        "combined_score": combined_score,
                        "final_score": base_score,
                    }

                    # Build human-readable contributing factors
                    reasoning["contributing_factors"].extend(
                        [
                            (
                                f"Found {exact_matches} exact keyword matches: {matched_keywords}"
                                if exact_matches > 0
                                else None
                            ),
                            (
                                f"Found {fuzzy_matches} fuzzy keyword matches: {fuzzy_matched_keywords}"
                                if fuzzy_matches > 0
                                else None
                            ),
                            f"Keyword coverage: {total_matches}/{len(keywords)} ({coverage_ratio:.1%})",
                            f"Coverage multiplier: {coverage_multiplier:.2f}",
                            f"Final keyword score: {base_score:.3f}",
                        ]
                    )
                    reasoning["contributing_factors"] = [
                        f for f in reasoning["contributing_factors"] if f is not None
                    ]

                    logger.info("🔍       ✓ KEYWORD MATCHING SUMMARY:")
                    logger.info(
                        f"🔍         Exact matches: {matched_keywords} ({exact_matches}/{len(keywords)})"
                    )
                    logger.info(
                        f"🔍         Fuzzy matches: {fuzzy_matched_keywords} ({fuzzy_matches}/{len(keywords)})"
                    )
                    logger.info(
                        f"🔍         Combined score: {combined_score:.3f}, Coverage: {coverage_ratio:.1%}"
                    )
                    logger.info(
                        f"🔍         Coverage multiplier: {coverage_multiplier:.2f}, Final score: {base_score:.3f}"
                    )

                    return base_score, reasoning
                else:
                    reasoning["contributing_factors"].append(
                        "No valid keyword matches found"
                    )
                    logger.info("🔍       ✗ No valid matches found")
            else:
                reasoning["contributing_factors"].append(
                    "No keyword matches found (exact or fuzzy)"
                )
                logger.info("🔍       ✗ No keyword matches found (exact or fuzzy)")

        return 0.0, reasoning

    def _get_combined_text(
        self, attachment: dict[str, Any], email_data: dict[str, Any]
    ) -> str:
        """
        Combine attachment filename, email subject and body into searchable text.

        Args:
            attachment: Attachment metadata
            email_data: Email context

        Returns:
            Combined text for keyword matching
        """
        filename = attachment.get("filename", "").lower().replace("_", " ")
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()

        # Clean and combine text
        combined = f"{filename} {subject} {body}"

        # Log for debugging
        logger.info(f"🔍       Filename text: '{filename}'")
        logger.info(f"🔍       Subject text: '{subject}'")
        logger.info(f"🔍       Body text: '{body[:100]}...'")
        logger.info(f"🔍       Combined text: '{combined[:150]}...'")

        return combined

    def _apply_episodic_learning(
        self,
        asset_id: str,
        sender: str,
        similar_cases: list[dict[str, Any]],
    ) -> float:
        """
        Apply learning from human feedback to adjust confidence.

        This method ONLY uses human feedback to influence future decisions,
        NOT the system's own processing history, to avoid reinforcing mistakes.

        Args:
            asset_id: Asset ID being matched
            sender: Email sender
            similar_cases: Similar cases from processing history (NOT used for decision-making)

        Returns:
            Confidence adjustment based on human feedback (-0.3 to +0.3)
        """
        if not self.episodic_memory:
            return 0.0

        try:
            # Query ONLY human feedback patterns, NOT processing history
            feedback_patterns = self.episodic_memory.search_human_feedback_patterns(
                sender=sender, feedback_type="asset_match", limit=10
            )

            if not feedback_patterns:
                return 0.0

            # Look for human corrections involving this sender and asset combination
            relevant_feedback = []
            for feedback in feedback_patterns:
                feedback_asset_id = feedback.get("asset_id")
                if feedback_asset_id == asset_id:
                    relevant_feedback.append(feedback)

            if not relevant_feedback:
                return 0.0

            # Analyze human corrections for this sender-asset combination
            positive_corrections = 0  # Human corrected to match this asset
            negative_corrections = 0  # Human corrected away from this asset
            total_impact = 0.0

            for feedback in relevant_feedback:
                corrected_decision = feedback.get("corrected_decision", "").lower()
                original_decision = feedback.get("original_decision", "").lower()
                confidence_impact = feedback.get("confidence_impact", 0.0)

                total_impact += abs(confidence_impact)

                # If human corrected TO this asset match
                if "match" in corrected_decision and "no_match" in original_decision:
                    positive_corrections += 1
                # If human corrected AWAY from this asset match
                elif "no_match" in corrected_decision and "match" in original_decision:
                    negative_corrections += 1

            if positive_corrections == 0 and negative_corrections == 0:
                return 0.0

            total_corrections = positive_corrections + negative_corrections
            avg_impact = (
                total_impact / total_corrections if total_corrections > 0 else 0.0
            )

            # Apply confidence adjustment based on human feedback
            if positive_corrections > negative_corrections and total_corrections >= 2:
                # Humans have consistently corrected TO this asset match
                return min(avg_impact * 0.3, 0.3)  # Up to +0.3 boost
            elif negative_corrections > positive_corrections and total_corrections >= 2:
                # Humans have consistently corrected AWAY from this asset match
                return -min(avg_impact * 0.3, 0.3)  # Up to -0.3 penalty
            else:
                # Inconclusive or insufficient feedback
                return 0.0

        except Exception as e:
            logger.error(f"Failed to apply human feedback learning: {e}")
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
        Query semantic memory for asset profiles using search terms and fallback strategies.

        Uses multiple strategies to ensure relevant assets are found:
        1. Specific term matching (asset-specific keywords)
        2. Sender-based asset retrieval (trusted senders)
        3. Fuzzy term matching for partial matches

        Args:
            context: Email context for filtering relevant assets

        Returns:
            List of asset profiles with keywords and patterns
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, using defaults")
            return []

        try:
            # DEBUG: Check what's actually in semantic memory
            total_assets = len(self.semantic_memory.data.get("asset_profiles", {}))
            logger.info(f"🔍 DEBUG: Total assets in semantic memory: {total_assets}")
            asset_names = list(
                self.semantic_memory.data.get("asset_profiles", {}).keys()
            )
            logger.info(f"🔍 DEBUG: Asset IDs in memory: {asset_names}")

            # Extract search terms from email content
            search_terms = self._extract_search_terms(context)
            logger.info("🔍 === QUERYING ASSET PROFILES (MULTI-STRATEGY) ===")
            logger.info(f"🔍 All search terms extracted: {search_terms}")

            # Get all asset keywords from semantic memory
            all_asset_keywords = self._get_all_asset_keywords()
            logger.info(f"🔍 All asset keywords in memory: {sorted(all_asset_keywords)}")

            all_results = []

            # Strategy 1: Search for specific terms that exist in asset keywords
            specific_terms = [
                term for term in search_terms if term.lower() in all_asset_keywords
            ]
            logger.info(f"🔍 Strategy 1 - Specific asset terms found: {specific_terms}")

            for term in specific_terms:
                logger.info(f"🔍 Searching for specific asset term: '{term}'")
                results = self.semantic_memory.search_asset_profiles(term, limit=50)
                logger.info(
                    f"🔍   Found {len(results)} profiles for specific term '{term}'"
                )
                for result in results:
                    logger.info(
                        f"🔍     {result['asset_id']} ({result['profile'].get('name', 'N/A')}): score={result['score']:.3f}"
                    )
                all_results.extend(results)

            # Strategy 2: Sender-based asset retrieval for trusted senders
            sender = context.get("sender", "")
            if sender:
                logger.info(
                    f"🔍 Strategy 2 - Checking sender-based assets for: {sender}"
                )
                sender_mapping = self.semantic_memory.get_sender_mapping(sender)
                if sender_mapping and "asset_ids" in sender_mapping:
                    sender_assets = sender_mapping["asset_ids"]
                    logger.info(f"🔍   Sender has access to assets: {sender_assets}")

                    # Add all sender's assets as candidates with base relevance score
                    asset_profiles = self.semantic_memory.data.get("asset_profiles", {})
                    for asset_id in sender_assets:
                        if asset_id in asset_profiles and not any(
                            r["asset_id"] == asset_id for r in all_results
                        ):
                            # Only add if not already found in strategy 1
                            all_results.append(
                                {
                                    "asset_id": asset_id,
                                    "profile": asset_profiles[asset_id],
                                    "score": 0.3,  # Base relevance for sender assets
                                }
                            )
                            logger.info(
                                f"🔍     Added sender asset: {asset_id} (base score: 0.3)"
                            )

            # Strategy 3: Fuzzy term matching for asset keywords
            if len(all_results) < 3:  # Only if we don't have many results
                logger.info("🔍 Strategy 3 - Fuzzy matching for additional assets")
                asset_profiles = self.semantic_memory.data.get("asset_profiles", {})

                for asset_id, profile in asset_profiles.items():
                    # Skip if already found
                    if any(r["asset_id"] == asset_id for r in all_results):
                        continue

                    # Check for fuzzy matches between search terms and asset keywords
                    keywords = profile.get("keywords", [])
                    best_fuzzy_score = 0.0

                    for search_term in search_terms:
                        for keyword in keywords:
                            # Use fuzzy matching
                            fuzzy_result = fuzzy_keyword_match(
                                search_term,
                                keyword,
                                exact_threshold=0.8,
                                partial_threshold=0.6,
                            )
                            if fuzzy_result["score"] > best_fuzzy_score:
                                best_fuzzy_score = fuzzy_result["score"]

                    # Add assets with decent fuzzy matches
                    if best_fuzzy_score >= 0.6:
                        all_results.append(
                            {
                                "asset_id": asset_id,
                                "profile": profile,
                                "score": best_fuzzy_score
                                * 0.5,  # Discounted fuzzy score
                            }
                        )
                        logger.info(
                            f"🔍     Added fuzzy match: {asset_id} (fuzzy score: {best_fuzzy_score:.3f})"
                        )

            # DEBUG: Check if we have no search results at all
            if not all_results:
                logger.warning("🔍 WARNING: No asset profiles found with any strategy")
                logger.warning(f"🔍 Search terms: {search_terms}")
                logger.warning(f"🔍 Asset keywords: {sorted(all_asset_keywords)}")
                logger.warning(f"🔍 Sender: {sender}")

                # Last resort: return all assets if sender is trusted
                if sender_mapping and sender_mapping.get("trust_score", 0) >= 0.8:
                    logger.info(
                        "🔍 Last resort: returning all assets for trusted sender"
                    )
                    asset_profiles = self.semantic_memory.data.get("asset_profiles", {})
                    for asset_id, profile in asset_profiles.items():
                        all_results.append(
                            {
                                "asset_id": asset_id,
                                "profile": profile,
                                "score": 0.1,  # Very low base score
                            }
                        )

                if not all_results:
                    return []

            # Deduplicate and merge scores
            asset_map = {}
            for result in all_results:
                asset_id = result["asset_id"]
                if asset_id not in asset_map:
                    asset_map[asset_id] = result
                else:
                    # Combine scores (take maximum)
                    asset_map[asset_id]["score"] = max(
                        asset_map[asset_id]["score"], result["score"]
                    )

            final_results = list(asset_map.values())
            logger.info(f"🔍 FINAL ASSET PROFILES ({len(final_results)} unique):")
            for result in final_results:
                logger.info(
                    f"🔍   {result['asset_id']} ({result['profile'].get('name', 'N/A')}): final_score={result['score']:.3f}"
                )

            # Sort by score and return top matches
            final_results.sort(key=lambda x: x["score"], reverse=True)
            top_results = final_results[:20]  # Limit to top 20

            logger.info(
                f"🔍 === ASSET PROFILES QUERY COMPLETE ({len(top_results)} returned) ==="
            )
            return top_results

        except Exception as e:
            logger.error(f"Failed to query semantic memory: {e}")
            return []

    async def query_similar_cases(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query episodic memory for similar processing cases.

        WARNING: This method returns the system's own processing decisions,
        which should NOT be used to influence future automated decisions.
        This is only used for review and analysis purposes.

        Args:
            context: Email context

        Returns:
            List of similar processing cases from processing history (for review only)
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
                f"Retrieved {len(similar_cases)} similar cases from processing history (review only)"
            )
            return similar_cases
        except Exception as e:
            logger.error(f"Failed to query episodic memory: {e}")
            return []

    def _extract_search_terms(self, context: dict[str, Any]) -> list[str]:
        """
        Extract search terms from email context and attachments.

        Args:
            context: Dictionary with email data and attachments

        Returns:
            List of search terms for asset matching
        """
        search_terms = []

        # Get email content
        subject = context.get("subject", "")
        body = context.get("body", "")
        sender = context.get("sender", "")
        attachments = context.get("attachments", [])

        logger.info("🔍 === EXTRACTING SEARCH TERMS ===")
        logger.info("🔍 INPUT SOURCES:")
        logger.info(f"🔍   Subject: '{subject}'")
        logger.info(f"🔍   Body: '{body[:100]}...'")
        logger.info(f"🔍   Sender: '{sender}'")
        logger.info(
            f"🔍   Attachments: {[att.get('filename', 'N/A') for att in attachments]}"
        )

        # Extract from subject (split into words, filter meaningful ones)
        if subject:
            subject_words = [
                word.strip().lower()
                for word in subject.replace("_", " ").replace("-", " ").split()
                if len(word.strip()) > 1  # Skip single letters
            ]
            search_terms.extend(subject_words)
            logger.info(f"🔍   Subject terms: {subject_words}")

        # Extract from body (first 200 chars, split into words)
        if body:
            body_preview = body[:200].lower()
            body_words = [
                word.strip().lower()
                for word in body_preview.replace("_", " ").replace("-", " ").split()
                if len(word.strip()) > 2  # Skip short words for body
            ]
            # Limit body words to avoid noise
            search_terms.extend(body_words[:10])
            logger.info(f"🔍   Body terms: {body_words[:10]}")

        # Extract from attachment filenames
        for attachment in attachments:
            filename = attachment.get("filename", "")
            if filename:
                # Remove extension and split
                name_part = filename.lower().split(".")[0]
                filename_words = [
                    word.strip().lower()
                    for word in name_part.replace("_", " ").replace("-", " ").split()
                    if len(word.strip()) > 1
                ]
                search_terms.extend(filename_words)
                logger.info(f"🔍   Filename '{filename}' terms: {filename_words}")

        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in search_terms:
            if term not in seen and len(term) > 1:
                unique_terms.append(term)
                seen.add(term)

        logger.info(f"🔍 FINAL SEARCH TERMS: {unique_terms}")
        logger.info("🔍 === SEARCH TERMS EXTRACTION COMPLETE ===")

        return unique_terms

    def _get_all_asset_keywords(self) -> set[str]:
        """
        Extract all keywords from all assets in semantic memory.

        Returns:
            Set of unique keywords from all asset profiles
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available for keyword extraction")
            return set()

        try:
            # Get all asset profiles from semantic memory
            asset_data = self.semantic_memory.data.get("asset_profiles", {})
            all_keywords = set()

            for _, profile in asset_data.items():
                keywords = profile.get("keywords", [])
                # Add individual keywords, making them lowercase for matching
                for keyword in keywords:
                    if isinstance(keyword, str) and len(keyword.strip()) > 0:
                        # Split multi-word keywords and add individual words
                        words = keyword.lower().strip().split()
                        all_keywords.update(words)

            logger.info(
                f"Extracted {len(all_keywords)} unique keywords from {len(asset_data)} assets"
            )
            return all_keywords

        except Exception as e:
            logger.error(f"Failed to extract asset keywords from semantic memory: {e}")
            return set()

    async def _record_matching_session(
        self,
        email_data: dict[str, Any],
        attachments: list[dict[str, Any]],
        matches: list[dict[str, Any]],
    ):
        """
        Record this matching session in episodic memory for learning.

        Args:
            email_data: Email context
            attachments: List of attachments processed
            matches: List of asset matches with reasoning
        """
        if not self.episodic_memory:
            return

        try:
            email_id = email_data.get("id", f"match_{datetime.now().timestamp()}")
            sender = email_data.get("sender", "unknown")
            subject = email_data.get("subject", "")

            # Collect all decision reasoning from matches
            all_decision_reasoning = []
            attachment_filenames = []

            for match in matches:
                attachment_filename = match.get("attachment_filename", "")
                attachment_filenames.append(attachment_filename)

                # Get the decision reasoning if available
                if "decision_reasoning" in match:
                    all_decision_reasoning.extend(match["decision_reasoning"])

            # Create comprehensive metadata including decision reasoning
            metadata = {
                "attachments": attachment_filenames,
                "total_attachments": len(attachments),
                "total_matches": len(matches),
                "email_subject": subject,
                "sender": sender,
                "decision_reasoning": all_decision_reasoning,  # Include detailed reasoning
                "matching_summary": {
                    "successful_matches": len(
                        [
                            m
                            for m in matches
                            if m.get("confidence", 0) > self.asset_match_threshold
                        ]
                    ),
                    "low_confidence_matches": len(
                        [
                            m
                            for m in matches
                            if 0 < m.get("confidence", 0) <= self.asset_match_threshold
                        ]
                    ),
                    "no_matches": len(
                        [m for m in matches if m.get("confidence", 0) == 0]
                    ),
                },
            }

            # Record each match as a separate processing record for detailed tracking
            for match in matches:
                asset_id = match.get("asset_id", "UNMATCHED")
                confidence = match.get("confidence", 0.0)

                # Determine decision category
                if confidence > self.asset_match_threshold:
                    decision = "matched"
                    category = "asset_match"
                elif confidence > 0:
                    decision = "low_confidence"
                    category = "asset_match"
                else:
                    decision = "no_match"
                    category = "no_match"

                # Store individual match record with reasoning
                match_metadata = {
                    **metadata,
                    "specific_match": {
                        "attachment_filename": match.get("attachment_filename", ""),
                        "asset_id": asset_id,
                        "confidence": confidence,
                        "reasoning": match.get("decision_reasoning", []),
                        "match_factors": match.get("match_factors", []),
                        "confidence_factors": match.get("confidence_factors", []),
                    },
                }

                self.episodic_memory.add_processing_record(
                    email_id=f"{email_id}_{match.get('attachment_filename', '')}",
                    sender=sender,
                    subject=subject,
                    asset_id=asset_id,
                    category=category,
                    confidence=confidence,
                    decision=decision,
                    metadata=match_metadata,
                )

            logger.info(
                f"Recorded matching session: {len(matches)} matches for {len(attachments)} attachments"
            )

        except Exception as e:
            logger.error(f"Failed to record matching session: {e}")

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


def levenshtein_similarity(a: str, b: str) -> float:
    """
    Calculate Levenshtein similarity between two strings.

    Args:
        a: First string
        b: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not a or not b:
        return 0.0

    # Use SequenceMatcher for efficiency
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fuzzy_keyword_match(
    keyword: str,
    text: str,
    exact_threshold: float = 0.9,
    partial_threshold: float = 0.7,
) -> dict[str, float]:
    """
    Find the best fuzzy match for a keyword in text.

    Args:
        keyword: The keyword to search for
        text: The text to search in
        exact_threshold: Minimum similarity for "exact" match (higher weight)
        partial_threshold: Minimum similarity for partial match (lower weight)

    Returns:
        Dictionary with match info: {'score': float, 'match_type': str, 'matched_text': str}
    """
    if not keyword or not text:
        return {"score": 0.0, "match_type": "none", "matched_text": ""}

    keyword_lower = keyword.lower()
    text_lower = text.lower()

    # Check for exact substring match first (fastest)
    if keyword_lower in text_lower:
        return {"score": 1.0, "match_type": "exact_substring", "matched_text": keyword}

    # Split text into words for fuzzy matching
    words = re.findall(r"\b\w+\b", text_lower)

    best_score = 0.0
    best_match = ""
    match_type = "none"

    for word in words:
        similarity = levenshtein_similarity(keyword_lower, word)

        if similarity > best_score:
            best_score = similarity
            best_match = word

            if similarity >= exact_threshold:
                match_type = "exact_fuzzy"
            elif similarity >= partial_threshold:
                match_type = "partial_fuzzy"

    return {
        "score": best_score if best_score >= partial_threshold else 0.0,
        "match_type": match_type if best_score >= partial_threshold else "none",
        "matched_text": best_match if best_score >= partial_threshold else "",
    }

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

        # Get threshold from procedural memory (memory-driven architecture)
        try:
            if self.procedural_memory:
                thresholds = self.procedural_memory.data.get(
                    "confidence_thresholds", {}
                )
                self.asset_match_threshold = thresholds.get(
                    "requires_review_threshold", config.requires_review_threshold
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

        # DISABLED: Episodic memory should only be updated with human-approved data
        # await self._record_matching_session(email_data, attachments, matches)

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
            return []

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
            }

            # Apply each matching rule from procedural memory
            for rule in matching_rules:
                rule_id = rule.get("rule_id", "unknown")
                logger.info(f"🔍   Applying rule: {rule_id}")

                rule_score = self._apply_matching_rule(
                    rule, attachment, email_data, profile, asset_id
                )

                if rule_score > 0:
                    weighted_score = rule_score * rule.get("weight", 0.5)
                    score_data["confidence"] += weighted_score
                    score_data["rule_matches"].append(
                        {
                            "rule_id": rule_id,
                            "score": rule_score,
                            "weight": rule.get("weight", 0.5),
                            "weighted_score": weighted_score,
                        }
                    )
                    logger.info(
                        f"🔍     ✓ {rule_id}: raw_score={rule_score:.3f}, weight={rule.get('weight', 0.5):.3f}, weighted={weighted_score:.3f}"
                    )
                else:
                    logger.info(f"🔍     ✗ {rule_id}: no match (score=0)")

            # Apply episodic memory learning
            episodic_adjustment = self._apply_episodic_learning(
                asset_id, sender, similar_cases
            )
            if episodic_adjustment != 0:
                score_data["confidence"] += episodic_adjustment
                score_data["confidence_factors"].append(
                    f"Episodic learning adjustment: {episodic_adjustment:+.2f}"
                )
                logger.info(f"🔍   Episodic adjustment: {episodic_adjustment:+.3f}")

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
        body = email_data.get("body", "").lower()
        combined_text = f"{filename} {subject} {body}"

        logger.info(f"🔍     RULE {rule_id} DETAILS:")
        logger.info(f"🔍       Filename text: '{filename}'")
        logger.info(f"🔍       Subject text: '{subject}'")
        logger.info(f"🔍       Body text: '{body[:100]}...'")
        logger.info(f"🔍       Combined text: '{combined_text[:150]}...'")

        if rule_id == "exact_name_match":
            # Check for exact asset name matches or significant word overlap
            asset_name = asset_profile.get("name", "").lower()
            logger.info(f"🔍       Asset name: '{asset_name}'")

            if asset_name:
                # Full name match gets maximum score
                if asset_name in combined_text:
                    score = rule.get("confidence", 0.95)
                    logger.info(f"🔍       ✓ Full name match found! Score: {score:.3f}")
                    return score

                # Partial name match: check for significant word overlap
                asset_words = set(asset_name.split())
                text_words = set(combined_text.split())
                common_words = asset_words.intersection(text_words)

                logger.info(f"🔍       Asset words: {sorted(asset_words)}")
                logger.info(
                    f"🔍       Text words: {sorted(list(text_words)[:10])}... (showing first 10)"
                )
                logger.info(f"🔍       Common words: {sorted(common_words)}")

                # If we have 2+ significant words in common, give partial score
                if len(common_words) >= 2:
                    overlap_ratio = len(common_words) / len(asset_words)
                    score = overlap_ratio * rule.get("confidence", 0.95)
                    logger.info(
                        f"🔍       ✓ Partial name match: {len(common_words)}/{len(asset_words)} words, ratio={overlap_ratio:.3f}, score={score:.3f}"
                    )
                    return score
                else:
                    logger.info(
                        f"🔍       ✗ Insufficient word overlap: {len(common_words)}/{len(asset_words)}"
                    )

        elif rule_id == "sender_asset_association":
            # Check if sender is known to be associated with this asset using semantic memory
            sender = email_data.get("sender", "").lower()
            logger.info(f"🔍       Checking sender association for: '{sender}'")

            # Query semantic memory for sender mappings
            try:
                sender_mapping = self.semantic_memory.get_sender_mapping(sender)
                logger.info(f"🔍       Sender mapping result: {sender_mapping}")

                if sender_mapping and asset_id in sender_mapping.get("asset_ids", []):
                    # Sender is associated with this asset
                    score = rule.get("confidence", 0.3)
                    logger.info(
                        f"🔍       ✓ Sender association found: {sender} -> {asset_profile.get('name', '')} (asset_id: {asset_id}), score={score:.3f}"
                    )
                    return score
                else:
                    logger.info(
                        f"🔍       ✗ No sender association: {sender} -> {asset_id}"
                    )
            except Exception as e:
                logger.warning(f"🔍       Could not query sender mappings: {e}")
                # Fallback to old hardcoded logic
                logger.info("🔍       Using fallback hardcoded sender logic")
                if sender == "rick@bunker.us" and asset_profile.get(
                    "name", ""
                ).lower().startswith("i3"):
                    if "i3" in filename:
                        score = rule.get("confidence", 0.9)
                        logger.info(
                            f"🔍       ✓ Fallback sender + content match: {sender} -> {asset_profile.get('name', '')} (filename: {attachment.get('filename', '')}), score={score:.3f}"
                        )
                        return score
                    else:
                        logger.info(
                            "🔍       ◐ Partial fallback match (sender ok, no i3 in filename): score=0.1"
                        )
                        return 0.1
            return 0.0

        elif rule_id == "keyword_match":
            # Check for asset keyword matches
            keywords = asset_profile.get("keywords", [])
            logger.info(f"🔍       Asset keywords: {keywords}")

            if not keywords:
                logger.info(
                    f"🔍       ✗ No keywords found for {asset_profile.get('name', 'unknown')}"
                )
                return 0.0

            matches = 0
            matched_keywords = []

            for keyword in keywords:
                if keyword.lower() in combined_text:
                    matches += 1
                    matched_keywords.append(keyword)
                    logger.info(f"🔍       ✓ Keyword '{keyword}' found in combined text")
                else:
                    logger.info(
                        f"🔍       ✗ Keyword '{keyword}' NOT found in combined text"
                    )

            if matches > 0:
                # More generous scoring: boost score for multiple matches
                match_ratio = matches / len(keywords)
                base_score = match_ratio * rule.get("confidence", 0.8)

                # Bonus for multiple keyword matches
                if matches >= 2:
                    base_score = min(base_score * 1.3, 1.0)

                logger.info(
                    f"🔍       ✓ Keyword matches: {matched_keywords} ({matches}/{len(keywords)} = {match_ratio:.2f}), base_score: {base_score:.3f}"
                )
                return base_score
            else:
                logger.info("🔍       ✗ No keyword matches found")

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
            logger.info("🔍 === QUERYING ASSET PROFILES ===")
            logger.info(f"🔍 Search terms extracted: {search_terms}")
            all_results = []

            # Get all asset keywords from semantic memory to determine priority terms
            all_asset_keywords = self._get_all_asset_keywords()
            priority_terms = [
                term for term in search_terms if term in all_asset_keywords
            ]

            logger.info(f"🔍 All asset keywords in memory: {sorted(all_asset_keywords)}")
            logger.info(f"🔍 Priority asset terms found: {priority_terms}")

            # First, search for priority asset-specific terms (no limit)
            for term in priority_terms:
                logger.info(f"🔍 Searching for priority term: '{term}'")
                results = self.semantic_memory.search_asset_profiles(term, limit=50)
                logger.info(
                    f"🔍   Found {len(results)} profiles for priority term '{term}'"
                )
                for result in results:
                    logger.info(
                        f"🔍     {result['asset_id']} ({result['profile'].get('name', 'N/A')}): score={result['score']:.3f}"
                    )
                all_results.extend(results)

            # Then search for general terms (limited to avoid noise)
            general_terms = [
                term for term in search_terms if term not in priority_terms
            ]
            logger.info(f"🔍 General terms: {general_terms[:5]}... (showing first 5)")

            for term in general_terms[:5]:  # Limit general terms
                logger.info(f"🔍 Searching for general term: '{term}'")
                results = self.semantic_memory.search_asset_profiles(term, limit=10)
                logger.info(
                    f"🔍   Found {len(results)} profiles for general term '{term}'"
                )
                for result in results:
                    logger.info(
                        f"🔍     {result['asset_id']} ({result['profile'].get('name', 'N/A')}): score={result['score']:.3f}"
                    )
                all_results.extend(results)

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
        Record the matching session in episodic memory.

        IMPORTANT: This method is currently DISABLED because episodic memory
        should only contain human-validated experiences, not automatic matches.
        Episodic memory updates should happen through the feedback integrator
        when humans approve or correct matches.

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

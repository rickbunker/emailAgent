"""
Asset identification module.

This module provides clean, simple asset identification logic that:
1. First checks sender mappings (high confidence)
2. Then applies pattern matching with proper thresholds
3. Returns None instead of forcing false positives

The architecture separates concerns properly - this module orchestrates
the identification process but delegates actual matching to specialized services.
"""

# # Standard library imports
import re
from typing import Optional

# # Local application imports
from src.asset_management.core.data_models import (
    Asset,
    AssetMatch,
    IdentificationContext,
)
from src.asset_management.core.exceptions import IdentificationError
from src.asset_management.memory_integration.sender_mappings import SenderMappingService
from src.memory.semantic import SemanticMemory, KnowledgeType
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AssetIdentifier:
    """
    Main asset identification service.

    Implements a clean identification pipeline that:
    1. Checks sender mappings first (existing system)
    2. Applies simple pattern matching if no sender match
    3. Enforces confidence thresholds to prevent false positives
    4. Returns None when no confident match is found
    """

    def __init__(
        self,
        sender_mapping_service: Optional[SenderMappingService] = None,
        confidence_threshold: Optional[float] = None,
    ):
        """
        Initialize the asset identifier.

        Args:
            sender_mapping_service: Service for checking sender mappings.
                                  If not provided, creates a new one.
            confidence_threshold: Minimum confidence required for a match.
                                Defaults to config.asset_match_confidence_threshold
        """
        self.sender_mappings = sender_mapping_service or SenderMappingService()
        self.semantic_memory = SemanticMemory()
        self._thresholds_cache = {}
        self.confidence_threshold = confidence_threshold or getattr(
            config, "asset_match_confidence_threshold", 0.7
        )
        logger.info(
            f"Asset identifier initialized with threshold: {self.confidence_threshold}"
        )

    @log_function()
    async def _get_confidence_thresholds(self) -> dict[str, float]:
        """
        Get confidence thresholds from business rules in memory.

        Returns:
            Dictionary of confidence thresholds for asset identification
        """
        if self._thresholds_cache:
            return self._thresholds_cache

        try:
            # Search for asset identification thresholds
            threshold_rules = await self.semantic_memory.search(
                query="Confidence thresholds for asset_identification",
                limit=10,
                knowledge_type=KnowledgeType.RULE,
            )

            thresholds = {}
            for rule in threshold_rules:
                metadata = (
                    rule.metadata
                )  # Access metadata property directly from MemoryItem
                if (
                    metadata.get("rule_category") == "confidence_thresholds"
                    and metadata.get("threshold_category") == "asset_identification"
                ):
                    threshold_data = metadata.get("thresholds", {})
                    thresholds.update(threshold_data)
                    break

            # Set defaults if not found in memory
            if not thresholds:
                logger.warning(
                    "No confidence thresholds found in memory, using defaults"
                )
                thresholds = {
                    "asset_match_confidence_threshold": 0.7,
                    "exact_word_match_confidence": 0.95,
                    "all_words_match_confidence": 0.85,
                    "substring_match_confidence": 0.75,
                    "partial_words_match_confidence": 0.65,
                    "weak_match_minimum": 0.5,
                }

            # Cache the result
            self._thresholds_cache = thresholds
            logger.debug(f"Loaded confidence thresholds: {thresholds}")
            return thresholds

        except Exception as e:
            logger.error(f"Failed to load confidence thresholds from memory: {e}")
            # Return hardcoded defaults as fallback
            return {
                "asset_match_confidence_threshold": 0.7,
                "exact_word_match_confidence": 0.95,
                "all_words_match_confidence": 0.85,
                "substring_match_confidence": 0.75,
                "partial_words_match_confidence": 0.65,
                "weak_match_minimum": 0.5,
            }

    @log_function()
    async def identify_asset(
        self, context: IdentificationContext, known_assets: list[Asset]
    ) -> Optional[AssetMatch]:
        """
        Identify which asset a document belongs to.

        This is the main entry point for asset identification. It implements
        a clean pipeline that prioritizes high-confidence matches and avoids
        false positives.

        Args:
            context: All available context for identification
            known_assets: List of available assets to match against

        Returns:
            AssetMatch if a confident match is found, None otherwise

        Raises:
            IdentificationError: If the identification process fails
        """
        logger.info(f"Starting asset identification for: {context.filename}")

        if not known_assets:
            logger.warning("No known assets available for matching")
            return None

        try:
            # Step 1: Check sender mappings (highest confidence)
            if context.sender_email:
                sender_match = await self._check_sender_mapping(
                    context.sender_email, known_assets
                )
                if sender_match:
                    logger.info(
                        f"Found sender mapping: {sender_match.asset_name} "
                        f"(confidence: {sender_match.confidence:.2f})"
                    )
                    return sender_match

            # Step 2: Apply pattern matching
            pattern_match = await self._apply_pattern_matching(context, known_assets)

            # Step 3: Apply confidence threshold
            if pattern_match and pattern_match.confidence >= self.confidence_threshold:
                logger.info(
                    f"Found pattern match: {pattern_match.asset_name} "
                    f"(confidence: {pattern_match.confidence:.2f})"
                )
                return pattern_match
            elif pattern_match:
                logger.info(
                    f"Pattern match below threshold: {pattern_match.asset_name} "
                    f"({pattern_match.confidence:.2f} < {self.confidence_threshold})"
                )

            # Step 4: No confident match found
            logger.info("No confident asset match found")
            return None

        except Exception as e:
            logger.error(f"Asset identification failed: {e}")
            raise IdentificationError(
                f"Failed to identify asset for {context.filename}",
                details={"error": str(e), "context": context},
            )

    async def _check_sender_mapping(
        self, sender_email: str, known_assets: list[Asset]
    ) -> Optional[AssetMatch]:
        """
        Check if sender email has an existing asset mapping.

        Args:
            sender_email: Email address to check
            known_assets: List of known assets for name lookup

        Returns:
            AssetMatch if mapping exists, None otherwise
        """
        # Convert asset list to lookup dict
        asset_lookup = {asset.deal_id: asset for asset in known_assets}

        # Query sender mappings
        match = await self.sender_mappings.get_asset_match_from_sender(
            sender_email,
            {aid: {"deal_name": a.deal_name} for aid, a in asset_lookup.items()},
        )

        if match and match.asset_id in asset_lookup:
            # Update with full asset name
            match.asset_name = asset_lookup[match.asset_id].deal_name

        return match

    async def _apply_pattern_matching(
        self, context: IdentificationContext, known_assets: list[Asset]
    ) -> Optional[AssetMatch]:
        """
        Apply simple pattern matching to identify assets.

        This implements clean pattern matching that:
        - Checks exact matches in identifiers
        - Checks word boundaries to avoid partial matches
        - Returns proper confidence scores

        Args:
            context: Identification context
            known_assets: List of assets to match against

        Returns:
            Best matching asset or None
        """
        combined_text = context.get_combined_text()
        best_match = None
        best_confidence = 0.0

        for asset in known_assets:
            # Check all identifiers for this asset
            all_identifiers = [asset.deal_name, asset.asset_name] + asset.identifiers

            max_confidence = 0.0
            matched_identifier = None

            for identifier in all_identifiers:
                if not identifier:
                    continue

                confidence = await self._calculate_identifier_confidence(
                    identifier, combined_text
                )

                if confidence > max_confidence:
                    max_confidence = confidence
                    matched_identifier = identifier

            # Track best overall match
            if max_confidence > best_confidence:
                best_confidence = max_confidence
                best_match = AssetMatch(
                    asset_id=asset.deal_id,
                    asset_name=asset.deal_name,
                    confidence=max_confidence,
                    match_source="pattern_match",
                    match_details={
                        "matched_identifier": matched_identifier,
                        "pattern_type": await self._get_pattern_type(max_confidence),
                    },
                )

        return best_match

    async def _calculate_identifier_confidence(
        self, identifier: str, text: str
    ) -> float:
        """
        Calculate confidence score for an identifier match.

        Uses business rules from memory instead of hardcoded scores.

        Args:
            identifier: The identifier to match
            text: The text to search in

        Returns:
            Confidence score between 0.0 and 1.0
        """
        identifier_lower = identifier.lower()
        text_lower = text.lower()

        # Get confidence scores from memory
        thresholds = await self._get_confidence_thresholds()
        exact_word_confidence = thresholds.get("exact_word_match_confidence", 0.95)
        substring_confidence = thresholds.get("substring_match_confidence", 0.75)
        all_words_confidence = thresholds.get("all_words_match_confidence", 0.85)
        partial_words_confidence = thresholds.get(
            "partial_words_match_confidence", 0.65
        )

        # Exact match gets highest confidence
        if identifier_lower in text_lower:
            # Check if it's a word boundary match (not substring)
            pattern = r"\b" + re.escape(identifier_lower) + r"\b"
            if re.search(pattern, text_lower):
                return exact_word_confidence
            else:
                return substring_confidence

        # Check individual words for multi-word identifiers
        if " " in identifier_lower:
            words = identifier_lower.split()
            matching_words = sum(
                1 for word in words if len(word) >= 3 and word in text_lower
            )
            if matching_words == len(words):
                return all_words_confidence
            elif matching_words >= len(words) * 0.7:
                return partial_words_confidence

        # No significant match
        return 0.0

    async def _get_pattern_type(self, confidence: float) -> str:
        """Get descriptive pattern type based on confidence from memory."""
        # Get thresholds from memory
        thresholds = await self._get_confidence_thresholds()
        exact_word_confidence = thresholds.get("exact_word_match_confidence", 0.95)
        all_words_confidence = thresholds.get("all_words_match_confidence", 0.85)
        substring_confidence = thresholds.get("substring_match_confidence", 0.75)
        partial_words_confidence = thresholds.get(
            "partial_words_match_confidence", 0.65
        )

        if confidence >= exact_word_confidence:
            return "exact_word_match"
        elif confidence >= all_words_confidence:
            return "all_words_match"
        elif confidence >= substring_confidence:
            return "substring_match"
        elif confidence >= partial_words_confidence:
            return "partial_word_match"
        else:
            return "weak_match"

"""
Asset Matcher Node - Matches email attachments to specific investment assets.

This node queries procedural memory for HOW to perform matching (algorithms, weights)
and semantic memory for WHAT to match against (asset profiles, relationships).
"""

# # Standard library imports
from typing import Any

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class AssetMatcherNode:
    """
    Matches relevant attachments to specific investment assets using memory-driven logic.

    Separates HOW (procedural memory) from WHAT (semantic memory).
    """

    def __init__(self, semantic_memory=None, procedural_memory=None) -> None:
        """
        Initialize asset matcher with memory system connections.

        Args:
            semantic_memory: Semantic memory for asset profiles and relationships
            procedural_memory: Procedural memory for matching algorithms and rules
        """
        self.semantic_memory = semantic_memory
        self.procedural_memory = procedural_memory
        self.asset_match_threshold = (
            config.requires_review_threshold
        )  # Using existing config

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

        matches = []
        for attachment in attachments:
            attachment_matches = await self._match_single_attachment(
                attachment, email_data, matching_rules, available_assets
            )
            matches.extend(attachment_matches)

        logger.info(f"Generated {len(matches)} asset matches")
        return matches

    async def _match_single_attachment(
        self,
        attachment: dict[str, Any],
        email_data: dict[str, Any],
        matching_rules: dict[str, Any],
        available_assets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Match a single attachment to assets using memory-driven logic.

        Args:
            attachment: Attachment metadata
            email_data: Email context
            matching_rules: Rules from procedural memory
            available_assets: Asset profiles from semantic memory

        Returns:
            List of matches for this attachment
        """
        filename = attachment.get("filename", "")
        matches = []

        # For now, use simple pattern matching until memory systems are connected
        # TODO: Replace with actual memory queries
        simple_matches = await self._simple_asset_matching(
            filename, email_data, available_assets
        )

        for asset_id, confidence in simple_matches.items():
            if confidence >= self.asset_match_threshold:
                matches.append(
                    {
                        "attachment_filename": filename,
                        "asset_id": asset_id,
                        "confidence": confidence,
                        "reasoning": {
                            "match_factors": [f"Pattern match for {asset_id}"],
                            "confidence_factors": [f"Score: {confidence:.2f}"],
                        },
                    }
                )

        return matches

    async def _simple_asset_matching(
        self,
        filename: str,
        email_data: dict[str, Any],
        available_assets: list[dict[str, Any]],
    ) -> dict[str, float]:
        """
        Simple asset matching until memory systems are integrated.

        This is a placeholder that will be replaced with memory queries.
        """
        matches = {}
        filename_lower = filename.lower()

        # Basic pattern matching (will be replaced with semantic memory queries)
        if "fund" in filename_lower or "af_" in filename_lower:
            matches["FUND001"] = 0.8

        if "compliance" in filename_lower:
            matches["FUND001"] = 0.8  # Same fund for demo

        if "real" in filename_lower or "estate" in filename_lower:
            matches["REALESTATE001"] = 0.7

        # Subject line clues
        subject = email_data.get("subject", "").lower()
        if "alpha" in subject and "fund" in subject:
            matches["FUND001"] = matches.get("FUND001", 0.0) + 0.2

        return matches

    async def query_matching_procedures(
        self, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Query procedural memory for asset matching algorithms and rules.

        TODO: Implement when procedural memory is available.

        Args:
            context: Email and attachment context

        Returns:
            Dictionary of matching procedures and weights
        """
        if not self.procedural_memory:
            logger.warning("Procedural memory not available, using defaults")
            return self._get_default_matching_rules()

        # This will query procedural memory for:
        # - Filename pattern matching algorithms
        # - Subject line analysis procedures
        # - Sender-asset relationship weighting
        # - Confidence calculation methods
        # - Multi-signal combination rules

        return {}

    async def query_asset_profiles(
        self, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Query semantic memory for asset profiles and relationships.

        TODO: Implement when semantic memory is available.

        Args:
            context: Email context for filtering relevant assets

        Returns:
            List of asset profiles with keywords and patterns
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available, using defaults")
            return self._get_default_asset_profiles()

        # This will query semantic memory for:
        # - Asset profiles (names, IDs, descriptions)
        # - Historical sender-asset relationships
        # - Document type patterns per asset
        # - Keywords associated with each asset
        # - Previous successful matches

        return []

    def _get_default_matching_rules(self) -> dict[str, Any]:
        """Default matching rules until procedural memory is available."""
        return {
            "filename_weight": 0.4,
            "subject_weight": 0.3,
            "sender_weight": 0.3,
            "confidence_threshold": self.asset_match_threshold,
            "multi_match_allowed": True,
            "max_matches_per_attachment": 3,
        }

    def _get_default_asset_profiles(self) -> list[dict[str, Any]]:
        """Default asset profiles until semantic memory is available."""
        return [
            {
                "asset_id": "FUND001",
                "name": "Alpha Investment Fund",
                "keywords": ["alpha", "fund", "af_", "investment"],
                "document_types": ["financial_statements", "compliance_documents"],
                "typical_senders": ["investor.relations", "compliance", "audit"],
            },
            {
                "asset_id": "REALESTATE001",
                "name": "Beta Real Estate Portfolio",
                "keywords": ["real", "estate", "property", "beta"],
                "document_types": ["property_reports", "valuations"],
                "typical_senders": ["property.management", "valuation"],
            },
        ]

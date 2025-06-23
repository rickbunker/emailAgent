"""
Document classification module.

This module provides clean document classification that:
1. Uses semantic memory to get asset type categories (not hardcoded)
2. Uses semantic memory to get classification patterns (not hardcoded)
3. Applies pattern matching algorithms for classification
4. Returns proper confidence scores

The module properly separates concerns:
- Semantic Memory: FACTS (categories, patterns)
- This Module: HOW to apply those facts (algorithms)
"""

# # Standard library imports
import re
from typing import Any, Optional

# # Local application imports
from src.asset_management.core.data_models import (
    AssetType,
    CategoryMatch,
    ClassificationContext,
    DocumentCategory,
)
from src.asset_management.core.exceptions import ClassificationError, MemorySystemError
from src.memory.semantic import SemanticMemory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class DocumentClassifier:
    """
    Main document classification service.

    Implements clean classification that:
    1. Gets allowed categories from semantic memory (not hardcoded)
    2. Gets patterns from semantic memory (not hardcoded)
    3. Applies pattern matching algorithms
    4. Returns appropriate confidence scores

    This properly separates:
    - FACTS (in semantic memory): What categories exist, what patterns match
    - ALGORITHMS (in this code): How to apply patterns and calculate scores
    """

    def __init__(
        self,
        semantic_memory: Optional[SemanticMemory] = None,
        confidence_threshold: Optional[float] = None,
    ):
        """
        Initialize the document classifier.

        Args:
            semantic_memory: Semantic memory instance for accessing facts.
                           If not provided, creates a new one.
            confidence_threshold: Minimum confidence for classification.
                                Defaults to config.document_classification_threshold
        """
        self.semantic_memory = semantic_memory or self._create_semantic_memory()
        self.confidence_threshold = confidence_threshold or getattr(
            config, "document_classification_threshold", 0.5
        )
        # Cache for performance (cleared periodically)
        self._category_cache: dict[str, list[str]] = {}
        self._pattern_cache: dict[str, list[dict[str, Any]]] = {}

        logger.info(
            f"Document classifier initialized with threshold: {self.confidence_threshold}"
        )

    def _create_semantic_memory(self) -> SemanticMemory:
        """Create a new semantic memory instance."""
        try:
            return SemanticMemory(
                max_items=getattr(config, "semantic_memory_max_items", 50000),
                qdrant_url=getattr(config, "qdrant_url", "http://localhost:6333"),
                embedding_model=getattr(config, "embedding_model", "all-MiniLM-L6-v2"),
            )
        except Exception as e:
            logger.error(f"Failed to create semantic memory: {e}")
            raise MemorySystemError(
                "Could not initialize semantic memory", details={"error": str(e)}
            )

    @log_function()
    async def classify_document(
        self, context: ClassificationContext
    ) -> Optional[CategoryMatch]:
        """
        Classify a document into the appropriate category.

        This method:
        1. Gets allowed categories from semantic memory (FACTS)
        2. Gets classification patterns from semantic memory (FACTS)
        3. Applies pattern matching algorithms (ALGORITHM)
        4. Returns the best match with confidence

        Args:
            context: Classification context with filename and asset type

        Returns:
            CategoryMatch with the best matching category, or None if no match

        Raises:
            ClassificationError: If classification fails
        """
        logger.info(
            f"Starting document classification for: {context.filename} "
            f"(asset type: {context.asset_type.value})"
        )

        try:
            # Step 1: Get allowed categories from semantic memory (FACTS)
            allowed_categories = await self._get_allowed_categories(context.asset_type)

            if not allowed_categories:
                logger.warning(
                    f"No categories found for asset type: {context.asset_type.value}"
                )
                return None

            # Step 2: Apply pattern matching (ALGORITHM)
            best_match = await self._apply_pattern_matching(
                context.filename, allowed_categories, context.asset_type
            )

            # Step 3: Check email subject/body if no filename match
            if not best_match and (context.email_subject or context.email_body):
                content = f"{context.email_subject or ''} {context.email_body or ''}"
                best_match = await self._apply_pattern_matching(
                    content, allowed_categories, context.asset_type
                )

            # Step 4: Default to correspondence if configured
            if not best_match and "correspondence" in [
                cat.lower() for cat in allowed_categories
            ]:
                best_match = CategoryMatch(
                    category=DocumentCategory.CORRESPONDENCE,
                    confidence=getattr(
                        config, "default_correspondence_confidence", 0.4
                    ),
                    match_source="default_fallback",
                    match_details={"reason": "No specific pattern matched"},
                )

            # Step 5: Apply threshold
            if best_match and best_match.confidence >= self.confidence_threshold:
                logger.info(
                    f"Classified as: {best_match.category.value} "
                    f"(confidence: {best_match.confidence:.2f})"
                )
                return best_match
            elif best_match:
                logger.info(
                    f"Classification below threshold: {best_match.category.value} "
                    f"({best_match.confidence:.2f} < {self.confidence_threshold})"
                )

            return None

        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            raise ClassificationError(
                f"Failed to classify document {context.filename}",
                details={"error": str(e), "context": context},
            )

    async def _get_allowed_categories(self, asset_type: AssetType) -> list[str]:
        """
        Get allowed document categories for an asset type from semantic memory.

        This retrieves FACTS from semantic memory, not hardcoded data.

        Args:
            asset_type: The asset type enum

        Returns:
            List of allowed category names
        """
        # Check cache first
        cache_key = asset_type.value
        if cache_key in self._category_cache:
            return self._category_cache[cache_key]

        try:
            # Get from semantic memory
            categories = await self.semantic_memory.get_asset_type_categories(
                asset_type.value
            )

            # Cache for performance
            self._category_cache[cache_key] = categories

            return categories

        except Exception as e:
            logger.error(f"Failed to get categories for {asset_type.value}: {e}")
            # Return minimal fallback
            return ["correspondence", "unknown"]

    async def _apply_pattern_matching(
        self, text: str, allowed_categories: list[str], asset_type: AssetType
    ) -> Optional[CategoryMatch]:
        """
        Apply pattern matching to classify document.

        This is the ALGORITHM part - HOW we match patterns.
        The patterns themselves come from semantic memory.

        Args:
            text: Text to match against (filename or content)
            allowed_categories: Categories allowed for this asset type
            asset_type: The asset type for context

        Returns:
            Best matching category or None
        """
        text_lower = text.lower()
        best_match = None
        best_confidence = 0.0

        for category_name in allowed_categories:
            # Get patterns from semantic memory (FACTS)
            patterns = await self._get_category_patterns(category_name, asset_type)

            for pattern_info in patterns:
                pattern = pattern_info.get("pattern", "")
                pattern_confidence = pattern_info.get("confidence", 0.7)

                if not pattern:
                    continue

                try:
                    if re.search(pattern, text_lower):
                        # Calculate confidence (ALGORITHM)
                        confidence = self._calculate_match_confidence(
                            pattern, text_lower, category_name, pattern_confidence
                        )

                        if confidence > best_confidence:
                            best_confidence = confidence
                            # Try to get the enum value
                            try:
                                category_enum = DocumentCategory(category_name)
                            except ValueError:
                                # Category name doesn't match enum exactly
                                # Try to find matching enum
                                category_enum = self._find_category_enum(category_name)
                                if not category_enum:
                                    logger.warning(
                                        f"Unknown category name from semantic memory: {category_name}"
                                    )
                                    continue

                            best_match = CategoryMatch(
                                category=category_enum,
                                confidence=confidence,
                                match_source="pattern_match",
                                match_details={
                                    "pattern": pattern,
                                    "matched_text": text[:100],
                                    "pattern_source": "semantic_memory",
                                },
                            )
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                    continue

        return best_match

    async def _get_category_patterns(
        self, category_name: str, asset_type: AssetType
    ) -> list[dict[str, Any]]:
        """
        Get classification patterns for a category from semantic memory.

        Args:
            category_name: The document category name
            asset_type: Asset type for context

        Returns:
            List of pattern dictionaries with 'pattern' and 'confidence' keys
        """
        cache_key = f"{asset_type.value}:{category_name}"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]

        try:
            # Query semantic memory for classification patterns
            classification_hints = await self.semantic_memory.get_classification_hints(
                asset_type.value,
                {"category": category_name, "request_type": "patterns"},
            )

            patterns = []
            for hint in classification_hints:
                if hint.get("hint_type") == "pattern":
                    patterns.append(
                        {
                            "pattern": hint.get("pattern", ""),
                            "confidence": hint.get("confidence", 0.7),
                        }
                    )

            # Cache for performance
            self._pattern_cache[cache_key] = patterns

            return patterns

        except Exception as e:
            logger.error(f"Failed to get patterns for {category_name}: {e}")
            return []

    def _calculate_match_confidence(
        self, pattern: str, text: str, category: str, base_confidence: float
    ) -> float:
        """
        Calculate confidence score for a pattern match.

        This is pure ALGORITHM - HOW we calculate confidence.
        The base confidence comes from semantic memory.

        Args:
            pattern: The regex pattern that matched
            text: The text that was matched
            category: The document category name
            base_confidence: Base confidence from semantic memory

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with base confidence from semantic memory
        confidence = base_confidence

        # Apply algorithmic adjustments

        # Boost for specific/longer patterns
        if len(pattern) > 20:  # Complex pattern
            confidence *= getattr(config, "complex_pattern_boost", 1.1)

        # Boost for exact word boundaries
        if r"\b" in pattern:  # Uses word boundaries
            confidence *= getattr(config, "word_boundary_boost", 1.05)

        # Ensure within bounds
        return min(1.0, max(0.0, confidence))

    def _find_category_enum(self, category_name: str) -> Optional[DocumentCategory]:
        """
        Find matching DocumentCategory enum for a category name.

        Handles variations like 'rent_roll' vs 'RENT_ROLL'.

        Args:
            category_name: Category name from semantic memory

        Returns:
            Matching DocumentCategory enum or None
        """
        # Normalize the name
        normalized = category_name.upper().replace("-", "_").replace(" ", "_")

        # Try direct match
        try:
            return DocumentCategory(normalized)
        except ValueError:
            pass

        # Try matching by value
        for cat in DocumentCategory:
            if cat.value.upper() == normalized:
                return cat

        # Try fuzzy matching
        for cat in DocumentCategory:
            if normalized in cat.value.upper() or cat.value.upper() in normalized:
                return cat

        return None

    def clear_cache(self) -> None:
        """Clear the internal caches."""
        self._category_cache.clear()
        self._pattern_cache.clear()
        logger.info("Document classifier caches cleared")

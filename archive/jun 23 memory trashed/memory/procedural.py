"""
Procedural Memory System for Asset Document Agent

Stores stable business rules and procedures (like compiled program code).
Contains proven, tested patterns and algorithms that form the foundation
of asset identification and document classification logic.

Key Features:
    - Stable business rule storage and evaluation
    - Asset type-aware pattern matching
    - Procedural classification algorithms
    - Configuration rule management
    - Business rule validation

Author: Rick Bunker
License: For Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# # Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from ..utils.logging_system import get_logger, log_function


class PatternType(Enum):
    """Types of stable business rule patterns"""

    CLASSIFICATION = "classification"  # Document classification business rules
    ASSET_MATCHING = "asset_matching"  # Asset identification business rules
    CONFIGURATION = "configuration"  # Configuration business rules
    CONFIDENCE = "confidence"  # Confidence scoring business rules
    ROUTING = "routing"  # Document routing business rules
    VALIDATION = "validation"  # File validation business rules


class RuleType(Enum):
    """Types of procedural rules stored in memory."""

    CLASSIFICATION = "classification"
    ROUTING = "routing"
    APPROVAL = "approval"
    VALIDATION = "validation"
    NOTIFICATION = "notification"


class RulePriority(Enum):
    """Priority levels for procedural rules."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleConfidence(Enum):
    """Confidence levels for procedural rules."""

    VERY_HIGH = "very_high"  # >= 95%
    HIGH = "high"  # >= 80%
    MEDIUM = "medium"  # >= 60%
    LOW = "low"  # >= 40%
    VERY_LOW = "very_low"  # < 40%


@dataclass
class BusinessRule:
    """A stable business rule or procedural pattern"""

    rule_id: str
    rule_type: PatternType
    rule_data: dict[str, Any]
    usage_count: int
    confidence: float
    last_used: datetime
    created_date: datetime
    source: str  # "knowledge_base", "initial_seed", "validated_rule"


class ProceduralMemory:
    """
    Procedural memory system for stable business rules and procedures.

    Stores proven, compiled business logic for asset identification and
    document classification. Does not learn or adapt - contains stable
    rules like program code that form the foundation of decision-making.
    """

    def __init__(self, qdrant_client: QdrantClient):
        """Initialize procedural memory system."""
        self.logger = get_logger(f"{__name__}.ProceduralMemory")
        self.qdrant = qdrant_client

        # Collections for different types of procedural knowledge
        self.collections = {
            "classification_patterns": "procedural_classification_patterns",
            "asset_patterns": "procedural_asset_patterns",
            "configuration_rules": "procedural_configuration_rules",
            "confidence_models": "procedural_confidence_models",
        }

        self.logger.info("Procedural memory system initialized")

    @log_function()
    async def initialize_collections(self) -> bool:
        """Initialize Qdrant collections for procedural memory."""
        try:
            for collection_name in self.collections.values():
                if not await self._collection_exists(collection_name):
                    await self._create_collection(
                        collection_name,
                        vector_size=384,  # sentence-transformers dimension
                        description=f"Procedural memory: {collection_name}",
                    )
                    self.logger.info(
                        f"Created procedural collection: {collection_name}"
                    )

            # Seed initial patterns if collections are empty
            await self._seed_initial_patterns()
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize procedural collections: {e}")
            return False

    async def _collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            collections = self.qdrant.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception:
            return False

    async def _create_collection(
        self, collection_name: str, vector_size: int, description: str
    ):
        """Create a Qdrant collection."""
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    @log_function()
    async def classify_document_with_details(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        asset_type: str | None = None,
    ) -> tuple[str, float, dict[str, Any]]:
        """
        Classify document using memory-driven patterns with detailed pattern information.

        Args:
            filename: Document filename
            email_subject: Email subject
            email_body: Email body content
            asset_type: Asset type context for filtering

        Returns:
            Tuple of (document_category, confidence, detailed_patterns)
        """
        self.logger.info("🔍 Memory-driven document classification with details")

        try:
            # Get all stored classification patterns from procedural memory
            scroll_result = self.qdrant.scroll(
                collection_name=self.collections["classification_patterns"],
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            if not scroll_result[0]:
                self.logger.warning("No classification patterns in procedural memory")
                return "unknown", 0.0, {"patterns_used": [], "total_patterns": 0}

            patterns = scroll_result[0]
            combined_text = f"{filename} {email_subject} {email_body}".lower()

            # Vote-based classification using all stored patterns
            category_votes: dict[str, list[float]] = {}
            patterns_evaluated = 0
            detailed_patterns = []

            for point in patterns:
                try:
                    payload = point.payload
                    # Data is stored at top level, not nested under pattern_data
                    category = payload.get("document_category", "unknown")

                    if category == "unknown":
                        continue

                    patterns_evaluated += 1

                    # Evaluate this memory pattern against current document
                    match_score = await self._evaluate_memory_pattern(
                        payload, combined_text, filename, email_subject, email_body
                    )

                    # Apply asset type context weighting
                    pattern_asset_type = payload.get("asset_type", "")
                    if asset_type and pattern_asset_type:
                        if pattern_asset_type == asset_type:
                            match_score *= 1.2  # Boost for matching asset type
                        else:
                            match_score *= 0.8  # Reduce for non-matching asset type

                    if match_score > 0.1:  # Only consider meaningful matches
                        if category not in category_votes:
                            category_votes[category] = []
                        category_votes[category].append(match_score)

                        # Store detailed pattern information
                        detailed_patterns.append(
                            {
                                "pattern_id": payload.get("pattern_id", "unknown"),
                                "category": category,
                                "match_score": match_score,
                                "asset_type": pattern_asset_type,
                                "source": payload.get("source", "unknown"),
                                "pattern_type": payload.get(
                                    "pattern_type", "classification"
                                ),
                                "regex_patterns": payload.get("regex_patterns", []),
                                "keywords": payload.get("keywords", []),
                                "filename_indicators": payload.get(
                                    "filename_indicators", []
                                ),
                                "subject_indicators": payload.get(
                                    "subject_indicators", []
                                ),
                                "created_date": payload.get("created_date", "unknown"),
                            }
                        )

                        self.logger.debug(
                            f"Pattern vote: {category} = {match_score:.3f} (ID: {payload.get('pattern_id', 'unknown')[:8]})"
                        )

                except Exception as e:
                    self.logger.debug(f"Error evaluating pattern: {e}")
                    continue

            if not category_votes:
                self.logger.info(
                    f"No pattern matches from {patterns_evaluated} patterns"
                )
                return (
                    "unknown",
                    0.0,
                    {
                        "patterns_used": [],
                        "total_patterns": patterns_evaluated,
                        "categories_considered": 0,
                    },
                )

            # Calculate final classification from votes
            best_category = "unknown"
            best_confidence = 0.0

            for category, scores in category_votes.items():
                # Use average confidence with vote count bonus
                avg_confidence = sum(scores) / len(scores)
                vote_bonus = min(
                    len(scores) * 0.1, 0.3
                )  # Max 30% bonus for multiple votes
                final_confidence = min(avg_confidence + vote_bonus, 1.0)

                if final_confidence > best_confidence:
                    best_confidence = final_confidence
                    best_category = category

            # Sort patterns by match score and filter to winning category
            winning_patterns = [
                p for p in detailed_patterns if p["category"] == best_category
            ]
            winning_patterns.sort(key=lambda x: x["match_score"], reverse=True)

            detailed_info = {
                "patterns_used": winning_patterns[
                    :5
                ],  # Top 5 patterns for winning category
                "all_matching_patterns": detailed_patterns,
                "total_patterns": patterns_evaluated,
                "categories_considered": len(category_votes),
                "category_votes": {
                    cat: len(scores) for cat, scores in category_votes.items()
                },
                "winning_category_votes": len(category_votes.get(best_category, [])),
                "avg_winning_score": (
                    sum(category_votes.get(best_category, []))
                    / len(category_votes.get(best_category, []))
                    if category_votes.get(best_category)
                    else 0.0
                ),
            }

            self.logger.info(
                f"Memory classification: {best_category} ({best_confidence:.3f}) "
                f"from {len(category_votes)} categories, {patterns_evaluated} patterns"
            )

            return best_category, best_confidence, detailed_info

        except Exception as e:
            self.logger.error(f"Memory-driven classification failed: {e}")
            return (
                "unknown",
                0.0,
                {"patterns_used": [], "total_patterns": 0, "error": str(e)},
            )

    @log_function()
    async def classify_document(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        asset_type: str | None = None,
    ) -> tuple[str, float]:
        """
        Classify document using simplified pattern matching.

        Args:
            filename: Document filename
            email_subject: Email subject
            email_body: Email body content
            asset_type: Asset type context for filtering

        Returns:
            Tuple of (document_category, confidence)
        """
        self.logger.info("🔍 Simplified document classification")

        try:
            # Get classification patterns from memory
            scroll_result = self.qdrant.scroll(
                collection_name=self.collections["classification_patterns"],
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            if not scroll_result[0]:
                self.logger.warning("No classification patterns in procedural memory")
                return "unknown", 0.0

            patterns = scroll_result[0]

            # Combine all text for matching
            combined_text = f"{filename} {email_subject} {email_body}".lower()

            best_category = "unknown"
            best_confidence = 0.0

            # Direct pattern matching without complex voting
            for point in patterns:
                try:
                    payload = point.payload
                    category = payload.get("document_category", "unknown")
                    pattern_asset_type = payload.get("asset_type", "")

                    # Skip if asset type doesn't match (when specified)
                    if (
                        asset_type
                        and pattern_asset_type
                        and pattern_asset_type != asset_type
                    ):
                        continue

                    # Simple keyword matching
                    keywords = payload.get("keywords", [])
                    filename_indicators = payload.get("filename_indicators", [])

                    keyword_matches = 0
                    filename_matches = 0

                    # Check keywords in combined text
                    for keyword in keywords:
                        if keyword.lower() in combined_text:
                            keyword_matches += 1

                    # Check filename indicators
                    filename_lower = filename.lower()
                    for indicator in filename_indicators:
                        if indicator.lower() in filename_lower:
                            filename_matches += 1

                    # Calculate simple confidence score
                    confidence = 0.0

                    # Filename matches are highly indicative
                    if filename_matches > 0:
                        confidence = 0.8 + (0.1 * min(filename_matches, 2))

                    # Keywords add confidence
                    if keywords and keyword_matches > 0:
                        keyword_ratio = keyword_matches / len(keywords)
                        confidence = max(confidence, 0.5 + (0.4 * keyword_ratio))

                    # Check regex patterns for high confidence
                    regex_patterns = payload.get("regex_patterns", [])
                    for pattern in regex_patterns[:3]:  # Check first 3 patterns only
                        try:
                            # # Standard library imports
                            import re

                            if re.search(pattern, combined_text):
                                confidence = max(confidence, 0.85)
                                break
                        except:
                            continue

                    # Update best match
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_category = category

                except Exception as e:
                    self.logger.debug(f"Error evaluating pattern: {e}")
                    continue

            # Apply minimum confidence threshold
            if best_confidence < 0.3:
                best_category = "unknown"
                best_confidence = 0.0

            self.logger.info(
                f"Classification result: {best_category} (confidence: {best_confidence:.2f})"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Classification failed: {e}")
            return "unknown", 0.0

    async def _extract_patterns(self, text: str, category: str) -> list[str]:
        """Extract meaningful patterns from successful classification."""
        patterns = []

        # Extract key phrases (2-4 words)
        words = text.split()
        for i in range(len(words) - 1):
            phrase = " ".join(words[i : i + 2])
            if len(phrase) > 5:  # Skip very short phrases
                patterns.append(phrase)

        # Extract category-specific indicators
        category_terms = category.replace("_", " ").split()
        for term in category_terms:
            if term in text:
                patterns.append(term)

        return list(set(patterns))  # Remove duplicates

    @log_function()
    async def get_classification_rules(
        self, asset_type: str | None = None
    ) -> dict[str, Any]:
        """
        Get stable business rules for document classification.

        Args:
            asset_type: Optional filter for asset type specific rules

        Returns:
            Dictionary containing classification rules and patterns

        Raises:
            RuntimeError: If unable to retrieve rules from memory
        """
        try:
            # Get all stored classification patterns from procedural memory
            scroll_result = self.qdrant.scroll(
                collection_name=self.collections["classification_patterns"],
                limit=10000,  # Get all patterns
                with_payload=True,
                with_vectors=False,
            )

            if not scroll_result or not scroll_result[0]:
                self.logger.warning("No classification rules in procedural memory")
                return {"rules": [], "total_count": 0, "asset_type_filter": asset_type}

            patterns = scroll_result[0]

            # Filter by asset type if specified
            filtered_rules = []
            for point in patterns:
                try:
                    payload = point.payload
                    # Data is stored at top level, not nested under pattern_data
                    category = payload.get("document_category", "unknown")
                    pattern_asset_type = payload.get("asset_type", "")

                    # Skip if asset type filter doesn't match
                    if asset_type:
                        if pattern_asset_type and pattern_asset_type != asset_type:
                            continue

                    rule = {
                        "rule_id": payload.get("pattern_id", "unknown"),
                        "category": category,
                        "asset_type": payload.get("asset_type", "any"),
                        "confidence_range": payload.get("confidence_range", (0.0, 1.0)),
                        "regex_patterns": payload.get("regex_patterns", []),
                        "keywords": payload.get("keywords", []),
                        "filename_indicators": payload.get("filename_indicators", []),
                        "subject_indicators": payload.get("subject_indicators", []),
                        "source": payload.get("source", "unknown"),
                        "created_date": payload.get("created_date", "unknown"),
                    }
                    filtered_rules.append(rule)

                except Exception as e:
                    self.logger.debug(f"Error processing rule: {e}")
                    continue

            self.logger.info(
                f"Retrieved {len(filtered_rules)} classification rules (asset_type: {asset_type})"
            )

            return {
                "rules": filtered_rules,
                "total_count": len(filtered_rules),
                "asset_type_filter": asset_type,
                "categories_available": list(
                    set(rule["category"] for rule in filtered_rules)
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to get classification rules: {e}")
            raise RuntimeError(f"Unable to retrieve classification rules: {e}")

    @log_function()
    async def get_asset_matching_rules(self) -> dict[str, Any]:
        """
        Get stable business rules for asset identification.

        Returns:
            Dictionary containing asset matching rules and procedures

        Raises:
            RuntimeError: If unable to retrieve rules from memory
        """
        try:
            # Get asset patterns from procedural memory
            scroll_result = self.qdrant.scroll(
                collection_name=self.collections["asset_patterns"],
                limit=10000,  # Get all patterns
                with_payload=True,
                with_vectors=False,
            )

            asset_rules = []
            if scroll_result and scroll_result[0]:
                for point in scroll_result[0]:
                    try:
                        payload = point.payload
                        # Data is stored at top level, not nested under pattern_data
                        asset_type = payload.get("asset_type", "unknown")

                        rule = {
                            "rule_id": payload.get("pattern_id", "unknown"),
                            "asset_type": asset_type,
                            "matching_keywords": payload.get("keywords", []),
                            "regex_patterns": payload.get("regex_patterns", []),
                            "confidence_threshold": payload.get(
                                "confidence_threshold", 0.5
                            ),
                            "priority": payload.get("priority", "medium"),
                            "source": payload.get("source", "unknown"),
                            "created_date": payload.get("created_date", "unknown"),
                        }
                        asset_rules.append(rule)

                    except Exception as e:
                        self.logger.debug(f"Error processing asset rule: {e}")
                        continue

            self.logger.info(f"Retrieved {len(asset_rules)} asset matching rules")

            return {
                "rules": asset_rules,
                "total_count": len(asset_rules),
                "asset_types_available": list(
                    set(rule["asset_type"] for rule in asset_rules)
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to get asset matching rules: {e}")
            raise RuntimeError(f"Unable to retrieve asset matching rules: {e}")

    @log_function()
    async def evaluate_business_rules(
        self, context: dict[str, Any], constraints: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Evaluate business rules against provided context.

        Args:
            context: Context data containing filename, subject, body, asset_type, etc.
            constraints: Optional constraints to filter applicable rules

        Returns:
            Dictionary containing evaluation results and applicable rules

        Raises:
            ValueError: If context is missing required fields
            RuntimeError: If rule evaluation fails
        """
        # Validate required context fields
        required_fields = ["filename", "email_subject", "email_body"]
        missing_fields = [field for field in required_fields if field not in context]
        if missing_fields:
            raise ValueError(f"Context missing required fields: {missing_fields}")

        try:
            filename = context["filename"]
            email_subject = context["email_subject"]
            email_body = context["email_body"]
            asset_type = context.get("asset_type")

            # Get applicable classification rules
            classification_rules = await self.get_classification_rules(asset_type)
            combined_text = f"{filename} {email_subject} {email_body}".lower()

            # Evaluate each rule
            rule_evaluations = []
            for rule in classification_rules["rules"]:
                try:
                    # Evaluate rule against context
                    match_score = await self._evaluate_memory_pattern(
                        rule, combined_text, filename, email_subject, email_body
                    )

                    # Apply constraints if provided
                    if constraints:
                        min_confidence = constraints.get("min_confidence", 0.0)
                        if match_score < min_confidence:
                            continue

                        required_category = constraints.get("required_category")
                        if required_category and rule["category"] != required_category:
                            continue

                    if match_score > 0.1:  # Only include meaningful matches
                        rule_evaluations.append(
                            {
                                "rule_id": rule["rule_id"],
                                "category": rule["category"],
                                "asset_type": rule["asset_type"],
                                "match_score": match_score,
                                "rule_source": rule["source"],
                                "confidence_range": rule["confidence_range"],
                            }
                        )

                except Exception as e:
                    self.logger.debug(
                        f"Error evaluating rule {rule.get('rule_id', 'unknown')}: {e}"
                    )
                    continue

            # Sort by match score descending
            rule_evaluations.sort(key=lambda x: x["match_score"], reverse=True)

            result = {
                "evaluated_rules": rule_evaluations,
                "total_rules_evaluated": len(classification_rules["rules"]),
                "matching_rules_count": len(rule_evaluations),
                "best_match": rule_evaluations[0] if rule_evaluations else None,
                "context_provided": context,
                "constraints_applied": constraints or {},
            }

            self.logger.info(
                f"Evaluated {len(classification_rules['rules'])} rules, "
                f"{len(rule_evaluations)} matches found"
            )

            return result

        except Exception as e:
            self.logger.error(f"Business rule evaluation failed: {e}")
            raise RuntimeError(f"Unable to evaluate business rules: {e}")

    def _extract_filename_indicators(self, filename: str) -> list[str]:
        """Extract classification indicators from filename."""
        indicators = []

        # File extension
        if "." in filename:
            indicators.append(filename.split(".")[-1].lower())

        # Common filename patterns
        filename_lower = filename.lower()
        common_patterns = [
            "report",
            "statement",
            "summary",
            "update",
            "analysis",
            "quarterly",
            "monthly",
            "annual",
            "financial",
            "legal",
        ]

        for pattern in common_patterns:
            if pattern in filename_lower:
                indicators.append(pattern)

        return indicators

    def _extract_subject_indicators(self, subject: str) -> list[str]:
        """Extract classification indicators from email subject."""
        indicators = []

        subject_lower = subject.lower()
        important_terms = [
            "urgent",
            "important",
            "quarterly",
            "monthly",
            "annual",
            "financial",
            "legal",
            "compliance",
            "report",
            "update",
        ]

        for term in important_terms:
            if term in subject_lower:
                indicators.append(term)

        return indicators

    async def _evaluate_memory_pattern(
        self,
        pattern_data: dict[str, Any],
        combined_text: str,
        filename: str,
        email_subject: str,
        email_body: str,
    ) -> float:
        """
        Evaluate how well a stored memory pattern matches current document.

        This method handles both knowledge base patterns and learned patterns.
        """
        total_score = 0.0
        evaluation_methods = 0

        # Method 1: Knowledge base regex patterns (from seeded patterns)
        if "regex_patterns" in pattern_data:
            regex_patterns = pattern_data["regex_patterns"]
            if regex_patterns:
                evaluation_methods += 1
                regex_score = await self._evaluate_regex_patterns(
                    regex_patterns, combined_text
                )
                total_score += regex_score
                if regex_score > 0:
                    self.logger.debug(f"Regex match score: {regex_score:.3f}")

        # Method 2: Learned text patterns (from human feedback/auto-learning)
        learned_score = await self._evaluate_learned_patterns(
            pattern_data, filename, email_subject, email_body
        )
        if learned_score > 0:
            evaluation_methods += 1
            total_score += learned_score
            self.logger.debug(f"Learned pattern score: {learned_score:.3f}")

        # Method 3: Keyword matching (from asset keywords)
        if "keywords" in pattern_data:
            keywords = pattern_data["keywords"]
            if keywords:
                evaluation_methods += 1
                keyword_score = await self._evaluate_keyword_patterns(
                    keywords, combined_text
                )
                total_score += keyword_score
                if keyword_score > 0:
                    self.logger.debug(f"Keyword match score: {keyword_score:.3f}")

        # Return average score if any evaluation methods were used
        if evaluation_methods > 0:
            return total_score / evaluation_methods
        else:
            return 0.0

    async def _evaluate_regex_patterns(
        self, regex_patterns: list[str], combined_text: str
    ) -> float:
        """Evaluate regex patterns from knowledge base."""
        if not regex_patterns:
            return 0.0

        # # Standard library imports
        import re

        matches_found = 0
        total_weight = 0.0

        for pattern in regex_patterns:
            try:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    # Weight longer, more specific patterns higher
                    pattern_weight = min(len(pattern) / 20.0, 1.0)
                    total_weight += pattern_weight
                    matches_found += 1
                    self.logger.debug(f"Regex match: '{pattern[:50]}...'")
            except re.error as e:
                self.logger.debug(f"Invalid regex pattern '{pattern}': {e}")

        if matches_found > 0:
            # Normalize score based on matches and pattern specificity
            return min(total_weight / len(regex_patterns), 1.0)
        return 0.0

    async def _evaluate_learned_patterns(
        self,
        pattern_data: dict[str, Any],
        filename: str,
        email_subject: str,
        email_body: str,
    ) -> float:
        """Evaluate learned patterns from human feedback/auto-learning."""
        score = 0.0
        checks = 0

        # Check filename indicators
        filename_indicators = pattern_data.get("filename_indicators", [])
        if filename_indicators:
            checks += 1
            filename_lower = filename.lower()
            matches = sum(
                1 for indicator in filename_indicators if indicator in filename_lower
            )
            score += matches / len(filename_indicators)

        # Check subject indicators
        subject_indicators = pattern_data.get("subject_indicators", [])
        if subject_indicators:
            checks += 1
            subject_lower = email_subject.lower()
            matches = sum(
                1 for indicator in subject_indicators if indicator in subject_lower
            )
            score += matches / len(subject_indicators)

        # Check text patterns
        text_patterns = pattern_data.get("text_patterns", [])
        if text_patterns:
            checks += 1
            combined_text = f"{filename} {email_subject} {email_body}".lower()
            matches = sum(1 for pattern in text_patterns if pattern in combined_text)
            score += matches / len(text_patterns)

        return score / max(checks, 1) if checks > 0 else 0.0

    async def _evaluate_keyword_patterns(
        self, keywords: list[str], combined_text: str
    ) -> float:
        """Evaluate keyword patterns from asset matching."""
        if not keywords:
            return 0.0

        matches = 0
        for keyword in keywords:
            if keyword.lower() in combined_text:
                matches += 1
                self.logger.debug(f"Keyword match: '{keyword}'")

        return matches / len(keywords) if keywords else 0.0

    # Keep the old method for backward compatibility
    async def _evaluate_pattern_match(
        self,
        pattern_data: dict[str, Any],
        filename: str,
        email_subject: str,
        email_body: str,
    ) -> float:
        """Legacy method - delegates to new memory pattern evaluation."""
        combined_text = f"{filename} {email_subject} {email_body}".lower()
        return await self._evaluate_memory_pattern(
            pattern_data, combined_text, filename, email_subject, email_body
        )

    async def _store_pattern(
        self,
        pattern_type: PatternType,
        pattern_data: dict[str, Any],
        text_content: str,
        confidence: float,
        source: str,
    ) -> str:
        """Store a learned pattern in Qdrant."""
        # # Standard library imports
        import uuid

        pattern_id = str(uuid.uuid4())  # Use UUID instead of timestamp

        # TODO: Generate semantic embedding for text_content
        vector = [0.0] * 384  # Placeholder

        point = PointStruct(
            id=pattern_id,
            vector=vector,
            payload={
                "pattern_id": pattern_id,
                "pattern_type": pattern_type.value,
                "pattern_data": pattern_data,
                "confidence": confidence,
                "source": source,
                "success_count": 1,
                "failure_count": 0,
                "created_date": datetime.now(UTC).isoformat(),
                "last_used": datetime.now(UTC).isoformat(),
            },
        )

        collection_name = self.collections["classification_patterns"]
        if pattern_type == PatternType.ASSET_MATCHING:
            collection_name = self.collections["asset_patterns"]
        elif pattern_type == PatternType.CONFIGURATION:
            collection_name = self.collections["configuration_rules"]
        elif pattern_type in [
            PatternType.CONFIDENCE,
            PatternType.ROUTING,
            PatternType.VALIDATION,
        ]:
            collection_name = self.collections["confidence_models"]

        self.qdrant.upsert(collection_name=collection_name, points=[point])

        self.logger.info(f"📚 Stored {pattern_type.value} pattern: {pattern_id}")
        return pattern_id

    async def _store_procedural_pattern(self, pattern_dict: dict[str, Any]) -> str:
        """Store a procedural pattern directly from dictionary data."""
        # # Standard library imports
        import uuid

        pattern_id = str(uuid.uuid4())  # Use UUID instead of timestamp

        # TODO: Generate semantic embedding for pattern content
        vector = [0.0] * 384  # Placeholder

        point = PointStruct(
            id=pattern_id,
            vector=vector,
            payload={
                "pattern_id": pattern_id,
                "created_date": datetime.now(UTC).isoformat(),
                "last_used": datetime.now(UTC).isoformat(),
                **pattern_dict,  # Include all pattern data
            },
        )

        # Select appropriate collection based on pattern type
        pattern_type = pattern_dict["pattern_type"]
        collection_name = self.collections["classification_patterns"]  # Default

        # Handle both enum objects and string values
        pattern_type_str = (
            pattern_type.value if hasattr(pattern_type, "value") else pattern_type
        )

        if pattern_type_str == PatternType.ASSET_MATCHING.value:
            collection_name = self.collections["asset_patterns"]
        elif pattern_type_str == PatternType.CONFIGURATION.value:
            collection_name = self.collections["configuration_rules"]
        elif pattern_type_str in [
            PatternType.CONFIDENCE.value,
            PatternType.ROUTING.value,
            PatternType.VALIDATION.value,
        ]:
            collection_name = self.collections["confidence_models"]

        self.qdrant.upsert(collection_name=collection_name, points=[point])
        self.logger.debug(f"📚 Stored procedural pattern: {pattern_id}")
        return pattern_id

    async def _update_pattern_usage(self, pattern_id: str, success: bool):
        """Update pattern usage statistics."""
        # TODO: Implement pattern usage tracking
        pass

    async def _seed_initial_patterns(self):
        """Seed initial patterns if collections are empty."""
        # Check if we need to seed patterns
        classification_count = self.qdrant.count(
            collection_name=self.collections["classification_patterns"]
        )

        if classification_count.count == 0:
            self.logger.info("🌱 Seeding initial classification patterns")

            # Seed a few basic patterns to get started
            initial_patterns = [
                {
                    "filename": "rent_roll.xlsx",
                    "subject": "Monthly rent roll",
                    "body": "Attached is the monthly rent roll report",
                    "category": "rent_roll",
                    "asset_type": "commercial_real_estate",
                },
                {
                    "filename": "financial_statement.pdf",
                    "subject": "Q4 Financial Statement",
                    "body": "Please find attached the quarterly financial statement",
                    "category": "financial_statements",
                    "asset_type": "commercial_real_estate",
                },
            ]

            for pattern in initial_patterns:
                # Store pattern directly as stable business rule
                pattern_data = {
                    "pattern_type": PatternType.CLASSIFICATION,
                    "asset_type": pattern["asset_type"],
                    "document_category": pattern["category"],
                    "filename_indicators": [pattern["filename"].lower()],
                    "subject_indicators": pattern["subject"].lower().split(),
                    "keywords": pattern["body"].lower().split(),
                    "confidence_range": (0.8, 0.95),
                    "source": "initial_seed",
                    "metadata": {
                        "pattern_category": "bootstrap_seed",
                        "seeded_from": "initial_patterns",
                    },
                }
                await self._store_procedural_pattern(pattern_data)

    async def seed_from_knowledge_base(
        self, knowledge_path: str = "./knowledge/"
    ) -> dict[str, int]:
        """
        Seed procedural memory from structured knowledge base files.

        Loads classification patterns, asset keywords, business rules, and
        configurations from JSON files and stores them in vector memory.

        Args:
            knowledge_path: Path to directory containing knowledge JSON files

        Returns:
            Dictionary with counts of loaded patterns by type

        Raises:
            FileNotFoundError: If knowledge files are missing
            ValueError: If JSON format is invalid
        """
        knowledge_dir = Path(knowledge_path)
        if not knowledge_dir.exists():
            raise FileNotFoundError(f"Knowledge directory not found: {knowledge_path}")

        self.logger.info(
            "🌱 Seeding procedural memory from knowledge base: %s", knowledge_path
        )

        # Initialize collections if needed
        await self.initialize_collections()

        stats = {
            "classification_patterns": 0,
            "asset_keywords": 0,
            "asset_patterns": 0,
            "business_rules": 0,
            "asset_configs": 0,
            "total_patterns": 0,
        }

        try:
            # Load classification patterns
            patterns_file = knowledge_dir / "classification_patterns.json"
            if patterns_file.exists():
                stats[
                    "classification_patterns"
                ] = await self._seed_classification_patterns(patterns_file)
                self.logger.info(
                    "✅ Loaded %d classification patterns",
                    stats["classification_patterns"],
                )

            # Load asset keywords
            keywords_file = knowledge_dir / "asset_keywords.json"
            if keywords_file.exists():
                stats["asset_keywords"] = await self._seed_asset_keywords(keywords_file)
                self.logger.info(
                    "✅ Loaded %d asset keyword sets", stats["asset_keywords"]
                )

            # Load asset matching procedures
            asset_procedures_file = knowledge_dir / "asset_matching_procedures.json"
            if asset_procedures_file.exists():
                stats["asset_patterns"] = await self._seed_asset_procedures(
                    asset_procedures_file
                )
                self.logger.info(
                    "✅ Loaded %d asset matching procedures", stats["asset_patterns"]
                )

            # Load business rules
            rules_file = knowledge_dir / "business_rules.json"
            if rules_file.exists():
                stats["business_rules"] = await self._seed_business_rules(rules_file)
                self.logger.info("✅ Loaded %d business rules", stats["business_rules"])

            # Load asset configurations
            configs_file = knowledge_dir / "asset_configs.json"
            if configs_file.exists():
                stats["asset_configs"] = await self._seed_asset_configs(configs_file)
                self.logger.info(
                    "✅ Loaded %d asset configurations", stats["asset_configs"]
                )

            stats["total_patterns"] = sum(stats.values())

            self.logger.info(
                "🎉 Knowledge base seeding complete: %d total patterns loaded",
                stats["total_patterns"],
            )
            return stats

        except Exception as e:
            self.logger.error("❌ Failed to seed from knowledge base: %s", e)
            raise

    async def _seed_classification_patterns(self, patterns_file: Path) -> int:
        """Load classification patterns from JSON file into memory."""
        with open(patterns_file) as f:
            data = json.load(f)

        patterns_loaded = 0
        classification_patterns = data.get("classification_patterns", {})

        for asset_type, categories in classification_patterns.items():
            for category, patterns in categories.items():
                # Store the regex patterns directly as a structured pattern
                pattern_data = {
                    "pattern_type": PatternType.CLASSIFICATION,
                    "asset_type": asset_type,
                    "document_category": category,
                    "regex_patterns": patterns,  # Store the actual regex patterns
                    "confidence_range": [
                        0.7,
                        0.9,
                    ],  # Based on knowledge base usage notes
                    "source": "knowledge_base_seed",
                    "metadata": {
                        "pattern_category": "knowledge_base_classification",
                        "pattern_count": len(patterns),
                        "usage": "document classification via regex matching",
                        "matching_strategy": "combined filename + email_subject + email_body",
                        "extracted_from": "legacy asset_document_agent.py",
                    },
                }

                # Store directly without trying to extract patterns from fake emails
                await self._store_procedural_pattern(pattern_data)
                patterns_loaded += 1

                self.logger.debug(
                    "📚 Stored %s classification pattern for %s: %d regex patterns",
                    asset_type,
                    category,
                    len(patterns),
                )

        return patterns_loaded

    async def _seed_asset_keywords(self, keywords_file: Path) -> int:
        """Load asset keywords from JSON file into memory."""
        with open(keywords_file) as f:
            data = json.load(f)

        keywords_loaded = 0
        asset_keywords = data.get("asset_keywords", {})

        for asset_type, keywords in asset_keywords.items():
            # Store asset keywords as a procedural pattern
            await self._store_procedural_pattern(
                {
                    "pattern_type": PatternType.ASSET_MATCHING,
                    "asset_type": asset_type,
                    "keywords": keywords,
                    "confidence": 0.9,
                    "source": "knowledge_base_seed",
                    "metadata": {
                        "pattern_category": "asset_keywords",
                        "keyword_count": len(keywords),
                        "usage": "asset type identification from email content",
                    },
                }
            )
            keywords_loaded += 1

        return keywords_loaded

    async def _seed_asset_procedures(self, procedures_file: Path) -> int:
        """Load asset matching procedures from JSON file into memory."""
        with open(procedures_file) as f:
            data = json.load(f)

        procedures_loaded = 0

        # Load matching procedures
        matching_procedures = data.get("matching_procedures", [])
        for procedure in matching_procedures:
            procedure_dict = {
                "pattern_type": PatternType.ASSET_MATCHING,
                "procedure_name": procedure.get("procedure_name"),
                "procedure_type": procedure.get("procedure_type"),
                "description": procedure.get("description"),
                "algorithm": procedure.get("algorithm", {}),
                "source": "knowledge_base_seed",
                "metadata": {
                    "pattern_category": "asset_matching_procedure",
                    "algorithm_type": "procedural_logic",
                    "usage": "asset matching algorithm execution",
                },
            }

            await self._store_procedural_pattern(procedure_dict)
            procedures_loaded += 1

            self.logger.debug(
                "📚 Stored asset matching procedure: %s",
                procedure.get("procedure_name"),
            )

        # Load learning procedures
        learning_procedures = data.get("learning_procedures", [])
        for procedure in learning_procedures:
            procedure_dict = {
                "pattern_type": PatternType.ASSET_MATCHING,
                "procedure_name": procedure.get("procedure_name"),
                "procedure_type": procedure.get("procedure_type"),
                "description": procedure.get("description"),
                "algorithm": procedure.get("algorithm", {}),
                "source": "knowledge_base_seed",
                "metadata": {
                    "pattern_category": "learning_procedure",
                    "algorithm_type": "learning_logic",
                    "usage": "asset matching learning and improvement",
                },
            }

            await self._store_procedural_pattern(procedure_dict)
            procedures_loaded += 1

            self.logger.debug(
                "📚 Stored learning procedure: %s",
                procedure.get("procedure_name"),
            )

        return procedures_loaded

    async def _seed_business_rules(self, rules_file: Path) -> int:
        """Load business rules from JSON file into memory."""
        with open(rules_file) as f:
            data = json.load(f)

        rules_loaded = 0

        # Store confidence adjustment rules
        confidence_adjustments = data.get("confidence_adjustments", {})
        for rule_name, rule_config in confidence_adjustments.items():
            await self._store_procedural_pattern(
                {
                    "pattern_type": PatternType.CONFIDENCE,
                    "rule_name": rule_name,
                    "rule_config": rule_config,
                    "confidence": 1.0,
                    "source": "knowledge_base_seed",
                    "metadata": {
                        "pattern_category": "confidence_adjustment",
                        "boost_amount": rule_config.get("boost_amount", 0.0),
                    },
                }
            )
            rules_loaded += 1

        # Store routing decisions
        routing_decisions = data.get("routing_decisions", {})
        for confidence_level, routing_config in routing_decisions.items():
            await self._store_procedural_pattern(
                {
                    "pattern_type": PatternType.ROUTING,
                    "confidence_level": confidence_level,
                    "routing_config": routing_config,
                    "confidence": 1.0,
                    "source": "knowledge_base_seed",
                    "metadata": {
                        "pattern_category": "routing_decision",
                        "save_location": routing_config.get("save_location"),
                    },
                }
            )
            rules_loaded += 1

        return rules_loaded

    async def _seed_asset_configs(self, configs_file: Path) -> int:
        """Load asset configurations from JSON file into memory."""
        with open(configs_file) as f:
            data = json.load(f)

        configs_loaded = 0
        asset_configs = data.get("asset_configs", {})

        for asset_type, config in asset_configs.items():
            await self._store_procedural_pattern(
                {
                    "pattern_type": PatternType.VALIDATION,
                    "asset_type": asset_type,
                    "config": config,
                    "confidence": 1.0,
                    "source": "knowledge_base_seed",
                    "metadata": {
                        "pattern_category": "asset_configuration",
                        "allowed_extensions": config.get("allowed_extensions", []),
                        "max_file_size_mb": config.get("max_file_size_mb", 100),
                    },
                }
            )
            configs_loaded += 1

        return configs_loaded

    async def get_pattern_stats(self) -> dict[str, Any]:
        """
        Get statistics about loaded patterns in procedural memory.

        Returns:
            Dictionary with pattern counts and metadata
        """
        if not self.qdrant:
            return {"error": "Qdrant client not available"}

        try:
            # Get total count from classification patterns collection
            result = self.qdrant.count(
                collection_name=self.collections["classification_patterns"]
            )

            stats = {
                "total_patterns": result.count,
                "collection_name": self.collections["classification_patterns"],
                "memory_available": True,
                "last_updated": datetime.now(UTC).isoformat(),
            }

            # Get pattern breakdown by source if possible
            try:
                # Count patterns from knowledge base vs learned patterns
                search_result = self.qdrant.scroll(
                    collection_name=self.collections["classification_patterns"],
                    limit=1000,  # Adjust based on expected pattern count
                    with_payload=True,
                )

                source_counts = {}
                pattern_types = {}

                for point in search_result[0]:
                    source = point.payload.get("source", "unknown")
                    pattern_type = point.payload.get("pattern_type", "unknown")

                    source_counts[source] = source_counts.get(source, 0) + 1
                    pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1

                stats["by_source"] = source_counts
                stats["by_type"] = pattern_types

            except Exception as e:
                self.logger.warning("Could not get detailed pattern breakdown: %s", e)

            return stats

        except Exception as e:
            self.logger.error("Failed to get pattern statistics: %s", e)
            return {"error": str(e)}

    async def export_learned_patterns(
        self, export_path: str = "./knowledge_export/"
    ) -> dict[str, str]:
        """
        Export learned patterns back to JSON files for version control.

        This allows you to capture patterns learned from human feedback
        and successful processing, creating an updated knowledge base.

        Args:
            export_path: Directory to export updated knowledge files

        Returns:
            Dictionary with paths to exported files
        """
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("📤 Exporting learned patterns to: %s", export_path)

        exported_files = {}

        try:
            if not self.qdrant:
                raise ValueError("Qdrant client not available for export")

            # Export all patterns
            search_result = self.qdrant.scroll(
                collection_name=self.collections["classification_patterns"],
                limit=10000,  # Adjust based on expected pattern count
                with_payload=True,
            )

            # Organize patterns by type
            classification_patterns = {}

            for point in search_result[0]:
                payload = point.payload
                pattern_type = payload.get("pattern_type", "unknown")

                if pattern_type == PatternType.CLASSIFICATION.value:
                    # Group by asset type and category
                    asset_type = payload.get("asset_type", "unknown")
                    category = payload.get("predicted_category", "unknown")

                    if asset_type not in classification_patterns:
                        classification_patterns[asset_type] = {}
                    if category not in classification_patterns[asset_type]:
                        classification_patterns[asset_type][category] = []

                    # Extract the pattern (could be from email_body or a specific pattern field)
                    pattern = payload.get("email_body", payload.get("pattern", ""))
                    if pattern:
                        classification_patterns[asset_type][category].append(pattern)

            # Export classification patterns
            if classification_patterns:
                patterns_export = {
                    "metadata": {
                        "description": "Updated classification patterns including learned patterns",
                        "version": "2.0.0",
                        "exported_date": datetime.now(UTC).isoformat(),
                        "source": "procedural_memory_export",
                    },
                    "classification_patterns": classification_patterns,
                }

                patterns_file = export_dir / "classification_patterns_updated.json"
                with open(patterns_file, "w") as f:
                    json.dump(patterns_export, f, indent=2)

                exported_files["classification_patterns"] = str(patterns_file)
                self.logger.info(
                    "✅ Exported classification patterns to: %s", patterns_file
                )

            return exported_files

        except Exception as e:
            self.logger.error("❌ Failed to export learned patterns: %s", e)
            raise

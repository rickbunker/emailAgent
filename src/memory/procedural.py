"""
Procedural Memory System for Asset Document Agent

Replaces hardcoded patterns, rules, and configurations with learned knowledge
stored in vector memory. The agent learns from successful classifications,
human feedback, and processing outcomes.

Key Features:
    - Dynamic pattern learning from examples
    - Adaptive confidence thresholds
    - Semantic similarity-based classification
    - Human feedback integration
    - Configuration optimization

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
from .episodic import EpisodicMemory


class PatternType(Enum):
    """Types of learned patterns"""

    CLASSIFICATION = "classification"  # Document classification patterns
    ASSET_MATCHING = "asset_matching"  # Asset identification patterns
    CONFIGURATION = "configuration"  # Learned configuration rules
    CONFIDENCE = "confidence"  # Confidence scoring patterns
    ROUTING = "routing"  # Document routing patterns
    VALIDATION = "validation"  # File validation patterns


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
class LearnedPattern:
    """A pattern learned from successful processing"""

    pattern_id: str
    pattern_type: PatternType
    pattern_data: dict[str, Any]
    success_count: int
    failure_count: int
    confidence: float
    last_used: datetime
    created_date: datetime
    source: str  # "human_feedback", "auto_learning", "initial_seed"


class ProceduralMemory:
    """
    Procedural memory system that learns and stores processing patterns.

    Replaces hardcoded rules with learned knowledge from successful
    document processing and human feedback.
    """

    def __init__(self, qdrant_client: QdrantClient):
        """Initialize procedural memory system."""
        self.logger = get_logger(f"{__name__}.ProceduralMemory")
        self.qdrant = qdrant_client
        self.episodic = EpisodicMemory()

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
    async def learn_classification_pattern(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        document_category: str,
        asset_type: str,
        confidence: float,
        source: str = "auto_learning",
    ) -> str:
        """
        Learn a new classification pattern from successful classification.

        Args:
            filename: Document filename
            email_subject: Email subject line
            email_body: Email body content
            document_category: Classified category
            asset_type: Asset type context
            confidence: Classification confidence
            source: Learning source (auto_learning, human_feedback)

        Returns:
            Pattern ID
        """
        self.logger.info(
            f"🧠 Learning classification pattern: {document_category} ({confidence:.3f})"
        )

        # Extract meaningful phrases from text
        combined_text = f"{filename} {email_subject} {email_body}".lower()
        patterns = await self._extract_patterns(combined_text, document_category)

        # Create learned pattern
        pattern_data = {
            "document_category": document_category,
            "asset_type": asset_type,
            "text_patterns": patterns,
            "filename_indicators": self._extract_filename_indicators(filename),
            "subject_indicators": self._extract_subject_indicators(email_subject),
            "confidence_range": (confidence - 0.1, confidence + 0.1),
        }

        pattern_id = await self._store_pattern(
            PatternType.CLASSIFICATION, pattern_data, combined_text, confidence, source
        )

        # Store in procedural memory only - this is a learned rule/pattern
        # Episodic memory is for individual experiences, not learned rules
        self.logger.info(f"📚 Learned classification pattern: {pattern_id}")

        return pattern_id

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
                    pattern_data = payload.get("pattern_data", {})
                    category = pattern_data.get("document_category", "unknown")

                    if category == "unknown":
                        continue

                    patterns_evaluated += 1

                    # Evaluate this memory pattern against current document
                    match_score = await self._evaluate_memory_pattern(
                        pattern_data, combined_text, filename, email_subject, email_body
                    )

                    # Apply asset type context weighting
                    pattern_asset_type = pattern_data.get("asset_type", "")
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
                                "pattern_type": pattern_data.get(
                                    "pattern_type", "classification"
                                ),
                                "regex_patterns": pattern_data.get(
                                    "regex_patterns", []
                                ),
                                "keywords": pattern_data.get("keywords", []),
                                "filename_indicators": pattern_data.get(
                                    "filename_indicators", []
                                ),
                                "subject_indicators": pattern_data.get(
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
        Classify document using memory-driven patterns (no hardcoded rules).

        Args:
            filename: Document filename
            email_subject: Email subject
            email_body: Email body content
            asset_type: Asset type context for filtering

        Returns:
            Tuple of (document_category, confidence)
        """
        self.logger.info("🔍 Memory-driven document classification")

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
                return "unknown", 0.0

            patterns = scroll_result[0]
            combined_text = f"{filename} {email_subject} {email_body}".lower()

            # Vote-based classification using all stored patterns
            category_votes: dict[str, list[float]] = {}
            patterns_evaluated = 0

            for point in patterns:
                try:
                    payload = point.payload
                    pattern_data = payload.get("pattern_data", {})
                    category = pattern_data.get("document_category", "unknown")

                    if category == "unknown":
                        continue

                    patterns_evaluated += 1

                    # Evaluate this memory pattern against current document
                    match_score = await self._evaluate_memory_pattern(
                        pattern_data, combined_text, filename, email_subject, email_body
                    )

                    # Apply asset type context weighting
                    pattern_asset_type = pattern_data.get("asset_type", "")
                    if asset_type and pattern_asset_type:
                        if pattern_asset_type == asset_type:
                            match_score *= 1.2  # Boost for matching asset type
                        else:
                            match_score *= 0.8  # Reduce for non-matching asset type

                    if match_score > 0.1:  # Only consider meaningful matches
                        if category not in category_votes:
                            category_votes[category] = []
                        category_votes[category].append(match_score)

                        self.logger.debug(
                            f"Pattern vote: {category} = {match_score:.3f}"
                        )

                except Exception as e:
                    self.logger.debug(f"Error evaluating pattern: {e}")
                    continue

            if not category_votes:
                self.logger.info(
                    f"No pattern matches from {patterns_evaluated} patterns"
                )
                return "unknown", 0.0

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

            self.logger.info(
                f"Memory classification: {best_category} ({best_confidence:.3f}) "
                f"from {len(category_votes)} categories, {patterns_evaluated} patterns"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Memory-driven classification failed: {e}")
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
                await self.learn_classification_pattern(
                    pattern["filename"],
                    pattern["subject"],
                    pattern["body"],
                    pattern["category"],
                    pattern["asset_type"],
                    0.9,
                    "initial_seed",
                )

    @log_function()
    async def learn_from_human_feedback(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        system_prediction: str,
        human_correction: str,
        asset_type: str,
    ) -> str:
        """
        Learn from human feedback to improve classification patterns.

        This is the key method for improving the agent's procedural knowledge.
        """
        self.logger.info(
            f"👨‍🏫 Learning from human feedback: {system_prediction} -> {human_correction}"
        )

        # Store the corrected pattern with high confidence
        pattern_id = await self.learn_classification_pattern(
            filename,
            email_subject,
            email_body,
            human_correction,
            asset_type,
            0.95,  # High confidence for human corrections
            "human_feedback",
        )

        # Store feedback in episodic memory (this IS an individual experience)
        await self.episodic.add_feedback(
            f"Classification correction: {filename}",
            {
                "system_prediction": system_prediction,
                "human_correction": human_correction,
                "feedback_type": "correction",
                "pattern_id": pattern_id,
                "filename": filename,
                "email_subject": email_subject,
                "asset_type": asset_type,
            },
        )

        return pattern_id

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
                stats["classification_patterns"] = (
                    await self._seed_classification_patterns(patterns_file)
                )
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

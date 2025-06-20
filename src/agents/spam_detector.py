"""
Spam Detection Agent for Email Document Management

A hybrid spam detection system designed for private market asset
management users who need reliable email filtering without false positives
that could block important business communications.

Architecture:
    The system combines multiple detection layers:
    1. Apache SpamAssassin for industry-standard spam scoring
    2. External blacklist checking against known malicious sources
    3. content analysis using pattern recognition
    4. Contact-aware filtering (trusted contacts get preferential treatment)
    5. Machine learning from user feedback for continuous improvement

Key Features:
    - Multi-layered detection for high accuracy and low false positives
    - Integration with contact memory to protect known relationships
    - Learning system that improves based on user feedback
    - Real-time blacklist checking against major RBLs
    - Confidence scoring with detailed reasoning
    - Complete logging for audit trails and debugging
    - Async architecture for high-performance processing

Detection Methods:
    - SpamAssassin integration with configurable thresholds
    - DNS blacklist checking (Spamhaus, SpamCop, SORBS, etc.)
    - Content pattern analysis for phishing and bulk indicators
    - Authentication header validation (SPF, DKIM, DMARC)
    - Sender reputation tracking and learning
    - Link analysis for suspicious URLs

Business Context:
    Designed for finance users who cannot afford to miss important
    emails from clients, counterparties, or regulators. Emphasis on minimizing
    false positives while maintaining strong protection against threats.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import asyncio
import os
import re
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List

# External dependencies (install with pip if needed)
try:
    # # Third-party imports
    import dns.resolver
    import requests
except ImportError:
    # Graceful degradation if optional dependencies not available
    requests = None
    dns = None

# # Standard library imports
# Memory system integration
# Logging system integration
import sys

from ..memory.contact import ContactMemory
from ..memory.episodic import EpisodicMemory
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory, KnowledgeType, KnowledgeConfidence

# SpamAssassin integration
from ..tools.spamassassin_integration import SpamAssassinIntegration

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function

# Initialize logger
logger = get_logger(__name__)


@dataclass
class EmailMessage:
    """
    Email message data structure for spam analysis.

    Represents an email message with all necessary information for
    complete spam detection analysis.

    Attributes:
        id: Unique identifier for the email
        sender: Email address of the sender
        subject: Email subject line
        content: Email body content (text or HTML)
        headers: Complete email headers dictionary
        received_date: When the email was received
        size: Email size in bytes
        attachments: List of attachment filenames
    """

    id: str
    sender: str
    subject: str
    content: str
    headers: dict[str, str] = field(default_factory=dict)
    received_date: datetime | None = None
    size: int | None = None
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate email data after initialization."""
        if not self.id:
            raise ValueError("Email ID cannot be empty")
        if not self.sender or "@" not in self.sender:
            raise ValueError(f"Invalid sender email: {self.sender}")
        if self.size is not None and self.size < 0:
            raise ValueError("Email size cannot be negative")


class SpamConfidence(Enum):
    """
    Confidence levels for spam detection with precise thresholds.

    These levels help downstream systems make appropriate decisions
    about email handling (block, quarantine, deliver with warning, etc.).
    """

    DEFINITELY_SPAM = "definitely_spam"  # 90%+ confidence - safe to block
    LIKELY_SPAM = "likely_spam"  # 70-90% confidence - quarantine
    SUSPICIOUS = "suspicious"  # 40-70% confidence - flag for review
    UNCERTAIN = "uncertain"  # 20-40% confidence - deliver with caution
    LIKELY_CLEAN = "likely_clean"  # 5-20% confidence - deliver normally
    DEFINITELY_CLEAN = "definitely_clean"  # <5% confidence - whitelist


class SpamReason(Enum):
    """
    Specific reasons why an email was flagged as spam.

    Provides detailed explanations for spam classification decisions,
    useful for user feedback and system tuning.
    """

    SPAMASSASSIN_HIGH_SCORE = "spamassassin_high_score"
    BLACKLISTED_IP = "blacklisted_ip"
    BLACKLISTED_DOMAIN = "blacklisted_domain"
    SUSPICIOUS_CONTENT = "suspicious_content"
    KNOWN_SPAM_PATTERN = "known_spam_pattern"
    NO_AUTHENTICATION = "no_authentication"
    BULK_SENDER = "bulk_sender"
    USER_PREVIOUS_SPAM = "user_previous_spam"
    SUSPICIOUS_LINKS = "suspicious_links"
    PHISHING_INDICATORS = "phishing_indicators"
    MALICIOUS_ATTACHMENT = "malicious_attachment"
    REPUTATION_POOR = "reputation_poor"


@dataclass
class SpamAnalysis:
    """
    Complete results of spam analysis with detailed metrics.

    Contains all information about why an email was classified as spam
    or clean, including confidence levels, specific reasons, and
    actionable recommendations.

    Attributes:
        is_spam: Boolean classification result
        confidence: Confidence level enum
        spam_score: Numeric score (0-100, higher = more likely spam)
        spamassassin_score: SpamAssassin-specific score
        reasons: List of specific reasons for classification
        blacklist_hits: List of blacklists that flagged this email
        content_flags: List of content-based warning flags
        recommendation: Suggested action for this email
        details: Additional analysis details and metadata
        processing_time: Time taken for analysis (seconds)
    """

    is_spam: bool
    confidence: SpamConfidence
    spam_score: float  # 0-100 scale
    spamassassin_score: float | None = None
    reasons: list[SpamReason] = field(default_factory=list)
    blacklist_hits: list[str] = field(default_factory=list)
    content_flags: list[str] = field(default_factory=list)
    recommendation: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0

    def __post_init__(self) -> None:
        """Validate spam analysis data after initialization."""
        if not 0.0 <= self.spam_score <= 100.0:
            raise ValueError(f"Spam score must be 0-100, got {self.spam_score}")
        if self.processing_time < 0:
            raise ValueError("Processing time cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage or serialization."""
        return {
            "is_spam": self.is_spam,
            "confidence": self.confidence.value,
            "spam_score": self.spam_score,
            "spamassassin_score": self.spamassassin_score,
            "reasons": [r.value for r in self.reasons],
            "blacklist_hits": self.blacklist_hits,
            "content_flags": self.content_flags,
            "recommendation": self.recommendation,
            "details": self.details,
            "processing_time": self.processing_time,
        }


class SpamDetector:
    """
    Hybrid spam detection agent with business capabilities.

    Combines multiple detection methods and integrates with memory systems
    to provide intelligent, learning-based spam filtering suitable for
    business environments where false positives are costly.

    The detector uses a layered approach:
    1. Check trusted contacts first (whitelist)
    2. Check known spam senders (blacklist)
    3. Run SpamAssassin analysis
    4. Check external blacklists
    5. Analyze content patterns
    6. Apply learned rules and patterns

    Attributes:
        procedural_memory: Stores spam detection rules and procedures
        semantic_memory: Stores knowledge about senders and patterns
        episodic_memory: Stores analysis history and user feedback
        contact_memory: Stores trusted contact information
        spamassassin: SpamAssassin integration for core detection
    """

    def __init__(self, spamassassin_threshold: float = 5.0) -> None:
        """
        Initialize the spam detection agent.

        Args:
            spamassassin_threshold: SpamAssassin score threshold for spam
        """
        # Initialize memory systems with config-based limits
        try:
            # For ProceduralMemory, create a minimal client for spam detection patterns
            # # Third-party imports
            from qdrant_client import QdrantClient

            # SpamDetector uses procedural memory for spam detection patterns
            mock_client = QdrantClient(
                ":memory:"
            )  # In-memory client for basic functionality
            self.procedural_memory = ProceduralMemory(mock_client)
        except Exception:
            # If Qdrant is not available, spam detector can work with other memory types
            self.procedural_memory = None

        self.semantic_memory = (
            SemanticMemory()
        )  # Uses config.semantic_memory_max_items automatically
        self.episodic_memory = EpisodicMemory()
        self.contact_memory = (
            ContactMemory()
        )  # Uses config.contact_memory_max_items automatically

        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing Spam Detection Agent")

        # Initialize semantic memory for spam patterns
        self.semantic_memory = SemanticMemory()

        # Load spam patterns from memory instead of hardcoding
        self.spam_patterns: Dict[str, Any] = {
            "keywords": [],
            "regex_patterns": [],
            "phishing_patterns": [],
            "blacklists": [],
            "tlds": [],
            "learning_config": {},
        }

        # Load patterns asynchronously (will be populated on first use)
        self._patterns_loaded = False
        self.logger.info("Spam patterns will be loaded from memory on first use")

        # Initialize SpamAssassin integration
        try:
            self.spamassassin = SpamAssassinIntegration(
                threshold=spamassassin_threshold
            )
            self.logger.info(
                f"SpamAssassin initialized with threshold {spamassassin_threshold}"
            )
        except Exception as e:
            self.logger.warning(f"SpamAssassin initialization failed: {e}")
            self.spamassassin = None

        self.logger.info("Spam Detection Agent initialized successfully")

    def _parse_confidence(self, confidence: Any) -> float:
        """
        Parse confidence value that might be string or numeric.

        Args:
            confidence: Confidence value (string like 'high', 'medium' or numeric)

        Returns:
            Numeric confidence value
        """
        if isinstance(confidence, (int, float)):
            return float(confidence)

        # Map string confidence to numeric values
        confidence_map = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3,
            "very_high": 0.9,
            "very_low": 0.1,
        }

        if isinstance(confidence, str):
            return confidence_map.get(confidence.lower(), 0.5)

        return 0.5  # Default

    @log_function()
    async def _ensure_patterns_loaded(self) -> None:
        """Ensure spam patterns are loaded from memory."""
        if self._patterns_loaded:
            return

        await self._load_spam_patterns_from_memory()
        self._patterns_loaded = True

    @log_function()
    async def _load_spam_patterns_from_memory(self) -> None:
        """
        Load spam patterns from semantic memory.

        Searches semantic memory for spam patterns and organizes them
        by type for efficient use during analysis.
        """
        self.logger.info("Loading spam patterns from semantic memory")

        try:
            # Search for all spam patterns
            pattern_results = await self.semantic_memory.search(
                query="spam pattern", limit=200, knowledge_type=KnowledgeType.PATTERN
            )

            patterns_by_type = {
                "keywords": [],
                "regex_patterns": [],
                "phishing_patterns": [],
                "blacklists": [],
                "domain_blacklists": [],
                "tlds": [],
            }

            for item in pattern_results:
                metadata = item.metadata
                pattern_type = metadata.get("pattern_type", "unknown")

                if pattern_type == "keyword":
                    patterns_by_type["keywords"].append(
                        {
                            "word": metadata.get("word", ""),
                            "confidence": self._parse_confidence(
                                metadata.get("confidence", 0.5)
                            ),
                            "weight": metadata.get("weight", 2.0),
                            "category": metadata.get("category", "spam"),
                        }
                    )
                elif pattern_type == "regex":
                    if metadata.get("category") == "phishing":
                        patterns_by_type["phishing_patterns"].append(
                            {
                                "regex": metadata.get("regex", ""),
                                "confidence": self._parse_confidence(
                                    metadata.get("confidence", 0.5)
                                ),
                                "weight": metadata.get("weight", 1.5),
                                "description": metadata.get("description", ""),
                            }
                        )
                    else:
                        patterns_by_type["regex_patterns"].append(
                            {
                                "regex": metadata.get("regex", ""),
                                "confidence": self._parse_confidence(
                                    metadata.get("confidence", 0.5)
                                ),
                                "weight": metadata.get("weight", 1.5),
                                "description": metadata.get("description", ""),
                            }
                        )
                elif pattern_type == "blacklist":
                    if metadata.get("blacklist_type") == "domain":
                        patterns_by_type["domain_blacklists"].append(
                            {
                                "server": metadata.get("server", ""),
                                "weight": metadata.get("weight", 0.8),
                            }
                        )
                    else:
                        patterns_by_type["blacklists"].append(
                            {
                                "server": metadata.get("server", ""),
                                "weight": metadata.get("weight", 0.8),
                            }
                        )
                elif pattern_type == "tld":
                    patterns_by_type["tlds"].append(
                        {
                            "tld": metadata.get("tld", ""),
                            "confidence": self._parse_confidence(
                                metadata.get("confidence", 0.5)
                            ),
                            "description": metadata.get("description", ""),
                        }
                    )

            # Search for learning configuration
            config_results = await self.semantic_memory.search(
                query="spam learning configuration",
                limit=1,
                knowledge_type=KnowledgeType.PROCESS,
            )

            if config_results:
                config_metadata = config_results[0].metadata
                self.spam_patterns["learning_config"] = config_metadata.get(
                    "configuration", {}
                )

            # Update patterns
            self.spam_patterns.update(patterns_by_type)

            self.logger.info(f"Loaded spam patterns from memory:")
            self.logger.info(f"  Keywords: {len(self.spam_patterns['keywords'])}")
            self.logger.info(
                f"  Regex patterns: {len(self.spam_patterns['regex_patterns'])}"
            )
            self.logger.info(
                f"  Phishing patterns: {len(self.spam_patterns['phishing_patterns'])}"
            )
            self.logger.info(f"  Blacklists: {len(self.spam_patterns['blacklists'])}")
            self.logger.info(
                f"  Domain blacklists: {len(self.spam_patterns['domain_blacklists'])}"
            )
            self.logger.info(f"  Suspicious TLDs: {len(self.spam_patterns['tlds'])}")

        except Exception as e:
            self.logger.error(f"Failed to load spam patterns from memory: {e}")
            # Fall back to empty patterns rather than crash
            self.logger.warning("Using empty spam patterns as fallback")

    @log_function()
    async def analyze_spam(self, email: EmailMessage) -> SpamAnalysis:
        """
        Main entry point for complete spam analysis.

        Performs multi-layered analysis to determine if an email is spam,
        including confidence scoring and detailed reasoning.

        Args:
            email: Email message to analyze

        Returns:
            Complete SpamAnalysis with classification and details

        Raises:
            ValueError: If email data is invalid
        """
        start_time = datetime.now()
        self.logger.info(f"Analyzing spam for email from {email.sender}")

        # Ensure spam patterns are loaded from memory
        await self._ensure_patterns_loaded()

        try:
            # Initialize analysis with defaults
            analysis = SpamAnalysis(
                is_spam=False, confidence=SpamConfidence.LIKELY_CLEAN, spam_score=0.0
            )

            # Step 1: Check if sender is a trusted contact (high priority)
            trusted_contact = await self._check_trusted_contact(email.sender)
            if trusted_contact:
                analysis.spam_score -= 30  # Significant trust bonus
                analysis.details["trusted_contact"] = trusted_contact
                self.logger.info(f"Trusted contact detected: {trusted_contact}")

            # Step 2: Check spam history for this sender
            spam_history = await self._check_spam_history(email.sender)
            if spam_history:
                analysis.spam_score += 50
                analysis.reasons.append(SpamReason.USER_PREVIOUS_SPAM)
                analysis.details["spam_history"] = spam_history
                self.logger.warning(f"Previous spam detected from {email.sender}")

            # Step 3: Run SpamAssassin analysis if available
            if self.spamassassin:
                sa_result = await self._run_spamassassin(email)
                if sa_result is not None:
                    sa_score, sa_details = sa_result
                    analysis.spamassassin_score = sa_score
                    analysis.spam_score += sa_score * 2  # Weight SpamAssassin results
                    analysis.details["spamassassin_details"] = sa_details
                    if sa_score >= self.spamassassin.threshold:
                        analysis.reasons.append(SpamReason.SPAMASSASSIN_HIGH_SCORE)
                    self.logger.debug(f"SpamAssassin score: {sa_score}")
            else:
                self.logger.debug("SpamAssassin not available, skipping")

            # Step 4: Check sender IP/domain against blacklists
            blacklist_results = await self._check_blacklists(email.sender)
            if blacklist_results:
                analysis.blacklist_hits.extend(blacklist_results)
                analysis.spam_score += (
                    len(blacklist_results) * 20
                )  # Significant penalty

                # Categorize by type of blacklist hit
                domain_hits = [
                    hit for hit in blacklist_results if "domain" in hit.lower()
                ]
                ip_hits = [hit for hit in blacklist_results if hit not in domain_hits]

                if domain_hits:
                    analysis.reasons.append(SpamReason.BLACKLISTED_DOMAIN)
                if ip_hits:
                    analysis.reasons.append(SpamReason.BLACKLISTED_IP)

                self.logger.warning(f"Blacklist hits: {len(blacklist_results)}")

            # Step 5: Analyze email content
            content_score, content_flags, matched_patterns = self._analyze_content(
                email
            )
            analysis.spam_score += content_score
            analysis.content_flags.extend(content_flags)
            analysis.details["patterns_matched"] = matched_patterns

            if content_score > 20:
                analysis.reasons.append(SpamReason.SUSPICIOUS_CONTENT)

            # Step 6: Check for phishing indicators
            phishing_score = self._check_phishing_indicators(email)
            if phishing_score > 15:
                analysis.spam_score += phishing_score
                analysis.reasons.append(SpamReason.PHISHING_INDICATORS)
                analysis.content_flags.append("phishing_patterns")

            # Step 7: Check email authentication
            auth_score = self._check_authentication(email)
            analysis.spam_score += auth_score
            if auth_score > 10:
                analysis.reasons.append(SpamReason.NO_AUTHENTICATION)

            # Step 8: Apply learned spam rules from memory
            rules_score = await self._apply_spam_rules(email, analysis)
            analysis.spam_score += rules_score

            # Step 9: Classify final spam score and set confidence
            analysis = self._classify_spam_score(analysis)

            # Step 10: Store analysis for learning
            await self._store_spam_analysis(email, analysis)

            # Calculate processing time
            end_time = datetime.now()
            analysis.processing_time = (end_time - start_time).total_seconds()

            self.logger.info(
                f"Spam analysis complete: {analysis.confidence.value} "
                f"(score: {analysis.spam_score:.1f}, time: {analysis.processing_time:.3f}s)"
            )

            self.logger.info("📊 Analysis Results:")
            self.logger.info(
                f"   Classification: {'SPAM' if analysis.is_spam else 'CLEAN'}"
            )
            self.logger.info(f"   Confidence: {analysis.confidence.value}")
            self.logger.info(f"   Spam Score: {analysis.spam_score:.1f}/100")
            self.logger.info(f"   Recommendation: {analysis.recommendation}")

            if analysis.reasons:
                self.logger.info(
                    f"   Reasons: {', '.join([r.value for r in analysis.reasons])}"
                )

            if analysis.blacklist_hits:
                self.logger.info(
                    f"   Blacklist Hits: {', '.join(analysis.blacklist_hits)}"
                )

            if analysis.content_flags:
                self.logger.info(
                    f"   Content Flags: {', '.join(analysis.content_flags)}"
                )

            self.logger.info(f"   Processing Time: {analysis.processing_time:.3f}s")

            return analysis

        except Exception as e:
            self.logger.error(f"Spam analysis failed for {email.sender}: {e}")
            # Return safe default
            return SpamAnalysis(
                is_spam=False,
                confidence=SpamConfidence.UNCERTAIN,
                spam_score=50.0,
                recommendation="Analysis failed - manual review recommended",
                details={"error": str(e)},
                processing_time=(datetime.now() - start_time).total_seconds(),
            )

    @log_function()
    async def _check_trusted_contact(self, sender_email: str) -> str | None:
        """
        Check if the sender is a known trusted contact.

        Searches contact memory for the sender and returns trust information.

        Args:
            sender_email: Email address to check

        Returns:
            Trust level string or None if not found
        """
        try:
            # Search contact memory for this sender
            search_results = await self.contact_memory.search(
                query=sender_email, limit=1
            )

            if search_results:
                memory_item, score = search_results[0]
                if score > 0.8:  # High confidence match
                    contact_data = memory_item.metadata
                    confidence = contact_data.get("confidence", "unknown")
                    contact_type = contact_data.get("contact_type", "unknown")

                    # Return trust information
                    if confidence in ["high", "medium"] and contact_type != "vendor":
                        return f"{contact_type}_{confidence}"

            return None

        except Exception as e:
            self.logger.warning(
                f"Failed to check trusted contact for {sender_email}: {e}"
            )
            return None

    @log_function()
    async def _check_spam_history(self, sender_email: str) -> dict[str, Any] | None:
        """
        Check if this sender has been marked as spam before.

        Searches episodic memory for previous spam classifications.

        Args:
            sender_email: Email address to check

        Returns:
            Dictionary with spam history or None if clean
        """
        try:
            # Search episodic memory for spam classifications
            search_results = await self.episodic_memory.search(
                query=f"spam {sender_email}", limit=3
            )

            spam_count = 0
            recent_spam = False

            for memory_item, score in search_results:
                if score > 0.7:  # Good match
                    metadata = memory_item.metadata
                    if metadata.get("classification") == "spam":
                        spam_count += 1

                        # Check if recent (last 30 days)
                        classification_date = metadata.get("date")
                        if classification_date:
                            try:
                                class_dt = datetime.fromisoformat(
                                    classification_date.replace("Z", "+00:00")
                                )
                                days_ago = (datetime.now(UTC) - class_dt).days
                                if days_ago <= 30:
                                    recent_spam = True
                            except (ValueError, TypeError):
                                pass

            if spam_count > 0:
                return {
                    "spam_count": spam_count,
                    "recent_spam": recent_spam,
                    "sender": sender_email,
                }

            return None

        except Exception as e:
            self.logger.warning(f"Failed to check spam history for {sender_email}: {e}")
            return None

    @log_function()
    async def _run_spamassassin(self, email: EmailMessage) -> tuple[float, str] | None:
        """
        Run SpamAssassin analysis on the email.

        Args:
            email: Email to analyze

        Returns:
            Tuple of (score, details) or None if analysis fails
        """
        if not self.spamassassin:
            return None

        try:
            # Create temporary file with email content
            email_content = f"From: {email.sender}\n"
            email_content += f"Subject: {email.subject}\n"
            for header, value in email.headers.items():
                email_content += f"{header}: {value}\n"
            email_content += f"\n{email.content}"

            # Run SpamAssassin analysis
            result = await self.spamassassin.check_spam(email_content)

            if result:
                return (result["score"], result.get("summary", ""))

            return None

        except Exception as e:
            self.logger.warning(f"SpamAssassin analysis failed: {e}")
            return None

    @log_function()
    async def _check_blacklists(self, sender_email: str) -> list[str]:
        """
        Check sender against DNS blacklists.

        Args:
            sender_email: Email address to check

        Returns:
            List of blacklist names that flagged this sender
        """
        if not dns:
            self.logger.debug("DNS module not available, skipping blacklist check")
            return []

        hits = []
        domain = sender_email.split("@")[1] if "@" in sender_email else sender_email

        try:
            # Get IP address for domain
            try:
                ip_result = socket.gethostbyname(domain)
                ip_parts = ip_result.split(".")
                reversed_ip = ".".join(reversed(ip_parts))
            except socket.gaierror:
                self.logger.debug(f"Could not resolve IP for domain {domain}")
                return hits

            # Ensure patterns are loaded
            if not self._patterns_loaded:
                await self._ensure_patterns_loaded()

            # Check each blacklist
            for blacklist in self.spam_patterns.get("blacklists", []):
                try:
                    query = f"{reversed_ip}.{blacklist['server']}"
                    result = dns.resolver.resolve(query, "A")

                    # If we get a result, the IP is blacklisted
                    if result:
                        hits.append(f"{blacklist['server']} (IP: {ip_result})")
                        self.logger.debug(
                            f"Blacklist hit: {blacklist['server']} for IP {ip_result}"
                        )

                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    # Not found in this blacklist (good)
                    continue
                except Exception as e:
                    self.logger.debug(
                        f"Blacklist check failed for {blacklist['server']}: {e}"
                    )
                    continue

            # Also check domain-based blacklists
            for blacklist in self.spam_patterns.get("domain_blacklists", []):
                try:
                    query = f"{domain}.{blacklist['server']}"
                    result = dns.resolver.resolve(query, "A")
                    if result:
                        hits.append(f"{blacklist['server']} (domain: {domain})")
                        self.logger.debug(
                            f"Domain blacklist hit: {blacklist['server']} for {domain}"
                        )

                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    continue
                except Exception as e:
                    self.logger.debug(
                        f"Domain blacklist check failed for {blacklist['server']}: {e}"
                    )
                    continue

            return hits

        except Exception as e:
            self.logger.warning(f"Blacklist checking failed: {e}")
            return []

    @log_function()
    def _analyze_content(
        self, email: EmailMessage
    ) -> tuple[float, list[str], list[dict]]:
        """
        Analyze email content for spam indicators.

        Args:
            email: Email to analyze

        Returns:
            Tuple of (spam_score_increase, content_flags, matched_patterns)
        """
        content = f"{email.subject} {email.content}".lower()
        flags = []
        score = 0.0
        matched_patterns = []

        # Check for spam words
        spam_word_count = 0
        for word in self.spam_patterns.get("keywords", []):
            if word["word"] in content:
                spam_word_count += 1
                score += word.get("weight", 2.0) * word.get("confidence", 0.5)
                matched_patterns.append(
                    {"type": "keyword", "id": word["word"], "pattern": word}
                )

        if spam_word_count > 3:
            flags.append(f"spam_words_{spam_word_count}")

        # Check for suspicious patterns
        pattern_count = 0
        for pattern in self.spam_patterns.get("regex_patterns", []):
            matches = len(re.findall(pattern["regex"], content, re.IGNORECASE))
            if matches > 0:
                pattern_count += matches
                score += (
                    matches
                    * pattern.get("weight", 1.5)
                    * pattern.get("confidence", 0.5)
                )
                matched_patterns.append(
                    {
                        "type": "regex",
                        "id": pattern.get("description", pattern["regex"][:30]),
                        "pattern": pattern,
                        "matches": matches,
                    }
                )

        if pattern_count > 2:
            flags.append(f"suspicious_patterns_{pattern_count}")

        # Check for excessive capitalization
        caps_ratio = sum(1 for c in email.subject + email.content if c.isupper()) / max(
            len(email.subject + email.content), 1
        )
        if caps_ratio > 0.3:
            score += 10.0
            flags.append("excessive_caps")

        # Check for excessive punctuation
        punct_count = len(re.findall(r"[!?]{2,}", content))
        if punct_count > 2:
            score += punct_count * 2.0
            flags.append("excessive_punctuation")

        # Check for suspicious links
        url_count = len(
            re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                content,
            )
        )
        if url_count > 3:
            score += url_count * 3.0
            flags.append(f"many_links_{url_count}")

        # Check for suspicious domains in URLs
        suspicious_tlds = [".tk", ".ml", ".ga", ".cf", ".club", ".download"]
        for tld in suspicious_tlds:
            if tld in content:
                score += 5.0
                flags.append(f"suspicious_tld_{tld}")

        # Check for financial/urgency indicators
        urgency_words = [
            "urgent",
            "immediate",
            "expire",
            "limited time",
            "act now",
            "hurry",
        ]
        urgency_count = sum(1 for word in urgency_words if word in content)
        if urgency_count > 1:
            score += urgency_count * 3.0
            flags.append("urgency_indicators")

        self.logger.debug(f"Content analysis: score={score:.1f}, flags={flags}")

        return score, flags, matched_patterns

    @log_function()
    def _check_phishing_indicators(self, email: EmailMessage) -> float:
        """
        Check for phishing indicators in email content.

        Args:
            email: Email to analyze

        Returns:
            Phishing score (higher = more likely phishing)
        """
        content = f"{email.subject} {email.content}".lower()
        score = 0.0

        # Check for common phishing patterns
        for pattern in self.spam_patterns.get("phishing_patterns", []):
            matches = len(re.findall(pattern["regex"], content, re.IGNORECASE))
            if matches > 0:
                score += (
                    matches
                    * pattern.get("weight", 8.0)
                    * pattern.get("confidence", 0.8)
                )
                self.logger.debug(
                    f"Phishing pattern match: {pattern.get('description', pattern['regex'])}"
                )

        # Check for credential harvesting terms
        cred_terms = ["username", "password", "login", "sign in", "verify account"]
        cred_count = sum(1 for term in cred_terms if term in content)
        if cred_count > 2:
            score += cred_count * 5.0

        # Check for impersonation attempts
        impersonation_terms = [
            "bank",
            "paypal",
            "amazon",
            "microsoft",
            "apple",
            "google",
        ]
        domain = email.sender.split("@")[1] if "@" in email.sender else ""

        for term in impersonation_terms:
            if term in content and term not in domain:
                score += 10.0  # Likely impersonation
                self.logger.debug(f"Possible impersonation of {term}")

        return score

    @log_function()
    def _check_authentication(self, email: EmailMessage) -> float:
        """
        Check email authentication headers (SPF, DKIM, DMARC).

        Args:
            email: Email to analyze

        Returns:
            Authentication penalty score
        """
        score = 0.0
        headers = {k.lower(): v for k, v in email.headers.items()}

        # Check SPF
        spf_header = headers.get("received-spf", "").lower()
        if "fail" in spf_header:
            score += 15.0
        elif "softfail" in spf_header:
            score += 8.0
        elif "none" in spf_header or not spf_header:
            score += 5.0

        # Check DKIM
        dkim_header = headers.get("dkim-signature", "")
        if not dkim_header:
            score += 5.0

        # Check DMARC
        auth_results = headers.get("authentication-results", "").lower()
        if "dmarc=fail" in auth_results:
            score += 20.0
        elif "dmarc=none" in auth_results or "dmarc" not in auth_results:
            score += 3.0

        return score

    @log_function()
    async def _apply_spam_rules(
        self, email: EmailMessage, analysis: SpamAnalysis
    ) -> float:
        """
        Apply learned spam detection rules from procedural memory.

        Args:
            email: Email to analyze
            analysis: Current analysis state

        Returns:
            Additional spam score from rules
        """
        try:
            # Search for relevant spam detection rules
            search_results = await self.procedural_memory.search(
                query="spam detection rule", limit=5
            )

            additional_score = 0.0

            for memory_item, score in search_results:
                if score > 0.7:  # Good relevance match
                    rule_data = memory_item.metadata
                    rule_type = rule_data.get("rule_type", "")

                    # Apply different types of learned rules
                    if rule_type == "sender_pattern":
                        pattern = rule_data.get("pattern", "")
                        if pattern and pattern in email.sender:
                            additional_score += rule_data.get("penalty", 10.0)

                    elif rule_type == "content_pattern":
                        pattern = rule_data.get("pattern", "")
                        if pattern and pattern in email.content.lower():
                            additional_score += rule_data.get("penalty", 5.0)

                    elif rule_type == "subject_pattern":
                        pattern = rule_data.get("pattern", "")
                        if pattern and pattern in email.subject.lower():
                            additional_score += rule_data.get("penalty", 8.0)

            return additional_score

        except Exception as e:
            self.logger.warning(f"Failed to apply spam rules: {e}")
            return 0.0

    @log_function()
    def _classify_spam_score(self, analysis: SpamAnalysis) -> SpamAnalysis:
        """
        Convert numeric spam score to confidence level and recommendation.

        Args:
            analysis: Analysis object to classify

        Returns:
            Updated analysis with confidence and recommendation
        """
        score = analysis.spam_score

        # Determine confidence level based on score
        if score >= 80:
            analysis.confidence = SpamConfidence.DEFINITELY_SPAM
            analysis.is_spam = True
            analysis.recommendation = "Block email - high confidence spam"
        elif score >= 60:
            analysis.confidence = SpamConfidence.LIKELY_SPAM
            analysis.is_spam = True
            analysis.recommendation = "Quarantine email - likely spam"
        elif score >= 40:
            analysis.confidence = SpamConfidence.SUSPICIOUS
            analysis.is_spam = True
            analysis.recommendation = "Flag for review - suspicious content"
        elif score >= 20:
            analysis.confidence = SpamConfidence.UNCERTAIN
            analysis.is_spam = False
            analysis.recommendation = "Deliver with caution - uncertain classification"
        elif score >= 5:
            analysis.confidence = SpamConfidence.LIKELY_CLEAN
            analysis.is_spam = False
            analysis.recommendation = "Deliver normally - likely clean"
        else:
            analysis.confidence = SpamConfidence.DEFINITELY_CLEAN
            analysis.is_spam = False
            analysis.recommendation = "Deliver normally - clean email"

        return analysis

    @log_function()
    async def _store_spam_analysis(
        self, email: EmailMessage, analysis: SpamAnalysis
    ) -> None:
        """
        Store spam analysis results in memory for learning.

        Args:
            email: Email that was analyzed
            analysis: Analysis results to store
        """
        try:
            # Store in episodic memory for learning
            content = f"Spam analysis: {email.sender} - {analysis.confidence.value}"

            metadata = {
                "analysis_type": "spam_detection",
                "sender": email.sender,
                "subject": email.subject,
                "classification": "spam" if analysis.is_spam else "clean",
                "confidence": analysis.confidence.value,
                "spam_score": analysis.spam_score,
                "reasons": [r.value for r in analysis.reasons],
                "date": datetime.now(UTC).isoformat(),
                "email_id": email.id,
            }

            await self.episodic_memory.add(content, metadata)
            self.logger.debug(f"Stored spam analysis for {email.sender}")

            # Update pattern effectiveness
            await self.update_pattern_effectiveness(
                email, analysis.is_spam, analysis.details.get("patterns_matched", [])
            )

        except Exception as e:
            self.logger.error(f"Failed to store spam analysis: {e}")

    @log_function()
    async def update_pattern_effectiveness(
        self,
        email: EmailMessage,
        was_spam: bool,
        patterns_matched: List[Dict[str, Any]],
    ) -> None:
        """
        Update the effectiveness of spam patterns based on user feedback.

        When a user marks an email as spam/not spam, this updates the
        confidence scores of patterns that matched to improve future accuracy.

        Args:
            email: The email that was classified
            was_spam: Whether the email was actually spam (user feedback)
            patterns_matched: List of patterns that matched this email
        """
        try:
            human_feedback_weight = self.spam_patterns.get("learning_config", {}).get(
                "human_feedback_weight", 1.5
            )

            for pattern in patterns_matched:
                pattern_type = pattern.get("type")
                pattern_id = pattern.get("id")

                if not pattern_type or not pattern_id:
                    continue

                # Calculate effectiveness adjustment
                if was_spam:
                    # Pattern correctly identified spam - increase confidence
                    adjustment = 0.05 * human_feedback_weight
                else:
                    # Pattern incorrectly flagged as spam - decrease confidence
                    adjustment = -0.1 * human_feedback_weight

                # Store feedback in semantic memory for pattern learning
                await self.semantic_memory.add(
                    content=f"Spam pattern feedback: {pattern_type} pattern {pattern_id}",
                    metadata={
                        "type": "pattern_feedback",
                        "pattern_type": pattern_type,
                        "pattern_id": pattern_id,
                        "was_spam": was_spam,
                        "confidence_adjustment": adjustment,
                        "email_sender": email.sender,
                        "email_subject": email.subject[:100],
                        "feedback_date": datetime.now(UTC).isoformat(),
                    },
                    knowledge_type=KnowledgeType.INSIGHT,
                    confidence=KnowledgeConfidence.HIGH,
                )

                self.logger.info(
                    f"Updated pattern effectiveness: {pattern_type} {pattern_id} "
                    f"(adjustment: {adjustment:+.3f})"
                )

        except Exception as e:
            self.logger.error(f"Failed to update pattern effectiveness: {e}")

    @log_function()
    async def mark_as_spam(self, email: EmailMessage, user_feedback: str = "") -> None:
        """
        Mark an email as spam based on user feedback.

        Updates the learning system with user feedback to improve future detection.

        Args:
            email: Email to mark as spam
            user_feedback: Optional user explanation
        """
        try:
            self.logger.info(f"User marked email from {email.sender} as spam")

            # Store user feedback in episodic memory
            content = f"User feedback: SPAM - {email.sender}"
            if user_feedback:
                content += f" - {user_feedback}"

            metadata = {
                "feedback_type": "user_spam_report",
                "sender": email.sender,
                "subject": email.subject,
                "classification": "spam",
                "user_feedback": user_feedback,
                "date": datetime.now(UTC).isoformat(),
                "email_id": email.id,
            }

            await self.episodic_memory.add(content, metadata)

            # Update semantic memory with sender information
            await self.semantic_memory.add(
                content=f"Spam sender: {email.sender}",
                metadata={
                    "sender_email": email.sender,
                    "sender_type": "spam",
                    "trust_level": "none",
                    "user_marked": True,
                    "last_updated": datetime.now(UTC).isoformat(),
                },
            )

            # Re-analyze to get patterns that would have matched
            analysis = await self.analyze_spam(email)
            if "patterns_matched" in analysis.details:
                await self.update_pattern_effectiveness(
                    email, True, analysis.details["patterns_matched"]
                )

            self.logger.info(f"User spam feedback recorded for {email.sender}")

        except Exception as e:
            self.logger.error(f"Failed to record spam feedback: {e}")

    @log_function()
    async def mark_as_not_spam(
        self, email: EmailMessage, user_feedback: str = ""
    ) -> None:
        """
        Mark an email as not spam based on user feedback.

        Updates the learning system to avoid false positives in the future.

        Args:
            email: Email to mark as not spam
            user_feedback: Optional user explanation
        """
        try:
            self.logger.info(f"User marked email from {email.sender} as not spam")

            # Store user feedback in episodic memory
            content = f"User feedback: NOT SPAM - {email.sender}"
            if user_feedback:
                content += f" - {user_feedback}"

            metadata = {
                "feedback_type": "user_ham_report",
                "sender": email.sender,
                "subject": email.subject,
                "classification": "clean",
                "user_feedback": user_feedback,
                "date": datetime.now(UTC).isoformat(),
                "email_id": email.id,
            }

            await self.episodic_memory.add(content, metadata)

            # Update semantic memory to mark as trusted
            await self.semantic_memory.add(
                content=f"Trusted sender: {email.sender}",
                metadata={
                    "sender_email": email.sender,
                    "sender_type": "trusted",
                    "trust_level": "high",
                    "user_verified": True,
                    "last_updated": datetime.now(UTC).isoformat(),
                },
            )

            # Re-analyze to get patterns that would have matched
            analysis = await self.analyze_spam(email)
            if "patterns_matched" in analysis.details:
                await self.update_pattern_effectiveness(
                    email, False, analysis.details["patterns_matched"]
                )

            self.logger.info(f"User not-spam feedback recorded for {email.sender}")

        except Exception as e:
            self.logger.error(f"Failed to record not-spam feedback: {e}")

    @log_function()
    async def get_spam_statistics(self) -> dict[str, Any]:
        """
        Get statistics about spam detection performance.

        Returns:
            Dictionary with spam detection metrics and statistics
        """
        try:
            # Search for recent spam analyses
            recent_analyses = await self.episodic_memory.search(
                query="spam analysis", limit=100
            )

            stats = {
                "total_analyses": len(recent_analyses),
                "spam_detected": 0,
                "clean_emails": 0,
                "confidence_distribution": {},
                "common_reasons": {},
                "user_feedback_count": 0,
            }

            for memory_item, score in recent_analyses:
                if score > 0.7:  # Good match
                    metadata = memory_item.metadata
                    classification = metadata.get("classification", "unknown")

                    if classification == "spam":
                        stats["spam_detected"] += 1
                    elif classification == "clean":
                        stats["clean_emails"] += 1

                    # Track confidence distribution
                    confidence = metadata.get("confidence", "unknown")
                    stats["confidence_distribution"][confidence] = (
                        stats["confidence_distribution"].get(confidence, 0) + 1
                    )

                    # Track common reasons
                    reasons = metadata.get("reasons", [])
                    for reason in reasons:
                        stats["common_reasons"][reason] = (
                            stats["common_reasons"].get(reason, 0) + 1
                        )

            # Get user feedback statistics
            feedback_results = await self.episodic_memory.search(
                query="user feedback", limit=50
            )
            stats["user_feedback_count"] = len(
                [r for r in feedback_results if r[1] > 0.7]
            )

            self.logger.info(
                f"Spam statistics: {stats['total_analyses']} analyses, {stats['spam_detected']} spam"
            )
            return stats

        except Exception as e:
            self.logger.error(f"Failed to get spam statistics: {e}")
            return {"error": str(e)}


@log_function()
async def demo_spam_detection() -> None:
    """
    Demonstration of the Spam Detection Agent.

    Creates sample emails with varying spam characteristics,
    analyzes them for spam indicators,
    and displays the analysis results.
    """
    logger.info("🛡️ Spam Detection Agent Demo")
    logger.info("=" * 50)

    # Initialize detector
    detector = SpamDetector()

    # Create test emails with different characteristics
    test_emails = [
        # Legitimate business email
        EmailMessage(
            id="test_001",
            sender="john.smith@realestate.com",
            subject="Q4 Rent Roll - 123 Main Street Property",
            content="Please find attached the quarterly rent roll for our Main Street property. All tenants are current on payments.",
            headers={"Received-SPF": "pass"},
        ),
        # Suspicious promotional email
        EmailMessage(
            id="test_002",
            sender="deals@promotions.biz",
            subject="🎉 URGENT: Claim Your FREE $1000 Gift Card NOW!!!",
            content="Congratulations! You've been selected to receive a FREE $1000 gift card! Click here immediately to claim your prize before it expires!",
            headers={},
        ),
        # Phishing attempt
        EmailMessage(
            id="test_003",
            sender="security@bank-alert.net",
            subject="URGENT: Your Account Has Been Compromised",
            content="Your bank account has been compromised. Please click this link immediately to verify your credentials and secure your account.",
            headers={"Received-SPF": "fail"},
        ),
    ]

    # Analyze each email
    for email in test_emails:
        logger.info(f"\n📧 Analyzing: {email.subject}")
        logger.info(f"   From: {email.sender}")

        analysis = await detector.analyze_spam(email)

        logger.info("📊 Analysis Results:")
        logger.info(f"   Classification: {'SPAM' if analysis.is_spam else 'CLEAN'}")
        logger.info(f"   Confidence: {analysis.confidence.value}")
        logger.info(f"   Spam Score: {analysis.spam_score:.1f}/100")
        logger.info(f"   Recommendation: {analysis.recommendation}")

        if analysis.reasons:
            logger.info(f"   Reasons: {', '.join([r.value for r in analysis.reasons])}")

        if analysis.blacklist_hits:
            logger.info(f"   Blacklist Hits: {', '.join(analysis.blacklist_hits)}")

        if analysis.content_flags:
            logger.info(f"   Content Flags: {', '.join(analysis.content_flags)}")

        logger.info(f"   Processing Time: {analysis.processing_time:.3f}s")

    # Show statistics
    stats = await detector.get_spam_statistics()
    logger.info("\n📈 Detection Statistics:")
    logger.info(f"   Total Analyses: {stats.get('total_analyses', 0)}")
    logger.info(f"   Spam Detected: {stats.get('spam_detected', 0)}")
    logger.info(f"   Clean Emails: {stats.get('clean_emails', 0)}")

    logger.info("\n✨ Demo completed!")


if __name__ == "__main__":
    # Run demo if executed directly
    asyncio.run(demo_spam_detection())

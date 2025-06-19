"""
Contact Extraction Agent for Email Document Management

This agent performs contact extraction from emails, focusing on
identifying genuine individual humans while filtering out automated systems,
spam, and unwanted solicitations. The system is designed specifically for
private market asset management users who need to build quality
contact databases from their email communications.

Key Features:
    - human vs. automated system detection
    - Multi-layered filtering to eliminate spam and bulk emails
    - Contact information extraction from signatures and headers
    - Confidence scoring based on multiple factors
    - Memory integration for learning and pattern recognition
    - Contact type classification (personal, professional, family, vendor)
    - Complete logging and monitoring

Detection Strategies:
    - Pattern matching for no-reply and automated addresses
    - Domain blacklist checking for bulk email services
    - Content analysis for personal vs. automated indicators
    - Semantic memory lookup for known sender patterns
    - Signature parsing for structured contact information
    - Email header analysis for authentication and routing

Contact Types:
    - Personal: Friends, family, personal contacts
    - Professional: Colleagues, business contacts, industry peers
    - Family: Family members and close relatives
    - Vendor: Service providers, suppliers, business vendors
    - Unknown: Contacts that don't fit clear categories

Integration:
    The agent integrates with the memory system to store learned patterns
    and contact information, enabling continuous improvement and faster
    processing of known contact types.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import asyncio
import os
import re

# Logging system integration
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..memory.contact import ContactMemory
from ..memory.episodic import EpisodicMemory

# Memory system integration
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory

# Email message structure
from .supervisor import EmailMessage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function

# Initialize logger
logger = get_logger(__name__)


class ContactType(Enum):
    """
    Types of contacts that can be extracted from emails.

    Categorizes contacts based on their relationship to the user
    and the nature of their communication patterns.
    """

    PERSONAL = "personal"  # Friends, personal acquaintances
    PROFESSIONAL = "professional"  # Work colleagues, business contacts
    FAMILY = "family"  # Family members, relatives
    VENDOR = "vendor"  # Service providers, suppliers
    UNKNOWN = "unknown"  # Unclassified contacts


class ContactConfidence(Enum):
    """
    Confidence levels for contact extraction accuracy.

    Represents the system's confidence in the extracted contact
    being a real person vs. an automated system or spam.
    """

    HIGH = "high"  # 90%+ confidence - definitely a real person
    MEDIUM = "medium"  # 70-90% confidence - likely a real person
    LOW = "low"  # 40-70% confidence - uncertain classification
    NONE = "none"  # <40% confidence - likely automated/spam


@dataclass
class ContactInfo:
    """
    Extracted contact information with complete metadata.

    Represents a complete contact profile extracted from email
    communications, including personal details, confidence metrics,
    and extraction metadata for quality assessment.

    Attributes:
        email: Primary email address of the contact
        name: Full name (if available)
        first_name: Given name (if parsed)
        last_name: Family name (if parsed)
        phone: Phone number (if found in signature)
        organization: Company or organization name
        title: Job title or position
        address: Physical address (if found)
        contact_type: Categorized relationship type
        confidence: Extraction confidence level
        source_email_id: ID of the email this contact was extracted from
        extraction_reasoning: Explanation of extraction decision
        metadata: Additional structured data and metrics
    """

    email: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    organization: str | None = None
    title: str | None = None
    address: str | None = None
    contact_type: ContactType = ContactType.UNKNOWN
    confidence: ContactConfidence = ContactConfidence.LOW
    source_email_id: str | None = None
    extraction_reasoning: str = ""
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize metadata dictionary if not provided."""
        if self.metadata is None:
            self.metadata = {}

        # Validate email format
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email address: {self.email}")

    def to_dict(self) -> dict[str, Any]:
        """Convert contact info to dictionary for storage."""
        return {
            "email": self.email,
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "organization": self.organization,
            "title": self.title,
            "address": self.address,
            "contact_type": self.contact_type.value,
            "confidence": self.confidence.value,
            "source_email_id": self.source_email_id,
            "extraction_reasoning": self.extraction_reasoning,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContactInfo":
        """Create ContactInfo from dictionary data."""
        return cls(
            email=data["email"],
            name=data.get("name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
            organization=data.get("organization"),
            title=data.get("title"),
            address=data.get("address"),
            contact_type=ContactType(data.get("contact_type", "unknown")),
            confidence=ContactConfidence(data.get("confidence", "low")),
            source_email_id=data.get("source_email_id"),
            extraction_reasoning=data.get("extraction_reasoning", ""),
            metadata=data.get("metadata", {}),
        )


class ContactExtractor:
    """
    contact extraction agent for email document management.

    Analyzes email messages to identify and extract real human contacts
    while filtering out automated systems, spam, and unwanted solicitations.
    Uses multiple detection layers and machine learning techniques to ensure
    high-quality contact extraction suitable for environments.

    The extractor integrates with the memory system to learn from patterns
    and improve accuracy over time, making it particularly effective for
    users with consistent communication patterns.

    Attributes:
        procedural_memory: Stores extraction rules and procedures
        semantic_memory: Stores knowledge about senders and email types
        episodic_memory: Stores extraction history and feedback
        contact_memory: Stores extracted contact information
    """

    def __init__(self) -> None:
        """
        Initialize the contact extraction agent.

        Sets up memory systems, pattern databases, and extraction
        parameters for optimal contact identification performance.
        """
        # Initialize memory systems with config-based limits
        try:
            # For ProceduralMemory, create a minimal client or skip if not needed for contact extraction
            # # Third-party imports
            from qdrant_client import QdrantClient

            # ContactExtractor typically doesn't need complex procedural patterns
            # Create a minimal client for basic functionality
            mock_client = QdrantClient(
                ":memory:"
            )  # In-memory client for basic functionality
            self.procedural_memory = ProceduralMemory(mock_client)
        except Exception:
            # If Qdrant is not available, contact extraction can work without procedural memory
            self.procedural_memory = None

        self.semantic_memory = SemanticMemory()
        self.episodic_memory = EpisodicMemory()
        self.contact_memory = ContactMemory()

        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing Contact Extraction Agent")

        # Patterns for identifying automated/bulk emails
        self.no_reply_patterns = [
            r"no[-_]?reply",
            r"noreply",
            r"donotreply",
            r"do[-_]?not[-_]?reply",
            r"automated",
            r"auto[-_]?generated",
            r"system",
            r"daemon",
            r"mailer[-_]?daemon",
            r"postmaster",
            r"webmaster",
            r"admin",
            r"robot",
            r"bounce",
        ]

        # Common bulk/marketing domains to exclude
        self.bulk_domains = {
            "mailchimp.com",
            "constantcontact.com",
            "sendgrid.net",
            "amazonses.com",
            "mailgun.org",
            "sparkpostmail.com",
            "email.amazon.com",
            "bounce.email",
            "unsubscribe.email",
            "campaign-monitor.com",
            "aweber.com",
            "getresponse.com",
            "madmimi.com",
            "verticalresponse.com",
            "icontact.com",
            "benchmarkemail.com",
            "emailbrain.com",
            "silverpop.com",
        }

        # Patterns for extracting contact information
        self.phone_pattern = re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
        )
        self.name_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b")

        # Patterns for identifying personal vs automated content
        self.personal_indicators = [
            r"\bthanks?\b",
            r"\bthank you\b",
            r"\bregards\b",
            r"\bbest\b",
            r"\bsincerely\b",
            r"\bcheers\b",
            r"\bhope\b",
            r"\bwish\b",
            r"\bfyi\b",
            r"\bbtw\b",
            r"\blmk\b",
            r"\basap\b",
        ]

        self.automated_indicators = [
            r"\bautomatic\b",
            r"\bgenerated\b",
            r"\bsystem\b",
            r"\bnotification\b",
            r"\balert\b",
            r"\breminder\b",
            r"\bconfirm\b",
            r"\bverify\b",
            r"\bunsubscribe\b",
            r"\bclick here\b",
            r"\bvisit our\b",
        ]

        self.logger.info("Contact Extraction Agent initialized successfully")

    @log_function()
    async def extract_contacts(self, email: EmailMessage) -> list[ContactInfo]:
        """
        Main entry point for contact extraction from an email message.

        Performs complete analysis to determine if the sender is a real
        person and extracts their contact information if appropriate.

        Args:
            email: Email message to analyze for contact extraction

        Returns:
            List of extracted ContactInfo objects (may be empty if no valid contacts)

        Raises:
            ValueError: If email parameter is invalid
        """
        if not email or not email.sender:
            raise ValueError("Email and sender information are required")

        self.logger.info(f"Extracting contacts from email: {email.sender}")

        try:
            # Step 1: Analyze if sender is likely a real person
            person_analysis = await self._analyze_real_person(email)

            if person_analysis["confidence"] == ContactConfidence.NONE:
                self.logger.info(f"Skipping extraction: {person_analysis['reasoning']}")
                return []

            # Step 2: Extract detailed contact information
            contact_info = await self._extract_contact_info(email, person_analysis)

            if not contact_info:
                self.logger.info("No extractable contact information found")
                return []

            # Step 3: Enhance contact with additional analysis
            contact_info = await self._enhance_contact(contact_info, email)

            # Step 4: Store successful extraction in memory
            await self._store_extraction(contact_info, email)

            self.logger.info(
                f"Successfully extracted contact: {contact_info.name or contact_info.email} "
                f"(confidence: {contact_info.confidence.value})"
            )

            return [contact_info]

        except Exception as e:
            self.logger.error(f"Contact extraction failed for {email.sender}: {e}")
            return []

    @log_function()
    async def _analyze_real_person(self, email: EmailMessage) -> dict[str, Any]:
        """
        Determine if the email sender is likely a real person vs. automated system.

        Uses multiple heuristics including pattern matching, domain analysis,
        content scoring, and memory lookups to classify the sender.

        Args:
            email: Email message to analyze

        Returns:
            Dictionary containing confidence level and reasoning
        """
        self.logger.debug(f"Analyzing sender authenticity: {email.sender}")

        sender_email = email.sender.lower().strip()

        # Validate email format
        if "@" not in sender_email:
            return {
                "confidence": ContactConfidence.NONE,
                "reasoning": "Invalid email format",
            }

        local_part, domain = sender_email.split("@", 1)

        # Check for no-reply patterns
        for pattern in self.no_reply_patterns:
            if re.search(pattern, sender_email, re.IGNORECASE):
                return {
                    "confidence": ContactConfidence.NONE,
                    "reasoning": f"No-reply address pattern detected: {pattern}",
                }

        # Check for bulk email domains
        if domain in self.bulk_domains:
            return {
                "confidence": ContactConfidence.NONE,
                "reasoning": f"Known bulk email domain: {domain}",
            }

        # Check for automated system patterns in local part
        automated_indicators = [
            "notification",
            "alert",
            "system",
            "admin",
            "support",
            "info",
            "sales",
            "marketing",
            "newsletter",
            "updates",
            "service",
            "help",
            "contact",
            "team",
        ]

        for indicator in automated_indicators:
            if indicator in local_part:
                # Still might be a person, check content for personal indicators
                personal_score = self._calculate_personal_score(email)
                if personal_score < 0.3:
                    return {
                        "confidence": ContactConfidence.NONE,
                        "reasoning": f"Automated system pattern in address: {indicator}",
                    }
                break

        # Check semantic memory for known sender patterns
        sender_knowledge = await self._check_sender_knowledge(email.sender)

        if sender_knowledge:
            trust_level = sender_knowledge.get("trust_level", "unknown")
            sender_type = sender_knowledge.get("sender_type", "unknown")

            if trust_level == "spam" or trust_level == "none":
                return {
                    "confidence": ContactConfidence.NONE,
                    "reasoning": "Previously identified as spam/untrusted sender",
                }

            if sender_type in ["family", "colleague", "friend", "personal"]:
                return {
                    "confidence": ContactConfidence.HIGH,
                    "reasoning": f"Known trusted contact type: {sender_type}",
                }

        # Calculate personal content score
        personal_score = self._calculate_personal_score(email)

        # Determine confidence based on multiple factors
        if personal_score >= 0.7:
            confidence = ContactConfidence.HIGH
            reasoning = f"High personal content score: {personal_score:.2f}"
        elif personal_score >= 0.4:
            confidence = ContactConfidence.MEDIUM
            reasoning = f"Medium personal content score: {personal_score:.2f}"
        elif personal_score >= 0.2:
            confidence = ContactConfidence.LOW
            reasoning = f"Low personal content score: {personal_score:.2f}"
        else:
            confidence = ContactConfidence.NONE
            reasoning = f"Very low personal content score: {personal_score:.2f}"

        self.logger.debug(f"Person analysis result: {confidence.value} - {reasoning}")

        return {
            "confidence": confidence,
            "reasoning": reasoning,
            "personal_score": personal_score,
        }

    @log_function()
    def _calculate_personal_score(self, email: EmailMessage) -> float:
        """
        Calculate a score indicating how personal/human the email content appears.

        Analyzes the email content for indicators of human vs. automated origin
        using pattern matching and linguistic analysis.

        Args:
            email: Email message to analyze

        Returns:
            Score between 0.0 (clearly automated) and 1.0 (clearly personal)
        """
        content = f"{email.subject} {email.content}".lower()

        # Count personal indicators
        personal_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in self.personal_indicators
        )

        # Count automated indicators
        automated_count = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in self.automated_indicators
        )

        # Check for personal pronouns and conversational language
        personal_pronouns = len(
            re.findall(r"\b(i|me|my|we|us|our|you|your)\b", content)
        )
        questions = len(re.findall(r"\?", content))
        _exclamations = len(re.findall(r"!", content))

        # Check for signature-like patterns
        signature_indicators = len(
            re.findall(
                r"(best regards|sincerely|thanks|cheers|yours|sent from)", content
            )
        )

        # Calculate composite score
        personal_signals = (
            personal_count + personal_pronouns + questions + signature_indicators
        )
        automated_signals = automated_count

        # Length normalization
        content_length = max(len(content.split()), 1)
        normalized_personal = min(personal_signals / content_length * 10, 1.0)
        normalized_automated = min(automated_signals / content_length * 10, 1.0)

        # Final score calculation
        if normalized_automated > normalized_personal * 2:
            score = max(0.0, 0.3 - normalized_automated * 0.5)
        else:
            score = min(1.0, normalized_personal * 0.7 + 0.3)

        self.logger.debug(
            f"Personal score calculation: personal={personal_signals}, "
            f"automated={automated_signals}, score={score:.3f}"
        )

        return score

    @log_function()
    async def _check_sender_knowledge(self, sender_email: str) -> dict[str, Any] | None:
        """
        Check semantic memory for existing knowledge about the sender.

        Looks up previous interactions and stored information about
        the sender to inform extraction decisions.

        Args:
            sender_email: Email address to look up

        Returns:
            Dictionary with sender information or None if not found
        """
        try:
            # Search semantic memory for sender information
            search_results = await self.semantic_memory.search(
                query=f"sender:{sender_email}", limit=1
            )

            if search_results:
                memory_item, score = search_results[0]
                if score > 0.8:  # High confidence match
                    return memory_item.metadata

            return None

        except Exception as e:
            self.logger.warning(
                f"Failed to check sender knowledge for {sender_email}: {e}"
            )
            return None

    @log_function()
    async def _extract_contact_info(
        self, email: EmailMessage, person_analysis: dict[str, Any]
    ) -> ContactInfo | None:
        """
        Extract detailed contact information from the email.

        Parses the email content, headers, and signature to extract
        structured contact information including name, phone, organization, etc.

        Args:
            email: Email message to extract from
            person_analysis: Result from person authenticity analysis

        Returns:
            ContactInfo object with extracted details or None if extraction fails
        """
        self.logger.debug(f"Extracting contact details from {email.sender}")

        try:
            # Initialize contact info with email address
            contact = ContactInfo(
                email=email.sender.lower().strip(),
                source_email_id=getattr(email, "id", None),
                confidence=person_analysis["confidence"],
                extraction_reasoning=person_analysis["reasoning"],
            )

            # Extract name from sender field or signature
            contact.name = self._extract_name_from_sender(email.sender)

            # Parse signature for additional details
            signature_info = self._extract_from_signature(email.content)

            # Merge signature information
            if signature_info.get("name") and not contact.name:
                contact.name = signature_info["name"]

            contact.phone = signature_info.get("phone")
            contact.organization = signature_info.get("organization")
            contact.title = signature_info.get("title")
            contact.address = signature_info.get("address")

            # Parse name into components
            if contact.name:
                name_parts = contact.name.strip().split()
                if len(name_parts) >= 2:
                    contact.first_name = name_parts[0]
                    contact.last_name = " ".join(name_parts[1:])
                elif len(name_parts) == 1:
                    contact.first_name = name_parts[0]

            # Determine contact type
            contact.contact_type = self._determine_contact_type(email, contact)

            # Add extraction metadata
            contact.metadata = {
                "extraction_date": datetime.now(UTC).isoformat(),
                "personal_score": person_analysis.get("personal_score", 0.0),
                "signature_found": bool(signature_info),
                "email_subject": email.subject,
                "extraction_version": "1.0",
            }

            # Validate that we have meaningful information
            if not contact.name and not contact.phone and not contact.organization:
                self.logger.debug("Insufficient contact information extracted")
                return None

            return contact

        except Exception as e:
            self.logger.error(f"Failed to extract contact info: {e}")
            return None

    @log_function()
    def _extract_name_from_sender(self, sender: str) -> str | None:
        """
        Extract human name from sender field.

        Handles various email sender formats to extract the display name.

        Args:
            sender: Sender field from email

        Returns:
            Extracted name or None if not found/invalid
        """
        if not sender:
            return None

        # Handle format: "John Doe <john@example.com>"
        if "<" in sender and ">" in sender:
            name_part = sender.split("<")[0].strip()
            # Clean up quotes and whitespace
            name_part = name_part.strip("\"'").strip()
            if name_part and "@" not in name_part:
                return name_part

        # Handle format where email is the display name (skip)
        if "@" in sender:
            return None

        return sender.strip() if sender.strip() else None

    @log_function()
    def _extract_from_signature(self, content: str) -> dict[str, str]:
        """
        Extract contact information from email signature.

        Parses email content to find and extract structured information
        from signature blocks including names, titles, organizations, and contact details.

        Args:
            content: Email body content to parse

        Returns:
            Dictionary with extracted signature information
        """
        if not content:
            return {}

        signature_info = {}

        # Look for common signature patterns
        lines = content.split("\n")

        # Find potential signature start
        signature_start = -1
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(
                marker in line_lower
                for marker in ["regards", "sincerely", "thanks", "best", "--"]
            ):
                signature_start = i
                break

        if signature_start == -1:
            # No clear signature, look in last few lines
            signature_start = max(0, len(lines) - 5)

        signature_lines = lines[signature_start:]
        signature_text = "\n".join(signature_lines)

        # Extract phone numbers
        phone_matches = self.phone_pattern.findall(signature_text)
        if phone_matches:
            # Format first phone number found
            area, exchange, number = phone_matches[0]
            signature_info["phone"] = f"({area}) {exchange}-{number}"

        # Extract names (look for capitalized words)
        name_matches = self.name_pattern.findall(signature_text)
        if name_matches:
            # Filter out common non-name words
            non_names = {
                "Best",
                "Regards",
                "Sincerely",
                "Thanks",
                "Sent",
                "From",
                "Mobile",
                "Phone",
            }
            potential_names = [name for name in name_matches if name not in non_names]
            if potential_names:
                signature_info["name"] = potential_names[0]

        # Look for organization/company names
        org_patterns = [
            r"(?:Company|Corp|Inc|LLC|Ltd)\.?",  # Company suffixes
            r"(?:at\s+)([A-Z][a-zA-Z\s&]+)",  # "at Company Name"
        ]

        for pattern in org_patterns:
            matches = re.findall(pattern, signature_text, re.IGNORECASE)
            if matches:
                signature_info["organization"] = matches[0].strip()
                break

        # Look for job titles
        title_patterns = [
            r"(?:Manager|Director|President|VP|CEO|CTO|CFO|Partner)",
            r"(?:Senior|Principal|Lead)\s+\w+",
            r"(?:Vice President|Executive|Analyst|Associate)",
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, signature_text, re.IGNORECASE)
            if matches:
                signature_info["title"] = matches[0].strip()
                break

        self.logger.debug(f"Signature extraction found: {list(signature_info.keys())}")

        return signature_info

    @log_function()
    def _determine_contact_type(
        self, email: EmailMessage, contact: ContactInfo
    ) -> ContactType:
        """
        Determine the type/category of the contact based on email content and context.

        Analyzes various signals to classify the relationship type.

        Args:
            email: Source email message
            contact: Contact information to classify

        Returns:
            ContactType enum value
        """
        content_lower = f"{email.subject} {email.content}".lower()

        # Family indicators
        family_terms = [
            "family",
            "mom",
            "dad",
            "sister",
            "brother",
            "aunt",
            "uncle",
            "cousin",
        ]
        if any(term in content_lower for term in family_terms):
            return ContactType.FAMILY

        # indicators
        business_terms = [
            "meeting",
            "project",
            "deadline",
            "proposal",
            "contract",
            "business",
        ]
        if any(term in content_lower for term in business_terms):
            return ContactType.PROFESSIONAL

        # Vendor indicators
        vendor_terms = ["invoice", "payment", "service", "quote", "delivery", "order"]
        if any(term in content_lower for term in vendor_terms):
            return ContactType.VENDOR

        # Check organization for business classification
        if contact.organization:
            return ContactType.PROFESSIONAL

        # Default to personal for individual contacts
        return ContactType.PERSONAL

    @log_function()
    async def _enhance_contact(
        self, contact: ContactInfo, email: EmailMessage
    ) -> ContactInfo:
        """
        Enhance contact information with additional analysis and data enrichment.

        Performs additional processing to improve contact quality and completeness.

        Args:
            contact: Contact information to enhance
            email: Source email for additional context

        Returns:
            Enhanced ContactInfo object
        """
        try:
            # Check for existing contact in memory
            existing_contacts = await self.contact_memory.search(
                query=contact.email, limit=1
            )

            if existing_contacts:
                existing_item, score = existing_contacts[0]
                if score > 0.9:  # Very high match
                    # Merge with existing contact information
                    existing_data = existing_item.metadata

                    # Update with new information if better
                    if not contact.name and existing_data.get("name"):
                        contact.name = existing_data["name"]
                    if not contact.phone and existing_data.get("phone"):
                        contact.phone = existing_data["phone"]
                    if not contact.organization and existing_data.get("organization"):
                        contact.organization = existing_data["organization"]

                    # Increase confidence if we have historical data
                    if contact.confidence == ContactConfidence.LOW:
                        contact.confidence = ContactConfidence.MEDIUM
                        contact.extraction_reasoning += (
                            " (enhanced with historical data)"
                        )

            return contact

        except Exception as e:
            self.logger.warning(f"Failed to enhance contact {contact.email}: {e}")
            return contact

    @log_function()
    async def _store_extraction(
        self, contact: ContactInfo, email: EmailMessage
    ) -> None:
        """
        Store the successful contact extraction in memory systems.

        Records the extraction results in appropriate memory systems
        for future reference and learning.

        Args:
            contact: Extracted contact information
            email: Source email message
        """
        try:
            # Store in contact memory
            await self.contact_memory.add(
                content=f"Contact: {contact.name or contact.email}",
                metadata=contact.to_dict(),
            )

            # Store extraction pattern in procedural memory
            await self.procedural_memory.add(
                content=f"Extracted contact from {email.sender}",
                metadata={
                    "action": "contact_extraction",
                    "sender": email.sender,
                    "success": True,
                    "confidence": contact.confidence.value,
                    "contact_type": contact.contact_type.value,
                    "extraction_date": datetime.now(UTC).isoformat(),
                },
            )

            # Store sender information in semantic memory
            await self.semantic_memory.add(
                content=f"Sender: {email.sender} is a real person",
                metadata={
                    "sender_email": email.sender,
                    "sender_type": contact.contact_type.value,
                    "trust_level": "trusted",
                    "confidence": contact.confidence.value,
                    "last_seen": datetime.now(UTC).isoformat(),
                },
            )

            self.logger.debug(f"Stored extraction results for {contact.email}")

        except Exception as e:
            self.logger.error(f"Failed to store extraction results: {e}")

    @log_function()
    async def get_extracted_contacts(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieve previously extracted contacts from memory.

        Gets a list of contacts that have been successfully extracted
        and stored in the contact memory system.

        Args:
            limit: Maximum number of contacts to retrieve

        Returns:
            List of contact dictionaries with metadata
        """
        try:
            search_results = await self.contact_memory.search(
                query="Contact:", limit=limit
            )

            contacts = []
            for memory_item, _score in search_results:
                if "email" in memory_item.metadata:
                    contacts.append(memory_item.metadata)

            self.logger.info(f"Retrieved {len(contacts)} extracted contacts")
            return contacts

        except Exception as e:
            self.logger.error(f"Failed to retrieve contacts: {e}")
            return []

    @log_function()
    async def search_contacts(
        self, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Search extracted contacts by name, email, or organization.

        Performs semantic search across stored contacts to find matches
        for the given query string.

        Args:
            query: Search query (name, email, organization, etc.)
            limit: Maximum number of results to return

        Returns:
            List of matching contact dictionaries
        """
        if not query or not query.strip():
            return []

        try:
            search_results = await self.contact_memory.search(
                query=query.strip(), limit=limit
            )

            contacts = []
            for memory_item, score in search_results:
                if "email" in memory_item.metadata:
                    contact_data = memory_item.metadata.copy()
                    contact_data["relevance_score"] = score
                    contacts.append(contact_data)

            self.logger.info(
                f"Contact search '{query}' returned {len(contacts)} results"
            )
            return contacts

        except Exception as e:
            self.logger.error(f"Contact search failed for query '{query}': {e}")
            return []

    @log_function()
    async def get_contact_statistics(self) -> dict[str, Any]:
        """
        Get statistics about extracted contacts.

        Returns:
            Dictionary with contact extraction statistics and metrics
        """
        try:
            all_contacts = await self.get_extracted_contacts(limit=1000)

            stats = {
                "total_contacts": len(all_contacts),
                "by_type": {},
                "by_confidence": {},
                "recent_extractions": 0,
            }

            # Calculate statistics
            for contact in all_contacts:
                # Count by type
                contact_type = contact.get("contact_type", "unknown")
                stats["by_type"][contact_type] = (
                    stats["by_type"].get(contact_type, 0) + 1
                )

                # Count by confidence
                confidence = contact.get("confidence", "low")
                stats["by_confidence"][confidence] = (
                    stats["by_confidence"].get(confidence, 0) + 1
                )

                # Count recent extractions (last 7 days)
                extraction_date = contact.get("metadata", {}).get("extraction_date")
                if extraction_date:
                    try:
                        extraction_dt = datetime.fromisoformat(
                            extraction_date.replace("Z", "+00:00")
                        )
                        days_ago = (datetime.now(UTC) - extraction_dt).days
                        if days_ago <= 7:
                            stats["recent_extractions"] += 1
                    except (ValueError, TypeError):
                        pass

            self.logger.info(
                f"Contact statistics: {stats['total_contacts']} total contacts"
            )
            return stats

        except Exception as e:
            self.logger.error(f"Failed to get contact statistics: {e}")
            return {
                "total_contacts": 0,
                "by_type": {},
                "by_confidence": {},
                "recent_extractions": 0,
            }


@log_function()
async def demo_contact_extractor() -> None:
    """
    Demonstration of the contact extraction system.

    Shows how to use the ContactExtractor with sample email data
    and displays the extraction results.
    """
    print("🤖 Contact Extraction Agent Demo")  # noqa: T201
    print("=" * 50)  # noqa: T201

    # Initialize extractor
    extractor = ContactExtractor()

    # Sample email for demonstration
    sample_email = EmailMessage(
        id="demo_001",
        sender="John Smith <john.smith@example.com>",
        subject="Project Update Meeting",
        content="""Hi there,

I wanted to follow up on our discussion about the quarterly project review.
Can we schedule a meeting for next week?

Best regards,
John Smith
Senior Project Manager
Acme Corporation
Phone: (555) 123-4567
john.smith@acme-corp.com
""",
    )

    print(f"📧 Analyzing email from: {sample_email.sender}")  # noqa: T201
    print(f"📝 Subject: {sample_email.subject}")  # noqa: T201

    # Extract contacts
    extracted_contacts = await extractor.extract_contacts(sample_email)

    if extracted_contacts:
        for contact in extracted_contacts:
            print("\n✅ Contact Extracted:")  # noqa: T201
            print(f"   Name: {contact.name}")  # noqa: T201
            print(f"   Email: {contact.email}")  # noqa: T201
            print(f"   Phone: {contact.phone}")  # noqa: T201
            print(f"   Organization: {contact.organization}")  # noqa: T201
            print(f"   Title: {contact.title}")  # noqa: T201
            print(f"   Type: {contact.contact_type.value}")  # noqa: T201
            print(f"   Confidence: {contact.confidence.value}")  # noqa: T201
            print(f"   Reasoning: {contact.extraction_reasoning}")  # noqa: T201
    else:
        print("\n❌ No contacts extracted")  # noqa: T201

    # Show statistics
    stats = await extractor.get_contact_statistics()
    print("\n📊 Extraction Statistics:")  # noqa: T201
    print(f"   Total contacts: {stats['total_contacts']}")  # noqa: T201
    print(f"   Recent extractions: {stats['recent_extractions']}")  # noqa: T201

    print("\n✨ Demo completed!")  # noqa: T201


if __name__ == "__main__":
    # Run demo if executed directly
    asyncio.run(demo_contact_extractor())

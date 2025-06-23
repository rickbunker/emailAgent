"""
Contact Memory Management System for EmailAgent

contact memory system for private market asset management environments.
Provides dedicated Qdrant-based storage for contact information with
features including deduplication, relationship tracking, and contact enrichment.

Features:
    - Persistent contact record management with deduplication
    - Contact information enrichment and updating over time
    - Relationship tracking and business context analysis
    - search capabilities (name, email, organization, phone)
    - Contact interaction history and frequency tracking
    - Tag-based organization and categorization
    - confidence scoring and validation

Business Context:
    Designed for asset management firms requiring complete contact management
    across deal flow, investor relations, and business development activities.
    Maintains relationship context and interaction history for
    improved business intelligence and relationship management.

Technical Architecture:
    - Dedicated Qdrant collection for contact persistence
    - Vector-based semantic search with embedding models
    - Contact deduplication by email address (primary key)
    - Incremental contact enrichment with confidence scoring
    - relationship taxonomy and categorization
    - Complete audit trail and interaction tracking

Contact Types:
    - Personal: Personal contacts and relationships
    - Professional: Business contacts and colleagues
    - Family: Family members and personal relationships
    - Vendor: Service providers and business vendors
    - Unknown: Unclassified contacts requiring review

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import os

# Logging system
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.config import config
from utils.logging_system import get_logger, log_function

from .base import BaseMemory, MemoryItem

# Initialize logger
logger = get_logger(__name__)


class ContactType(Enum):
    """
    contact classification for business context.

    Provides structured categorization of contacts for asset management
    environments with appropriate business context and relationship types.

    Values:
        PERSONAL: Personal contacts and individual relationships
        PROFESSIONAL: Business contacts, colleagues, and industry professionals
        FAMILY: Family members and personal relationships
        VENDOR: Service providers, vendors, and business partners
        UNKNOWN: Unclassified contacts requiring manual review
    """

    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    FAMILY = "family"
    VENDOR = "vendor"
    UNKNOWN = "unknown"


class ContactConfidence(Enum):
    """
    Contact information confidence levels for data quality assessment.

    Provides graduated confidence scoring for contact information accuracy
    to support data quality management and validation workflows.

    Values:
        HIGH: Verified contact information from authoritative sources
        MEDIUM: Contact information from reliable but unverified sources
        LOW: Contact information requiring verification or review
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContactRecord:
    """
    Complete contact record for asset management environments.

    contact data structure with complete information tracking,
    relationship context, and interaction history for business intelligence
    and relationship management in asset management firms.

    Attributes:
        id: Unique contact identifier
        email: Primary email address (used as primary key)
        name: Full contact name
        first_name: Contact first name for personalization
        last_name: Contact surname for formal addressing
        phone: Primary phone number
        organization: Company or organization affiliation
        title: title or position
        address: Physical or business address
        contact_type: contact classification
        confidence: Information accuracy confidence level
        relationship: Business relationship description
        notes: Additional contact notes and context
        tags: Categorization tags for organization
        first_seen: Initial contact discovery timestamp
        last_updated: Most recent information update timestamp
        last_email_interaction: Most recent email interaction timestamp
        email_count: Total number of email interactions
        sources: List of email IDs where contact was discovered
        extraction_history: Historical record of contact data extraction
    """

    id: str
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

    # relationship and business context
    relationship: str | None = None  # "colleague", "investor", "vendor", "counterparty"
    notes: str | None = None
    tags: list[str] = field(default_factory=list)

    # Contact tracking and audit trail
    first_seen: str = ""
    last_updated: str = ""
    last_email_interaction: str = ""
    email_count: int = 0

    # Data sources and extraction history
    sources: list[str] = field(default_factory=list)  # Email IDs where contact found
    extraction_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """
        Initialize contact record with default values and timestamps.

        Ensures proper initialization of list fields and automatic
        timestamp generation for audit trail maintenance.
        """
        if not self.first_seen:
            self.first_seen = datetime.now(UTC).isoformat()
        if not self.last_updated:
            self.last_updated = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert contact record to dictionary for storage.

        Serializes contact record for Qdrant storage with proper
        enum value conversion and data structure formatting.

        Returns:
            Dictionary representation suitable for vector database storage
        """
        data = asdict(self)
        # Convert enums to string values for storage
        data["contact_type"] = self.contact_type.value
        data["confidence"] = self.confidence.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContactRecord":
        """
        Create contact record from dictionary data.

        Deserializes contact record from storage with proper enum
        conversion and data structure reconstruction.

        Args:
            data: Dictionary containing contact record data

        Returns:
            ContactRecord instance with proper typing
        """
        # Convert string enum values back to enum instances
        if "contact_type" in data:
            data["contact_type"] = ContactType(data["contact_type"])
        if "confidence" in data:
            data["confidence"] = ContactConfidence(data["confidence"])

        return cls(**data)

    def get_search_text(self) -> str:
        """
        Generate complete search text for vector indexing.

        Creates searchable text representation combining all contact
        information for semantic vector search capabilities.

        Returns:
            Combined text string for vector embedding and search
        """
        parts = []

        # Core identification information
        if self.name:
            parts.append(self.name)
        if self.email:
            parts.append(self.email)
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)

        # context
        if self.organization:
            parts.append(self.organization)
        if self.title:
            parts.append(self.title)
        if self.relationship:
            parts.append(self.relationship)

        # Additional searchable information
        if self.phone:
            parts.append(self.phone)
        if self.notes:
            parts.append(self.notes)

        # Include tags for categorical search
        parts.extend(self.tags)

        return " ".join(parts)


class ContactMemory(BaseMemory):
    """
    contact memory system for asset management environments.

    Provides complete contact management with deduplication, relationship
    tracking, and business intelligence features designed for private market
    asset management firms requiring contact relationship management.

    Features:
        - Contact deduplication by email address
        - Incremental contact information enrichment
        - Business relationship tracking and categorization
        - Interaction frequency and history tracking
        - search with semantic and categorical filtering
        - confidence scoring and validation
        - Tag-based organization and workflow integration

    Business Context:
        Enables asset management firms to maintain complete contact
        databases across deal flow, investor relations, business development,
        and operational activities with relationship context.

    Technical Implementation:
        - Dedicated Qdrant collection for contact persistence
        - Email-based primary key with automatic deduplication
        - Vector semantic search with embedding models
        - Incremental update workflow for contact enrichment
        - audit trail and interaction tracking
    """

    def __init__(self, max_items: int | None = None, **kwargs):
        """
        Initialize contact memory system.

        Args:
            max_items: Maximum number of contacts to store (uses config default if None)
            **kwargs: Additional arguments passed to BaseMemory
        """
        super().__init__(max_items=max_items, **kwargs)
        self.collection_name = "contact"
        logger.info(f"Initialized ContactMemory with max_items={max_items}")

    @log_function()
    async def add_contact(
        self,
        email: str,
        name: str | None = None,
        phone: str | None = None,
        organization: str | None = None,
        title: str | None = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: str | None = None,
        **kwargs,
    ) -> str:
        """
        Add or update a contact record.

        Handles contact deduplication by email address with
        incremental information enrichment. If contact exists, updates
        with new information while preserving interaction history.

        Args:
            email: Contact's email address (primary identifier)
            name: Full contact name
            phone: Phone number
            organization: Company or organization name
            title: title or position
            contact_type: contact classification
            confidence: Information accuracy confidence level
            source_email_id: Email ID where contact was discovered
            **kwargs: Additional contact attributes for enrichment

        Returns:
            Contact ID (existing or newly created)

        Raises:
            ValueError: If email address invalid or missing

        Example:
            >>> contact_id = await contact_memory.add_contact(
            ...     email="john.doe@investment.com",
            ...     name="John Doe",
            ...     organization="Investment Partners LLC",
            ...     title="Managing Partner",
            ...     contact_type=ContactType.PROFESSIONAL,
            ...     confidence=ContactConfidence.HIGH
            ... )
        """
        if not email or not isinstance(email, str) or "@" not in email:
            raise ValueError("Valid email address required for contact creation")

        logger.info(f"Adding/updating contact: {email}")
        await self._ensure_collection()

        # Check for existing contact by email
        existing = await self.find_contact_by_email(email)

        if existing:
            logger.debug(f"Updating existing contact: {email}")
            return await self._update_existing_contact(
                existing,
                name,
                phone,
                organization,
                title,
                contact_type,
                confidence,
                source_email_id,
                **kwargs,
            )
        else:
            logger.debug(f"Creating new contact: {email}")
            return await self._create_new_contact(
                email,
                name,
                phone,
                organization,
                title,
                contact_type,
                confidence,
                source_email_id,
                **kwargs,
            )

    @log_function()
    async def _create_new_contact(
        self,
        email: str,
        name: str | None = None,
        phone: str | None = None,
        organization: str | None = None,
        title: str | None = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: str | None = None,
        **kwargs,
    ) -> str:
        """
        Create new contact record with complete initialization.

        Args:
            email: Contact email address
            name: Full contact name
            phone: Phone number
            organization: Organization name
            title: title
            contact_type: Contact classification
            confidence: Information confidence level
            source_email_id: Source email identifier
            **kwargs: Additional contact attributes

        Returns:
            Newly created contact ID
        """
        contact_id = str(uuid.uuid4())

        # Parse name into components if provided
        first_name, last_name = None, None
        if name:
            name_parts = name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            elif len(name_parts) == 1:
                first_name = name_parts[0]

        # Create contact record
        contact = ContactRecord(
            id=contact_id,
            email=email.lower().strip(),
            name=name,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            organization=organization,
            title=title,
            contact_type=contact_type,
            confidence=confidence,
            email_count=1 if source_email_id else 0,
            **kwargs,
        )

        # Add source tracking
        if source_email_id:
            contact.sources.append(source_email_id)
            contact.last_email_interaction = datetime.now(UTC).isoformat()

        # Record extraction history
        extraction_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "source_email_id": source_email_id,
            "extracted_fields": {
                "name": name,
                "phone": phone,
                "organization": organization,
                "title": title,
            },
            "confidence": confidence.value,
            "action": "created",
        }
        contact.extraction_history.append(extraction_record)

        # Store in vector database
        search_text = contact.get_search_text()
        memory_item = MemoryItem(
            id=contact_id, content=search_text, metadata=contact.to_dict()
        )

        await super().add(memory_item.content, memory_item.metadata)

        logger.info(f"Created new contact: {email} (ID: {contact_id})")
        return contact_id

    @log_function()
    async def _update_existing_contact(
        self,
        existing: ContactRecord,
        name: str | None = None,
        phone: str | None = None,
        organization: str | None = None,
        title: str | None = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: str | None = None,
        **kwargs,
    ) -> str:
        """
        Update existing contact with new information and enrichment.

        Performs merging of contact information with
        confidence-based field updating and interaction tracking.

        Args:
            existing: Existing contact record
            name: Updated name information
            phone: Updated phone number
            organization: Updated organization
            title: Updated title
            contact_type: Updated contact type
            confidence: Information confidence level
            source_email_id: Source email for this update
            **kwargs: Additional fields to update

        Returns:
            Updated contact ID
        """
        updated = False
        changes = []

        # Update name if provided and confidence allows
        if (
            name
            and (not existing.name or confidence.value >= existing.confidence.value)
            and existing.name != name
        ):
            existing.name = name
            # Update name components
            name_parts = name.strip().split()
            if len(name_parts) >= 2:
                existing.first_name = name_parts[0]
                existing.last_name = " ".join(name_parts[1:])
            elif len(name_parts) == 1:
                existing.first_name = name_parts[0]
            changes.append(f"name: '{existing.name}' -> '{name}'")
            updated = True

        # Update phone if provided and higher confidence
        if (
            phone
            and (not existing.phone or confidence.value >= existing.confidence.value)
            and existing.phone != phone
        ):
            changes.append(f"phone: '{existing.phone}' -> '{phone}'")
            existing.phone = phone
            updated = True

        # Update organization with confidence comparison
        if (
            organization
            and (
                not existing.organization
                or confidence.value >= existing.confidence.value
            )
            and existing.organization != organization
        ):
            changes.append(
                f"organization: '{existing.organization}' -> '{organization}'"
            )
            existing.organization = organization
            updated = True

        # Update title with confidence comparison
        if (
            title
            and (not existing.title or confidence.value >= existing.confidence.value)
            and existing.title != title
        ):
            changes.append(f"title: '{existing.title}' -> '{title}'")
            existing.title = title
            updated = True

        # Update contact type if higher confidence
        if (
            contact_type != ContactType.UNKNOWN
            and confidence.value >= existing.confidence.value
        ) and existing.contact_type != contact_type:
            changes.append(
                f"contact_type: {existing.contact_type.value} -> {contact_type.value}"
            )
            existing.contact_type = contact_type
            updated = True

        # Update confidence if higher
        if confidence.value > existing.confidence.value:
            changes.append(
                f"confidence: {existing.confidence.value} -> {confidence.value}"
            )
            existing.confidence = confidence
            updated = True

        # Update interaction tracking
        if source_email_id:
            if source_email_id not in existing.sources:
                existing.sources.append(source_email_id)
                updated = True
            existing.email_count += 1
            existing.last_email_interaction = datetime.now(UTC).isoformat()
            updated = True

        # Apply additional kwargs updates
        for key, value in kwargs.items():
            if hasattr(existing, key) and getattr(existing, key) != value:
                setattr(existing, key, value)
                changes.append(f"{key}: updated")
                updated = True

        if updated:
            existing.last_updated = datetime.now(UTC).isoformat()

            # Record extraction history
            extraction_record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "source_email_id": source_email_id,
                "changes": changes,
                "confidence": confidence.value,
                "action": "updated",
            }
            existing.extraction_history.append(extraction_record)

            # Update in database
            search_text = existing.get_search_text()
            memory_item = MemoryItem(
                id=existing.id, content=search_text, metadata=existing.to_dict()
            )

            await super().update(existing.id, memory_item.content, memory_item.metadata)

            logger.info(f"Updated contact {existing.email}: {len(changes)} changes")
            logger.debug(f"Contact changes: {changes}")
        else:
            logger.debug(f"No updates needed for contact: {existing.email}")

        return existing.id

    @log_function()
    async def find_contact_by_email(self, email: str) -> ContactRecord | None:
        """
        Find contact by email address (primary key lookup).

        Performs exact email address matching for contact retrieval
        with proper email normalization and case handling.

        Args:
            email: Email address to search for

        Returns:
            Contact record if found, None otherwise

        Example:
            >>> contact = await contact_memory.find_contact_by_email("john@company.com")
            >>> if contact:
            ...     print(f"Found: {contact.name} at {contact.organization}")
        """
        if not email:
            return None

        normalized_email = email.lower().strip()
        logger.debug(f"Searching for contact by email: {normalized_email}")

        try:
            # Search using exact email match filter
            filter_condition = {
                "key": "metadata.email",
                "match": {"value": normalized_email},
            }

            results = await super().search(
                query=normalized_email, limit=1, filter_conditions=filter_condition
            )

            if results:
                contact_data = results[0].metadata
                contact = ContactRecord.from_dict(contact_data)
                logger.debug(f"Found contact: {contact.name} ({contact.email})")
                return contact

            logger.debug(f"No contact found for email: {normalized_email}")
            return None

        except Exception as e:
            logger.error(f"Error finding contact by email {normalized_email}: {e}")
            return None

    @log_function()
    async def search_contacts(
        self,
        query: str,
        limit: int = 10,
        contact_type: ContactType | None = None,
        min_confidence: ContactConfidence | None = None,
        organization: str | None = None,
    ) -> list[ContactRecord]:
        """
        Search contacts with semantic and categorical filtering.

        Performs complete contact search combining semantic vector
        search with categorical filters for contact discovery.

        Args:
            query: Search query text (names, organizations, titles, etc.)
            limit: Maximum number of results to return
            contact_type: Filter by specific contact type
            min_confidence: Minimum confidence level filter
            organization: Filter by organization name

        Returns:
            List of matching contact records ordered by relevance

        Example:
            >>> # Search for investment professionals
            >>> contacts = await contact_memory.search_contacts(
            ...     query="investment managing partner",
            ...     contact_type=ContactType.PROFESSIONAL,
            ...     min_confidence=ContactConfidence.MEDIUM
            ... )
        """
        logger.info(f"Searching contacts: query='{query}', limit={limit}")

        try:
            # Build filter conditions
            filter_conditions = {"must": []}

            # Contact type filter
            if contact_type:
                filter_conditions["must"].append(
                    {
                        "key": "metadata.contact_type",
                        "match": {"value": contact_type.value},
                    }
                )

            # Minimum confidence filter
            if min_confidence:
                confidence_values = [conf.value for conf in ContactConfidence]
                min_index = confidence_values.index(min_confidence.value)
                allowed_values = confidence_values[min_index:]

                filter_conditions["must"].append(
                    {"key": "metadata.confidence", "match": {"any": allowed_values}}
                )

            # Organization filter
            if organization:
                filter_conditions["must"].append(
                    {"key": "metadata.organization", "match": {"text": organization}}
                )

            # Remove empty filter if no conditions
            search_filter = filter_conditions if filter_conditions["must"] else None

            # Perform semantic search
            results = await super().search(
                query=query, limit=limit, filter=search_filter
            )

            # Convert to contact records
            contacts = []
            for result in results:
                try:
                    contact = ContactRecord.from_dict(result.metadata)
                    contacts.append(contact)
                except Exception as e:
                    logger.warning(f"Error converting search result to contact: {e}")
                    continue

            logger.info(f"Found {len(contacts)} contacts matching search criteria")
            return contacts

        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return []

    @log_function()
    async def get_contact_by_id(self, contact_id: str) -> ContactRecord | None:
        """
        Retrieve contact by unique identifier.

        Args:
            contact_id: Unique contact identifier

        Returns:
            Contact record if found, None otherwise
        """
        logger.debug(f"Retrieving contact by ID: {contact_id}")

        try:
            memory_item = await super().get_item(contact_id)
            if memory_item:
                contact = ContactRecord.from_dict(memory_item.metadata)
                return contact
            return None
        except Exception as e:
            logger.error(f"Error retrieving contact {contact_id}: {e}")
            return None

    @log_function()
    async def get_all_contacts(
        self, limit: int = 100, contact_type: ContactType | None = None
    ) -> list[ContactRecord]:
        """
        Retrieve all contacts with optional filtering.

        Args:
            limit: Maximum number of contacts to return
            contact_type: Optional contact type filter

        Returns:
            List of contact records
        """
        logger.info(f"Retrieving all contacts (limit={limit}, type={contact_type})")

        try:
            # Build filter if contact type specified
            search_filter = None
            if contact_type:
                search_filter = {
                    "key": "metadata.contact_type",
                    "match": {"value": contact_type.value},
                }

            # Get all items with optional filter
            results = await super().search(
                query="*", limit=limit, filter=search_filter  # Match all
            )

            contacts = []
            for result in results:
                try:
                    contact = ContactRecord.from_dict(result.metadata)
                    contacts.append(contact)
                except Exception as e:
                    logger.warning(f"Error converting result to contact: {e}")
                    continue

            logger.info(f"Retrieved {len(contacts)} contacts")
            return contacts

        except Exception as e:
            logger.error(f"Error retrieving all contacts: {e}")
            return []

    @log_function()
    async def delete_contact(self, contact_id: str) -> bool:
        """
        Delete contact by ID.

        Args:
            contact_id: Contact identifier to delete

        Returns:
            True if deletion successful, False otherwise
        """
        logger.info(f"Deleting contact: {contact_id}")

        try:
            success = await super().delete_item(contact_id)
            if success:
                logger.info(f"Successfully deleted contact: {contact_id}")
            else:
                logger.warning(f"Contact not found for deletion: {contact_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting contact {contact_id}: {e}")
            return False

    @log_function()
    async def update_contact_relationship(
        self, contact_id: str, relationship: str, notes: str | None = None
    ) -> bool:
        """
        Update contact relationship and business context.

        Args:
            contact_id: Contact identifier
            relationship: Business relationship description
            notes: Additional context notes

        Returns:
            True if update successful, False otherwise
        """
        logger.info(f"Updating relationship for contact: {contact_id}")

        try:
            contact = await self.get_contact_by_id(contact_id)
            if not contact:
                logger.warning(
                    f"Contact not found for relationship update: {contact_id}"
                )
                return False

            # Update relationship information
            contact.relationship = relationship
            if notes:
                contact.notes = (
                    notes if not contact.notes else f"{contact.notes}\n{notes}"
                )
            contact.last_updated = datetime.now(UTC).isoformat()

            # Record in extraction history
            extraction_record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": "relationship_updated",
                "relationship": relationship,
                "notes": notes,
            }
            contact.extraction_history.append(extraction_record)

            # Update in database
            search_text = contact.get_search_text()
            memory_item = MemoryItem(
                id=contact.id, content=search_text, metadata=contact.to_dict()
            )

            await super().update_item(contact_id, memory_item)

            logger.info(
                f"Updated relationship for contact {contact.email}: {relationship}"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating contact relationship: {e}")
            return False

    @log_function()
    async def add_contact_tag(self, contact_id: str, tag: str) -> bool:
        """
        Add categorization tag to contact.

        Args:
            contact_id: Contact identifier
            tag: Tag to add for categorization

        Returns:
            True if tag added successfully, False otherwise
        """
        logger.debug(f"Adding tag '{tag}' to contact: {contact_id}")

        try:
            contact = await self.get_contact_by_id(contact_id)
            if not contact:
                logger.warning(f"Contact not found for tag addition: {contact_id}")
                return False

            # Add tag if not already present
            if tag not in contact.tags:
                contact.tags.append(tag)
                contact.last_updated = datetime.now(UTC).isoformat()

                # Update in database
                search_text = contact.get_search_text()
                memory_item = MemoryItem(
                    id=contact.id, content=search_text, metadata=contact.to_dict()
                )

                await super().update_item(contact_id, memory_item)

                logger.info(f"Added tag '{tag}' to contact {contact.email}")
                return True
            else:
                logger.debug(f"Tag '{tag}' already exists for contact {contact.email}")
                return True

        except Exception as e:
            logger.error(f"Error adding tag to contact: {e}")
            return False

    @log_function()
    async def record_email_interaction(self, email: str, email_id: str) -> bool:
        """
        Record email interaction for contact tracking.

        Updates interaction frequency and recency tracking for
        business intelligence and relationship management.

        Args:
            email: Contact email address
            email_id: Email message identifier

        Returns:
            True if interaction recorded successfully, False otherwise
        """
        logger.debug(f"Recording email interaction: {email} <- {email_id}")

        try:
            contact = await self.find_contact_by_email(email)
            if not contact:
                logger.debug(f"No existing contact found for interaction: {email}")
                return False

            # Update interaction tracking
            if email_id not in contact.sources:
                contact.sources.append(email_id)
            contact.email_count += 1
            contact.last_email_interaction = datetime.now(UTC).isoformat()
            contact.last_updated = datetime.now(UTC).isoformat()

            # Update in database
            search_text = contact.get_search_text()
            memory_item = MemoryItem(
                id=contact.id, content=search_text, metadata=contact.to_dict()
            )

            await super().update_item(contact.id, memory_item)

            logger.debug(
                f"Recorded interaction for {email} (total: {contact.email_count})"
            )
            return True

        except Exception as e:
            logger.error(f"Error recording email interaction: {e}")
            return False

    @log_function()
    async def get_sender_context(self, email_address: str) -> dict[str, Any]:
        """
        Get comprehensive context information for a specific sender.

        Retrieves complete sender information from contact memory including
        trust scores, relationship context, and communication patterns for
        asset management decision making.

        Args:
            email_address: Email address to get context for

        Returns:
            Dictionary containing comprehensive sender context

        Raises:
            ValueError: If email_address is empty or invalid

        Example:
            >>> context = await contact_memory.get_sender_context("john@blackstone.com")
            >>> print(context['trust_score'])  # 0.89
            >>> print(context['organization'])  # 'Blackstone Group'
        """
        if not email_address or not isinstance(email_address, str):
            raise ValueError("Email address must be a non-empty string")

        email_address = email_address.lower().strip()
        logger.info(f"Getting sender context for: {email_address}")

        try:
            # Get contact record
            contact = await self.find_contact_by_email(email_address)

            if not contact:
                logger.info(
                    f"No contact found for {email_address}, creating basic context"
                )
                return {
                    "email": email_address,
                    "contact_found": False,
                    "trust_score": config.default_sender_trust_score,
                    "organization": self._extract_domain_organization(email_address),
                    "contact_type": "unknown",
                    "confidence": "low",
                    "relationship": None,
                    "interaction_frequency": 0,
                    "last_interaction": None,
                    "tags": [],
                    "communication_patterns": {},
                    "risk_indicators": [],
                }

            # Calculate trust score based on contact information
            trust_score = self._calculate_sender_trust_score(contact)

            # Analyze communication patterns
            communication_patterns = self._analyze_communication_patterns(contact)

            # Identify risk indicators
            risk_indicators = self._identify_risk_indicators(contact, email_address)

            context = {
                "email": email_address,
                "contact_found": True,
                "contact_id": contact.id,
                "name": contact.name,
                "organization": contact.organization,
                "title": contact.title,
                "contact_type": contact.contact_type.value,
                "confidence": contact.confidence.value,
                "relationship": contact.relationship,
                "trust_score": trust_score,
                "interaction_frequency": contact.email_count,
                "last_interaction": contact.last_email_interaction,
                "first_seen": contact.first_seen,
                "tags": contact.tags,
                "communication_patterns": communication_patterns,
                "risk_indicators": risk_indicators,
                "notes": contact.notes,
            }

            logger.info(
                f"Sender context for {email_address}: trust_score={trust_score:.2f}, type={contact.contact_type.value}"
            )
            return context

        except Exception as e:
            logger.error(f"Failed to get sender context for {email_address}: {e}")
            return {
                "email": email_address,
                "contact_found": False,
                "trust_score": 0.0,
                "error": str(e),
            }

    @log_function()
    async def get_organization_patterns(self, organization: str) -> dict[str, Any]:
        """
        Get communication and document patterns for an organization.

        Analyzes patterns across all contacts from a specific organization
        to identify organizational communication preferences and document types.

        Args:
            organization: Organization name to analyze patterns for

        Returns:
            Dictionary containing organization patterns and insights

        Raises:
            ValueError: If organization is empty or invalid

        Example:
            >>> patterns = await contact_memory.get_organization_patterns("Blackstone Group")
            >>> print(patterns['total_contacts'])  # 12
            >>> print(patterns['common_document_types'])  # ['financial_statements', 'reports']
        """
        if not organization or not isinstance(organization, str):
            raise ValueError("Organization must be a non-empty string")

        organization = organization.strip()
        logger.info(f"Analyzing organization patterns for: {organization}")

        try:
            # Find all contacts from the organization
            org_contacts = await self.search_contacts(
                query=organization,
                organization=organization,
                limit=config.max_organization_contacts,
            )

            if not org_contacts:
                logger.info(f"No contacts found for organization: {organization}")
                return {
                    "organization": organization,
                    "total_contacts": 0,
                    "patterns": {},
                    "insights": [],
                }

            # Analyze patterns across organization contacts
            patterns = {
                "organization": organization,
                "total_contacts": len(org_contacts),
                "contact_types": {},
                "title_patterns": {},
                "communication_frequency": {},
                "trust_distribution": {},
                "common_tags": {},
                "relationship_types": {},
                "average_trust_score": 0.0,
                "most_active_contacts": [],
                "communication_insights": [],
            }

            # Analyze contact patterns
            total_interactions = 0
            trust_scores = []

            for contact in org_contacts:
                # Contact type distribution
                contact_type = contact.contact_type.value
                patterns["contact_types"][contact_type] = (
                    patterns["contact_types"].get(contact_type, 0) + 1
                )

                # Title patterns
                if contact.title:
                    patterns["title_patterns"][contact.title] = (
                        patterns["title_patterns"].get(contact.title, 0) + 1
                    )

                # Communication frequency
                total_interactions += contact.email_count

                # Trust score calculation
                trust_score = self._calculate_sender_trust_score(contact)
                trust_scores.append(trust_score)

                # Relationship types
                if contact.relationship:
                    patterns["relationship_types"][contact.relationship] = (
                        patterns["relationship_types"].get(contact.relationship, 0) + 1
                    )

                # Common tags
                for tag in contact.tags:
                    patterns["common_tags"][tag] = (
                        patterns["common_tags"].get(tag, 0) + 1
                    )

            # Calculate aggregate metrics
            patterns["total_interactions"] = total_interactions
            patterns["average_interactions_per_contact"] = (
                total_interactions / len(org_contacts) if org_contacts else 0
            )
            patterns["average_trust_score"] = (
                sum(trust_scores) / len(trust_scores) if trust_scores else 0.0
            )

            # Find most active contacts
            sorted_contacts = sorted(
                org_contacts, key=lambda c: c.email_count, reverse=True
            )
            patterns["most_active_contacts"] = [
                {
                    "name": contact.name,
                    "email": contact.email,
                    "title": contact.title,
                    "interaction_count": contact.email_count,
                }
                for contact in sorted_contacts[:5]  # Top 5 most active
            ]

            # Generate insights
            insights = []

            if patterns["average_trust_score"] > 0.7:
                insights.append("High trust organization - above average reliability")
            elif patterns["average_trust_score"] < 0.4:
                insights.append(
                    "Low trust organization - requires additional verification"
                )

            if total_interactions > 50:
                insights.append("High interaction volume - established relationship")

            most_common_type = (
                max(patterns["contact_types"], key=patterns["contact_types"].get)
                if patterns["contact_types"]
                else None
            )
            if most_common_type:
                insights.append(f"Primary contact type: {most_common_type}")

            patterns["insights"] = insights

            logger.info(
                f"Organization pattern analysis complete for {organization}: {len(org_contacts)} contacts, avg trust={patterns['average_trust_score']:.2f}"
            )
            return patterns

        except Exception as e:
            logger.error(
                f"Failed to analyze organization patterns for {organization}: {e}"
            )
            return {"organization": organization, "total_contacts": 0, "error": str(e)}

    @log_function()
    async def evaluate_sender_trust(
        self, sender_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Evaluate sender trustworthiness based on multiple factors.

        Performs comprehensive trust evaluation considering contact history,
        organization reputation, communication patterns, and verification status.

        Args:
            sender_data: Dictionary containing sender information

        Returns:
            Dictionary containing trust evaluation results

        Raises:
            ValueError: If sender_data is empty or missing required fields

        Example:
            >>> trust_eval = await contact_memory.evaluate_sender_trust({
            ...     "email": "john@blackstone.com",
            ...     "organization": "Blackstone Group",
            ...     "domain": "blackstone.com"
            ... })
            >>> print(trust_eval['overall_score'])  # 0.87
        """
        if not sender_data or not isinstance(sender_data, dict):
            raise ValueError("Sender data must be a non-empty dictionary")

        if "email" not in sender_data:
            raise ValueError("Sender data must include email address")

        email = sender_data["email"]
        logger.info(f"Evaluating sender trust for: {email}")

        try:
            # Get existing contact context
            contact = await self.find_contact_by_email(email)

            # Initialize trust evaluation
            trust_evaluation = {
                "email": email,
                "overall_score": 0.0,
                "factors": {
                    "contact_history": 0.0,
                    "organization_reputation": 0.0,
                    "communication_patterns": 0.0,
                    "verification_status": 0.0,
                    "domain_reputation": 0.0,
                },
                "risk_flags": [],
                "confidence": "low",
                "recommendation": "manual_review",
            }

            # Factor 1: Contact History (30% weight)
            if contact:
                history_score = self._evaluate_contact_history(contact)
                trust_evaluation["factors"]["contact_history"] = history_score
            else:
                trust_evaluation["risk_flags"].append("no_previous_contact_history")

            # Factor 2: Organization Reputation (25% weight)
            organization = sender_data.get("organization") or (
                contact.organization if contact else None
            )
            if organization:
                org_score = await self._evaluate_organization_reputation(organization)
                trust_evaluation["factors"]["organization_reputation"] = org_score
            else:
                trust_evaluation["risk_flags"].append("unknown_organization")

            # Factor 3: Communication Patterns (20% weight)
            if contact:
                comm_score = self._evaluate_communication_patterns(contact)
                trust_evaluation["factors"]["communication_patterns"] = comm_score
            else:
                trust_evaluation["risk_flags"].append("no_communication_patterns")

            # Factor 4: Verification Status (15% weight)
            if contact:
                verification_score = self._evaluate_verification_status(contact)
                trust_evaluation["factors"]["verification_status"] = verification_score
            else:
                trust_evaluation["risk_flags"].append("unverified_contact")

            # Factor 5: Domain Reputation (10% weight)
            domain = (
                sender_data.get("domain") or email.split("@")[1]
                if "@" in email
                else None
            )
            if domain:
                domain_score = self._evaluate_domain_reputation(domain)
                trust_evaluation["factors"]["domain_reputation"] = domain_score
            else:
                trust_evaluation["risk_flags"].append("invalid_email_domain")

            # Calculate overall trust score (weighted)
            weights = {
                "contact_history": 0.30,
                "organization_reputation": 0.25,
                "communication_patterns": 0.20,
                "verification_status": 0.15,
                "domain_reputation": 0.10,
            }

            overall_score = sum(
                trust_evaluation["factors"][factor] * weight
                for factor, weight in weights.items()
            )
            trust_evaluation["overall_score"] = overall_score

            # Determine confidence and recommendation
            if overall_score >= 0.8:
                trust_evaluation["confidence"] = "high"
                trust_evaluation["recommendation"] = "auto_approve"
            elif overall_score >= 0.6:
                trust_evaluation["confidence"] = "medium"
                trust_evaluation["recommendation"] = "conditional_approve"
            elif overall_score >= 0.4:
                trust_evaluation["confidence"] = "low"
                trust_evaluation["recommendation"] = "manual_review"
            else:
                trust_evaluation["confidence"] = "very_low"
                trust_evaluation["recommendation"] = "reject_or_quarantine"

            logger.info(
                f"Trust evaluation for {email}: score={overall_score:.2f}, recommendation={trust_evaluation['recommendation']}"
            )
            return trust_evaluation

        except Exception as e:
            logger.error(f"Failed to evaluate sender trust for {email}: {e}")
            return {
                "email": email,
                "overall_score": 0.0,
                "error": str(e),
                "recommendation": "manual_review",
            }

    @log_function()
    async def get_sender_document_patterns(
        self, email_address: str
    ) -> list[dict[str, Any]]:
        """
        Get document classification patterns for a specific sender.

        Analyzes historical document types and classification patterns
        from a specific sender to support current classification decisions.

        Args:
            email_address: Email address to analyze document patterns for

        Returns:
            List of document pattern insights and preferences

        Raises:
            ValueError: If email_address is empty or invalid

        Example:
            >>> patterns = await contact_memory.get_sender_document_patterns("john@blackstone.com")
            >>> for pattern in patterns:
            ...     print(f"{pattern['document_type']}: {pattern['frequency']}")
        """
        if not email_address or not isinstance(email_address, str):
            raise ValueError("Email address must be a non-empty string")

        email_address = email_address.lower().strip()
        logger.info(f"Analyzing document patterns for sender: {email_address}")

        try:
            # Get contact information
            contact = await self.find_contact_by_email(email_address)

            if not contact:
                logger.info(
                    f"No contact found for {email_address}, no document patterns available"
                )
                return []

            # Extract document patterns from contact history
            document_patterns = []

            # Analyze extraction history for document types
            document_types = {}
            for history_entry in contact.extraction_history:
                if "document_type" in history_entry:
                    doc_type = history_entry["document_type"]
                    document_types[doc_type] = document_types.get(doc_type, 0) + 1

            # Create pattern entries
            total_documents = sum(document_types.values()) if document_types else 0

            for doc_type, count in document_types.items():
                pattern = {
                    "sender_email": email_address,
                    "document_type": doc_type,
                    "frequency": count,
                    "percentage": (
                        (count / total_documents * 100) if total_documents > 0 else 0
                    ),
                    "confidence": (
                        "high" if count >= 5 else "medium" if count >= 2 else "low"
                    ),
                    "last_seen": None,  # Would be populated from actual document history
                }
                document_patterns.append(pattern)

            # Sort by frequency
            document_patterns.sort(key=lambda x: x["frequency"], reverse=True)

            # Add organizational patterns if available
            if contact.organization:
                org_patterns = await self._get_organization_document_patterns(
                    contact.organization
                )
                for org_pattern in org_patterns:
                    org_pattern["source"] = "organization_pattern"
                    document_patterns.append(org_pattern)

            logger.info(
                f"Found {len(document_patterns)} document patterns for {email_address}"
            )
            return document_patterns

        except Exception as e:
            logger.error(
                f"Failed to get sender document patterns for {email_address}: {e}"
            )
            return []

    @log_function()
    async def get_organization_asset_relationships(
        self, organization: str
    ) -> list[dict[str, Any]]:
        """
        Get asset relationships and context for an organization.

        Analyzes relationships between an organization and specific assets
        based on contact interactions and business context.

        Args:
            organization: Organization name to analyze asset relationships for

        Returns:
            List of asset relationship insights and connections

        Raises:
            ValueError: If organization is empty or invalid

        Example:
            >>> relationships = await contact_memory.get_organization_asset_relationships("Blackstone Group")
            >>> for rel in relationships:
            ...     print(f"Asset: {rel['asset_id']}, Relationship: {rel['relationship_type']}")
        """
        if not organization or not isinstance(organization, str):
            raise ValueError("Organization must be a non-empty string")

        organization = organization.strip()
        logger.info(f"Analyzing asset relationships for organization: {organization}")

        try:
            # Get all contacts from the organization
            org_contacts = await self.search_contacts(
                query=organization,
                organization=organization,
                limit=config.max_organization_contacts,
            )

            if not org_contacts:
                logger.info(f"No contacts found for organization: {organization}")
                return []

            asset_relationships = []
            asset_interactions = {}

            # Analyze contact interactions for asset references
            for contact in org_contacts:
                # Extract asset references from contact tags
                for tag in contact.tags:
                    if self._is_asset_related_tag(tag):
                        asset_id = self._extract_asset_id_from_tag(tag)
                        if asset_id:
                            if asset_id not in asset_interactions:
                                asset_interactions[asset_id] = {
                                    "asset_id": asset_id,
                                    "contacts": [],
                                    "total_interactions": 0,
                                    "relationship_types": set(),
                                    "first_interaction": None,
                                    "last_interaction": None,
                                }

                            asset_interactions[asset_id]["contacts"].append(
                                {
                                    "name": contact.name,
                                    "email": contact.email,
                                    "title": contact.title,
                                    "interaction_count": contact.email_count,
                                }
                            )
                            asset_interactions[asset_id][
                                "total_interactions"
                            ] += contact.email_count

                            if contact.relationship:
                                asset_interactions[asset_id]["relationship_types"].add(
                                    contact.relationship
                                )

            # Convert to relationship list
            for asset_id, interaction_data in asset_interactions.items():
                relationship = {
                    "organization": organization,
                    "asset_id": asset_id,
                    "relationship_type": self._determine_primary_relationship(
                        interaction_data["relationship_types"]
                    ),
                    "contact_count": len(interaction_data["contacts"]),
                    "total_interactions": interaction_data["total_interactions"],
                    "key_contacts": interaction_data["contacts"][:3],  # Top 3 contacts
                    "relationship_strength": self._calculate_relationship_strength(
                        interaction_data
                    ),
                    "confidence": (
                        "high"
                        if interaction_data["total_interactions"] >= 10
                        else (
                            "medium"
                            if interaction_data["total_interactions"] >= 3
                            else "low"
                        )
                    ),
                }
                asset_relationships.append(relationship)

            # Sort by relationship strength
            asset_relationships.sort(
                key=lambda x: x["relationship_strength"], reverse=True
            )

            logger.info(
                f"Found {len(asset_relationships)} asset relationships for {organization}"
            )
            return asset_relationships

        except Exception as e:
            logger.error(
                f"Failed to get organization asset relationships for {organization}: {e}"
            )
            return []

    # Helper methods for trust evaluation and pattern analysis

    def _extract_domain_organization(self, email: str) -> str:
        """Extract organization name from email domain."""
        if "@" not in email:
            return "unknown"

        domain = email.split("@")[1].lower()
        # Simple domain to organization mapping
        domain_mapping = {
            "blackstone.com": "Blackstone Group",
            "kkr.com": "KKR & Co",
            "apolloglobal.com": "Apollo Global Management",
            "carlyle.com": "The Carlyle Group",
            "tpg.com": "TPG Inc",
        }

        return domain_mapping.get(
            domain, domain.replace(".com", "").replace(".", " ").title()
        )

    def _calculate_sender_trust_score(self, contact: ContactRecord) -> float:
        """Calculate trust score based on contact information."""
        score = 0.0

        # Base score from confidence
        confidence_scores = {
            ContactConfidence.HIGH: 0.4,
            ContactConfidence.MEDIUM: 0.25,
            ContactConfidence.LOW: 0.1,
        }
        score += confidence_scores.get(contact.confidence, 0.0)

        # Interaction frequency bonus
        if contact.email_count >= 10:
            score += 0.3
        elif contact.email_count >= 5:
            score += 0.2
        elif contact.email_count >= 2:
            score += 0.1

        # Professional contact bonus
        if contact.contact_type == ContactType.PROFESSIONAL:
            score += 0.2

        # Known organization bonus
        if contact.organization and len(contact.organization) > 3:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _analyze_communication_patterns(self, contact: ContactRecord) -> dict[str, Any]:
        """Analyze communication patterns for a contact."""
        return {
            "interaction_frequency": contact.email_count,
            "consistency": "regular" if contact.email_count >= 5 else "occasional",
            "recency": "recent" if contact.last_email_interaction else "old",
            "pattern_confidence": "high" if contact.email_count >= 10 else "low",
        }

    def _identify_risk_indicators(
        self, contact: ContactRecord, email: str
    ) -> list[str]:
        """Identify potential risk indicators for a contact."""
        risks = []

        if contact.confidence == ContactConfidence.LOW:
            risks.append("low_confidence_contact")

        if contact.email_count == 0:
            risks.append("no_interaction_history")

        if not contact.organization:
            risks.append("unknown_organization")

        # Check for suspicious domains
        domain = email.split("@")[1] if "@" in email else ""
        suspicious_domains = ["tempmail", "guerrilla", "10minutemail"]
        if any(suspicious in domain for suspicious in suspicious_domains):
            risks.append("suspicious_email_domain")

        return risks

    def _evaluate_contact_history(self, contact: ContactRecord) -> float:
        """Evaluate contact history factor for trust scoring."""
        if contact.email_count >= 20:
            return 1.0
        elif contact.email_count >= 10:
            return 0.8
        elif contact.email_count >= 5:
            return 0.6
        elif contact.email_count >= 2:
            return 0.4
        elif contact.email_count >= 1:
            return 0.2
        else:
            return 0.0

    async def _evaluate_organization_reputation(self, organization: str) -> float:
        """Evaluate organization reputation factor."""
        # Known reputable organizations
        reputable_orgs = [
            "blackstone",
            "kkr",
            "apollo",
            "carlyle",
            "tpg",
            "bain capital",
            "warburg pincus",
            "general atlantic",
            "silver lake",
        ]

        org_lower = organization.lower()
        if any(known in org_lower for known in reputable_orgs):
            return 1.0

        # Check if we have multiple contacts from this organization
        org_contacts = await self.search_contacts(
            query=organization, organization=organization, limit=10
        )
        if len(org_contacts) >= 5:
            return 0.8
        elif len(org_contacts) >= 2:
            return 0.6
        else:
            return 0.3

    def _evaluate_communication_patterns(self, contact: ContactRecord) -> float:
        """Evaluate communication patterns factor."""
        if contact.email_count >= 10:
            return 1.0
        elif contact.email_count >= 5:
            return 0.7
        elif contact.email_count >= 2:
            return 0.5
        else:
            return 0.2

    def _evaluate_verification_status(self, contact: ContactRecord) -> float:
        """Evaluate verification status factor."""
        confidence_scores = {
            ContactConfidence.HIGH: 1.0,
            ContactConfidence.MEDIUM: 0.7,
            ContactConfidence.LOW: 0.3,
        }
        return confidence_scores.get(contact.confidence, 0.0)

    def _evaluate_domain_reputation(self, domain: str) -> float:
        """Evaluate domain reputation factor."""
        # Known business domains
        business_domains = [".com", ".org", ".net", ".edu", ".gov"]

        # Suspicious domain patterns
        suspicious_patterns = ["tempmail", "guerrilla", "10minute", "throwaway"]

        if any(suspicious in domain.lower() for suspicious in suspicious_patterns):
            return 0.0

        if any(domain.endswith(biz_domain) for biz_domain in business_domains):
            return 0.8

        return 0.5  # Neutral for unknown domains

    async def _get_organization_document_patterns(
        self, organization: str
    ) -> list[dict[str, Any]]:
        """Get document patterns for an organization."""
        # This would typically query episodic memory for document patterns
        # For now, return basic organizational patterns
        return [
            {
                "document_type": "financial_statements",
                "frequency": 5,
                "percentage": 40.0,
                "confidence": "medium",
                "source": "organization_pattern",
            }
        ]

    def _is_asset_related_tag(self, tag: str) -> bool:
        """Check if a tag is asset-related."""
        asset_keywords = ["asset", "deal", "investment", "property", "fund"]
        return any(keyword in tag.lower() for keyword in asset_keywords)

    def _extract_asset_id_from_tag(self, tag: str) -> str | None:
        """Extract asset ID from a tag if present."""
        # Simple pattern matching for asset IDs in tags
        # # Standard library imports
        import re

        asset_pattern = r"(asset_|deal_|prop_)([A-Z0-9_]+)"
        match = re.search(asset_pattern, tag, re.IGNORECASE)
        return match.group(0) if match else None

    def _determine_primary_relationship(self, relationship_types: set[str]) -> str:
        """Determine primary relationship type from a set."""
        if not relationship_types:
            return "unknown"

        # Priority order for relationship types
        priority = [
            "counterparty",
            "investor",
            "strategic_partner",
            "vendor",
            "colleague",
        ]

        for rel_type in priority:
            if rel_type in relationship_types:
                return rel_type

        return list(relationship_types)[0]  # Return first if no priority match

    def _calculate_relationship_strength(
        self, interaction_data: dict[str, Any]
    ) -> float:
        """Calculate relationship strength score."""
        contacts = len(interaction_data["contacts"])
        interactions = interaction_data["total_interactions"]
        relationship_types = len(interaction_data["relationship_types"])

        # Weighted scoring
        score = (
            (contacts * 0.3)
            + (min(interactions / 50, 1.0) * 0.5)
            + (relationship_types * 0.2)
        )
        return min(score, 1.0)


# Demonstration and testing functions
@log_function()
async def demo_contact_memory() -> None:
    """
    Demonstration of contact memory system capabilities.

    Showcases the contact management features including
    contact creation, deduplication, search, and relationship tracking
    for asset management environments.
    """
    logger.info("Starting ContactMemory demonstration")

    contact_memory = ContactMemory()

    try:
        # Add sample contacts
        logger.info("Adding sample contacts...")

        # Investment professional
        contact1_id = await contact_memory.add_contact(
            email="john.smith@blackstone.com",
            name="John Smith",
            organization="Blackstone Group",
            title="Managing Director",
            contact_type=ContactType.PROFESSIONAL,
            confidence=ContactConfidence.HIGH,
            relationship="counterparty",
        )

        # Investor contact
        _contact2_id = await contact_memory.add_contact(
            email="sarah.jones@pension.gov",
            name="Sarah Jones",
            organization="State Pension Fund",
            title="Investment Director",
            contact_type=ContactType.PROFESSIONAL,
            confidence=ContactConfidence.HIGH,
            relationship="investor",
        )

        # Test deduplication with update
        logger.info("Testing contact deduplication...")
        duplicate_id = await contact_memory.add_contact(
            email="john.smith@blackstone.com",  # Same email
            name="John Smith",
            phone="+1 212-555-0123",  # New information
            confidence=ContactConfidence.HIGH,
        )

        assert contact1_id == duplicate_id, "Deduplication failed"
        logger.info("✓ Contact deduplication working correctly")

        # Test search functionality
        logger.info("Testing contact search...")

        search_results = await contact_memory.search_contacts(
            query="investment director", contact_type=ContactType.PROFESSIONAL
        )

        logger.info(f"Found {len(search_results)} contacts for 'investment director'")
        for contact in search_results:
            logger.info(
                f"  - {contact.name} at {contact.organization} ({contact.title})"
            )

        # Test relationship tracking
        logger.info("Testing relationship management...")

        await contact_memory.update_contact_relationship(
            contact1_id,
            "strategic_partner",
            "Key relationship for infrastructure deals",
        )

        await contact_memory.add_contact_tag(contact1_id, "infrastructure")
        await contact_memory.add_contact_tag(contact1_id, "high_priority")

        # Retrieve updated contact
        updated_contact = await contact_memory.get_contact_by_id(contact1_id)
        logger.info(f"Updated contact relationship: {updated_contact.relationship}")
        logger.info(f"Contact tags: {updated_contact.tags}")

        # Test interaction tracking
        logger.info("Testing interaction tracking...")

        await contact_memory.record_email_interaction(
            "john.smith@blackstone.com", "email_12345"
        )

        interaction_contact = await contact_memory.find_contact_by_email(
            "john.smith@blackstone.com"
        )
        logger.info(f"Email interactions: {interaction_contact.email_count}")

        logger.info("ContactMemory demonstration completed successfully")

    except Exception as e:
        logger.error(f"ContactMemory demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # # Standard library imports
    import asyncio

    asyncio.run(demo_contact_memory())

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

    def __init__(self, max_items: int = 5000, **kwargs):
        """
        Initialize contact memory system.

        Args:
            max_items: Maximum number of contacts to store (default: 5000)
            **kwargs: Additional BaseMemory configuration parameters
        """
        super().__init__(max_items=max_items, **kwargs)
        self.collection_name = "contacts"
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
        if name and (
            not existing.name or confidence.value >= existing.confidence.value
        ):
            if existing.name != name:
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
        if phone and (
            not existing.phone or confidence.value >= existing.confidence.value
        ):
            if existing.phone != phone:
                changes.append(f"phone: '{existing.phone}' -> '{phone}'")
                existing.phone = phone
                updated = True

        # Update organization with confidence comparison
        if organization and (
            not existing.organization or confidence.value >= existing.confidence.value
        ):
            if existing.organization != organization:
                changes.append(
                    f"organization: '{existing.organization}' -> '{organization}'"
                )
                existing.organization = organization
                updated = True

        # Update title with confidence comparison
        if title and (
            not existing.title or confidence.value >= existing.confidence.value
        ):
            if existing.title != title:
                changes.append(f"title: '{existing.title}' -> '{title}'")
                existing.title = title
                updated = True

        # Update contact type if higher confidence
        if (
            contact_type != ContactType.UNKNOWN
            and confidence.value >= existing.confidence.value
        ):
            if existing.contact_type != contact_type:
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

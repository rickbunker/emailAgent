"""
Contact Memory Module

This module manages a dedicated Qdrant collection for storing and managing
contact information. Unlike episodic memory which stores extraction events,
this creates persistent contact records that can be updated and enriched over time.

Features:
- Contact deduplication (same person from multiple emails)
- Contact updates and enrichment
- Relationship tracking
- Search by name, email, organization, phone
- Contact history and interaction tracking
"""

import os
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, UTC
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

from .base import BaseMemory, MemoryItem


class ContactType(Enum):
    """Types of contacts."""
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    FAMILY = "family"
    VENDOR = "vendor"
    UNKNOWN = "unknown"


class ContactConfidence(Enum):
    """Confidence levels for contact information."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContactRecord:
    """A complete contact record."""
    id: str
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    title: Optional[str] = None
    address: Optional[str] = None
    contact_type: ContactType = ContactType.UNKNOWN
    confidence: ContactConfidence = ContactConfidence.LOW
    
    # Relationship and context
    relationship: Optional[str] = None  # "colleague", "friend", "vendor", etc.
    notes: Optional[str] = None
    tags: List[str] = None
    
    # Tracking
    first_seen: str = ""
    last_updated: str = ""
    last_email_interaction: str = ""
    email_count: int = 0
    
    # Sources - track where we got this info
    sources: List[str] = None  # List of email IDs where we found this contact
    extraction_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.sources is None:
            self.sources = []
        if self.extraction_history is None:
            self.extraction_history = []
        if not self.first_seen:
            self.first_seen = datetime.now(UTC).isoformat()
        if not self.last_updated:
            self.last_updated = datetime.now(UTC).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert enums to strings
        data['contact_type'] = self.contact_type.value
        data['confidence'] = self.confidence.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContactRecord':
        """Create from dictionary."""
        # Convert string enums back
        if 'contact_type' in data:
            data['contact_type'] = ContactType(data['contact_type'])
        if 'confidence' in data:
            data['confidence'] = ContactConfidence(data['confidence'])
        
        return cls(**data)
    
    def get_search_text(self) -> str:
        """Get text for vector search indexing."""
        parts = []
        
        if self.name:
            parts.append(self.name)
        if self.email:
            parts.append(self.email)
        if self.organization:
            parts.append(self.organization)
        if self.title:
            parts.append(self.title)
        if self.phone:
            parts.append(self.phone)
        if self.relationship:
            parts.append(self.relationship)
        if self.notes:
            parts.append(self.notes)
        
        # Add tags
        parts.extend(self.tags)
        
        return " ".join(parts)


class ContactMemory(BaseMemory):
    """
    Memory system for managing contacts.
    
    This creates a dedicated Qdrant collection for contacts with features like:
    - Contact deduplication
    - Contact updates and enrichment
    - Search by various fields
    - Relationship tracking
    """
    
    def __init__(self, max_items: int = 5000, **kwargs):
        super().__init__(max_items=max_items, **kwargs)
        self.collection_name = "contacts"
    
    async def add_contact(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        title: Optional[str] = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Add or update a contact.
        
        This method handles deduplication - if a contact with the same email
        already exists, it will update the existing record instead of creating
        a duplicate.
        
        Args:
            email: Contact's email address (primary key)
            name: Full name
            phone: Phone number
            organization: Company/organization
            title: Job title
            contact_type: Type of contact
            confidence: Confidence in the information
            source_email_id: ID of email where this contact was extracted
            **kwargs: Additional contact fields
            
        Returns:
            str: The contact ID
        """
        await self._ensure_collection()
        
        # Check if contact already exists
        existing = await self.find_contact_by_email(email)
        
        if existing:
            # Update existing contact
            return await self._update_existing_contact(
                existing, name, phone, organization, title, 
                contact_type, confidence, source_email_id, **kwargs
            )
        else:
            # Create new contact
            return await self._create_new_contact(
                email, name, phone, organization, title,
                contact_type, confidence, source_email_id, **kwargs
            )
    
    async def _create_new_contact(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        title: Optional[str] = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Create a new contact record."""
        
        contact_id = str(uuid.uuid4())
        
        contact = ContactRecord(
            id=contact_id,
            email=email,
            name=name,
            phone=phone,
            organization=organization,
            title=title,
            contact_type=contact_type,
            confidence=confidence,
            **kwargs
        )
        
        # Add source if provided
        if source_email_id:
            contact.sources.append(source_email_id)
            contact.extraction_history.append({
                'source_email_id': source_email_id,
                'extracted_at': datetime.now(UTC).isoformat(),
                'extracted_name': name,
                'extracted_phone': phone,
                'extracted_organization': organization,
                'extracted_title': title
            })
        
        # Generate embedding for search
        search_text = contact.get_search_text()
        embedding = self.embedding_model.encode(search_text)
        
        # Store in Qdrant
        point = models.PointStruct(
            id=contact_id,
            vector=embedding.tolist(),
            payload=contact.to_dict()
        )
        
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        print(f"[DEBUG][ADD_CONTACT] Created new contact: {name or email} ({contact_id})")
        return contact_id
    
    async def _update_existing_contact(
        self,
        existing: ContactRecord,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        title: Optional[str] = None,
        contact_type: ContactType = ContactType.UNKNOWN,
        confidence: ContactConfidence = ContactConfidence.LOW,
        source_email_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Update an existing contact record."""
        
        updated = False
        
        # Update fields if new information is provided and better
        if name and (not existing.name or confidence.value == 'high'):
            existing.name = name
            updated = True
        
        if phone and not existing.phone:
            existing.phone = phone
            updated = True
        
        if organization and (not existing.organization or confidence.value == 'high'):
            existing.organization = organization
            updated = True
        
        if title and (not existing.title or confidence.value == 'high'):
            existing.title = title
            updated = True
        
        # Update contact type if we have higher confidence
        if (contact_type != ContactType.UNKNOWN and 
            (existing.contact_type == ContactType.UNKNOWN or 
             confidence.value == 'high')):
            existing.contact_type = contact_type
            updated = True
        
        # Update confidence if higher
        confidence_order = {'low': 1, 'medium': 2, 'high': 3}
        if confidence_order.get(confidence.value, 0) > confidence_order.get(existing.confidence.value, 0):
            existing.confidence = confidence
            updated = True
        
        # Add source if new
        if source_email_id and source_email_id not in existing.sources:
            existing.sources.append(source_email_id)
            existing.extraction_history.append({
                'source_email_id': source_email_id,
                'extracted_at': datetime.now(UTC).isoformat(),
                'extracted_name': name,
                'extracted_phone': phone,
                'extracted_organization': organization,
                'extracted_title': title
            })
            updated = True
        
        # Update additional kwargs
        for key, value in kwargs.items():
            if hasattr(existing, key) and value is not None:
                setattr(existing, key, value)
                updated = True
        
        if updated:
            existing.last_updated = datetime.now(UTC).isoformat()
            existing.email_count += 1
            
            # Re-generate embedding
            search_text = existing.get_search_text()
            embedding = self.embedding_model.encode(search_text)
            
            # Update in Qdrant
            point = models.PointStruct(
                id=existing.id,
                vector=embedding.tolist(),
                payload=existing.to_dict()
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            print(f"[DEBUG][UPDATE_CONTACT] Updated contact: {existing.name or existing.email} ({existing.id})")
        else:
            print(f"[DEBUG][UPDATE_CONTACT] No updates needed for: {existing.name or existing.email}")
        
        return existing.id
    
    async def find_contact_by_email(self, email: str) -> Optional[ContactRecord]:
        """Find a contact by email address."""
        await self._ensure_collection()
        
        try:
            # Search using filter on email field
            search_result = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="email",
                            match=models.MatchValue(value=email)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            if search_result[0]:  # search_result is a tuple (points, next_page_offset)
                point = search_result[0][0]
                return ContactRecord.from_dict(point.payload)
            
            return None
        except Exception as e:
            print(f"[DEBUG][FIND_BY_EMAIL][ERROR] {email}: {e}")
            return None
    
    async def search_contacts(
        self,
        query: str,
        limit: int = 10,
        contact_type: Optional[ContactType] = None,
        min_confidence: Optional[ContactConfidence] = None
    ) -> List[ContactRecord]:
        """
        Search contacts using vector similarity.
        
        Args:
            query: Search query (name, organization, etc.)
            limit: Maximum results to return
            contact_type: Filter by contact type
            min_confidence: Minimum confidence level
            
        Returns:
            List[ContactRecord]: Matching contacts
        """
        await self._ensure_collection()
        
        # Build filter
        filter_conditions = []
        
        if contact_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="contact_type",
                    match=models.MatchValue(value=contact_type.value)
                )
            )
        
        if min_confidence:
            # This is tricky with string enums, we might need to filter post-search
            pass
        
        query_filter = None
        if filter_conditions:
            query_filter = models.Filter(must=filter_conditions)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)
        
        # Search
        search_result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False
        )
        
        contacts = []
        for hit in search_result.points:
            contact = ContactRecord.from_dict(hit.payload)
            
            # Apply confidence filter if specified
            if min_confidence:
                confidence_order = {'low': 1, 'medium': 2, 'high': 3}
                if confidence_order.get(contact.confidence.value, 0) < confidence_order.get(min_confidence.value, 0):
                    continue
            
            contacts.append(contact)
        
        print(f"[DEBUG][SEARCH_CONTACTS] query='{query}' -> {len(contacts)} results")
        return contacts
    
    async def get_contact_by_id(self, contact_id: str) -> Optional[ContactRecord]:
        """Get a contact by ID."""
        await self._ensure_collection()
        
        try:
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[contact_id],
                with_payload=True,
                with_vectors=False
            )
            
            if result:
                return ContactRecord.from_dict(result[0].payload)
            return None
        except Exception as e:
            print(f"[DEBUG][GET_CONTACT][ERROR] {contact_id}: {e}")
            return None
    
    async def get_all_contacts(self, limit: int = 100) -> List[ContactRecord]:
        """Get all contacts (paginated)."""
        await self._ensure_collection()
        
        try:
            result = await self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            contacts = []
            for point in result[0]:  # result is (points, next_page_offset)
                contacts.append(ContactRecord.from_dict(point.payload))
            
            return contacts
        except Exception as e:
            print(f"[DEBUG][GET_ALL_CONTACTS][ERROR]: {e}")
            return []
    
    async def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact."""
        await self._ensure_collection()
        
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[contact_id])
            )
            print(f"[DEBUG][DELETE_CONTACT] {contact_id}: DELETED")
            return True
        except Exception as e:
            print(f"[DEBUG][DELETE_CONTACT][ERROR] {contact_id}: {e}")
            return False
    
    async def update_contact_relationship(self, contact_id: str, relationship: str, notes: Optional[str] = None):
        """Update contact's relationship and notes."""
        contact = await self.get_contact_by_id(contact_id)
        if not contact:
            return False
        
        contact.relationship = relationship
        if notes:
            contact.notes = notes
        contact.last_updated = datetime.now(UTC).isoformat()
        
        # Re-save
        search_text = contact.get_search_text()
        embedding = self.embedding_model.encode(search_text)
        
        point = models.PointStruct(
            id=contact_id,
            vector=embedding.tolist(),
            payload=contact.to_dict()
        )
        
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        print(f"[DEBUG][UPDATE_RELATIONSHIP] {contact.name or contact.email}: {relationship}")
        return True
    
    async def add_contact_tag(self, contact_id: str, tag: str):
        """Add a tag to a contact."""
        contact = await self.get_contact_by_id(contact_id)
        if not contact:
            return False
        
        if tag not in contact.tags:
            contact.tags.append(tag)
            contact.last_updated = datetime.now(UTC).isoformat()
            
            # Re-save
            search_text = contact.get_search_text()
            embedding = self.embedding_model.encode(search_text)
            
            point = models.PointStruct(
                id=contact_id,
                vector=embedding.tolist(),
                payload=contact.to_dict()
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            print(f"[DEBUG][ADD_TAG] {contact.name or contact.email}: +{tag}")
        
        return True
    
    async def record_email_interaction(self, email: str, email_id: str):
        """Record that we had an email interaction with this contact."""
        contact = await self.find_contact_by_email(email)
        if contact:
            contact.last_email_interaction = datetime.now(UTC).isoformat()
            contact.email_count += 1
            
            if email_id not in contact.sources:
                contact.sources.append(email_id)
            
            # Re-save
            search_text = contact.get_search_text()
            embedding = self.embedding_model.encode(search_text)
            
            point = models.PointStruct(
                id=contact.id,
                vector=embedding.tolist(),
                payload=contact.to_dict()
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            print(f"[DEBUG][EMAIL_INTERACTION] {contact.name or contact.email}: email_count={contact.email_count}")


async def demo_contact_memory():
    """Demo the contact memory system."""
    print("📇 CONTACT MEMORY DEMO")
    print("=" * 40)
    
    contact_memory = ContactMemory()
    
    # Add some contacts
    print("\n➕ Adding contacts...")
    
    # First contact
    contact1_id = await contact_memory.add_contact(
        email="john.smith@acmecorp.com",
        name="John Smith",
        phone="(555) 123-4567",
        organization="Acme Corporation",
        title="Senior Project Manager",
        contact_type=ContactType.PROFESSIONAL,
        confidence=ContactConfidence.HIGH,
        source_email_id="email_001"
    )
    
    # Same person from another email (should update, not duplicate)
    contact1_id_again = await contact_memory.add_contact(
        email="john.smith@acmecorp.com",
        name="John Smith",  # Same name
        title="Project Manager",  # Different title, but lower confidence
        contact_type=ContactType.PROFESSIONAL,
        confidence=ContactConfidence.MEDIUM,
        source_email_id="email_002"
    )
    
    print(f"Contact 1 first add: {contact1_id}")
    print(f"Contact 1 second add: {contact1_id_again}")
    print(f"Same ID? {contact1_id == contact1_id_again}")
    
    # Different person
    contact2_id = await contact_memory.add_contact(
        email="sarah.davis@gmail.com",
        name="Sarah Davis",
        contact_type=ContactType.PERSONAL,
        confidence=ContactConfidence.MEDIUM,
        source_email_id="email_003"
    )
    
    # Add relationship info
    await contact_memory.update_contact_relationship(
        contact1_id, 
        "colleague", 
        "Works on Q4 project with us"
    )
    
    await contact_memory.add_contact_tag(contact1_id, "important")
    await contact_memory.add_contact_tag(contact2_id, "friend")
    
    print(f"\n📋 Total contacts added: 2 unique contacts")
    
    # Search contacts
    print(f"\n🔍 Searching contacts...")
    
    results = await contact_memory.search_contacts("John")
    print(f"Search 'John': {len(results)} results")
    for contact in results:
        print(f"  • {contact.name} ({contact.email}) - {contact.organization}")
    
    results = await contact_memory.search_contacts("Acme")
    print(f"Search 'Acme': {len(results)} results")
    
    results = await contact_memory.search_contacts("personal", contact_type=ContactType.PERSONAL)
    print(f"Search personal contacts: {len(results)} results")
    
    # Show all contacts
    print(f"\n📇 All contacts:")
    all_contacts = await contact_memory.get_all_contacts()
    for contact in all_contacts:
        print(f"• {contact.name or contact.email}")
        print(f"  Email: {contact.email}")
        if contact.phone:
            print(f"  Phone: {contact.phone}")
        if contact.organization:
            print(f"  Organization: {contact.organization}")
        print(f"  Type: {contact.contact_type.value}")
        print(f"  Confidence: {contact.confidence.value}")
        if contact.relationship:
            print(f"  Relationship: {contact.relationship}")
        if contact.tags:
            print(f"  Tags: {', '.join(contact.tags)}")
        print(f"  Email count: {contact.email_count}")
        print(f"  Sources: {len(contact.sources)} emails")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_contact_memory()) 
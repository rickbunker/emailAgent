"""
Contact Extraction Agent

This agent extracts contact information from emails, focusing on identifying
real individual humans while filtering out:
- Spam and automated systems
- Distribution lists and no-reply addresses  
- Cold callers and sales emails
- Bulk/marketing emails

The goal is to build a high-quality contact database of genuine personal 
and professional relationships.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory
from ..memory.contact import ContactMemory, ContactType as MemContactType, ContactConfidence as MemContactConfidence
from .supervisor import EmailMessage


class ContactType(Enum):
    """Types of contacts we can extract."""
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    FAMILY = "family"
    VENDOR = "vendor"
    UNKNOWN = "unknown"


class ContactConfidence(Enum):
    """Confidence levels for contact extraction."""
    HIGH = "high"       # Definitely a real person
    MEDIUM = "medium"   # Likely a real person
    LOW = "low"         # Uncertain
    NONE = "none"       # Definitely not a real person


@dataclass
class ContactInfo:
    """Extracted contact information."""
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
    source_email_id: Optional[str] = None
    extraction_reasoning: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContactExtractor:
    """
    Intelligent contact extraction agent.
    
    Identifies real human contacts from emails while filtering out automated
    systems, spam, and unwanted solicitations.
    """
    
    def __init__(self):
        self.procedural_memory = ProceduralMemory(max_items=1000)
        self.semantic_memory = SemanticMemory(max_items=1000)
        self.episodic_memory = EpisodicMemory(max_items=1000)
        self.contact_memory = ContactMemory(max_items=5000)
        
        # Patterns for identifying automated/bulk emails
        self.no_reply_patterns = [
            r'no[-_]?reply',
            r'noreply',
            r'donotreply',
            r'do[-_]?not[-_]?reply',
            r'automated',
            r'auto[-_]?generated',
            r'system',
            r'daemon',
            r'mailer[-_]?daemon'
        ]
        
        # Common bulk/marketing domains
        self.bulk_domains = {
            'mailchimp.com', 'constantcontact.com', 'sendgrid.net',
            'amazonses.com', 'mailgun.org', 'sparkpostmail.com',
            'email.amazon.com', 'bounce.email', 'unsubscribe.email'
        }
        
        # Patterns for extracting contact info
        self.phone_pattern = re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b')
        self.name_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
        
    async def extract_contacts(self, email: EmailMessage) -> List[ContactInfo]:
        """
        Main entry point for contact extraction.
        
        Args:
            email: Email message to analyze
            
        Returns:
            List[ContactInfo]: Extracted contacts (may be empty)
        """
        print(f"👥 Extracting contacts from: {email.sender}")
        
        # Step 1: Check if this is a real person
        person_analysis = await self._analyze_real_person(email)
        
        if person_analysis['confidence'] == ContactConfidence.NONE:
            print(f"   ❌ Skipping: {person_analysis['reasoning']}")
            return []
        
        # Step 2: Extract contact information
        contact_info = await self._extract_contact_info(email, person_analysis)
        
        # Step 3: Validate and enhance contact
        if contact_info:
            contact_info = await self._enhance_contact(contact_info, email)
            
            # Step 4: Store successful extraction
            await self._store_extraction(contact_info, email)
            
            print(f"   ✅ Extracted: {contact_info.name or contact_info.email}")
            return [contact_info]
        
        print(f"   ❌ No contact info extracted")
        return []
    
    async def _analyze_real_person(self, email: EmailMessage) -> Dict[str, Any]:
        """Determine if the sender is likely a real person."""
        print(f"   🔍 Analyzing if sender is real person...")
        
        sender_email = email.sender.lower()
        sender_parts = sender_email.split('@')
        
        if len(sender_parts) != 2:
            return {
                'confidence': ContactConfidence.NONE,
                'reasoning': 'Invalid email format'
            }
        
        local_part, domain = sender_parts
        
        # Check for no-reply patterns
        for pattern in self.no_reply_patterns:
            if re.search(pattern, sender_email, re.IGNORECASE):
                return {
                    'confidence': ContactConfidence.NONE,
                    'reasoning': f'No-reply address pattern: {pattern}'
                }
        
        # Check for bulk email domains
        if domain in self.bulk_domains:
            return {
                'confidence': ContactConfidence.NONE,
                'reasoning': f'Bulk email domain: {domain}'
            }
        
        # Check for automated system patterns
        automated_indicators = [
            'notification', 'alert', 'system', 'admin', 'support',
            'info', 'sales', 'marketing', 'newsletter', 'updates'
        ]
        
        if any(indicator in local_part for indicator in automated_indicators):
            # Could be automated, but let's check content for personal indicators
            personal_score = self._calculate_personal_score(email)
            if personal_score < 0.3:
                return {
                    'confidence': ContactConfidence.NONE,
                    'reasoning': f'Automated system pattern: {local_part}'
                }
        
        # Check semantic memory for known sender patterns
        sender_knowledge = await self._check_sender_knowledge(email.sender)
        
        if sender_knowledge:
            trust_level = sender_knowledge.get('trust_level', 'unknown')
            sender_type = sender_knowledge.get('sender_type', 'unknown')
            
            if trust_level == 'none':
                return {
                    'confidence': ContactConfidence.NONE,
                    'reasoning': 'Known spam/untrusted sender'
                }
            
            if sender_type in ['family', 'colleague', 'friend']:
                return {
                    'confidence': ContactConfidence.HIGH,
                    'reasoning': f'Known {sender_type} contact'
                }
        
        # Analyze email content for personal indicators
        personal_score = self._calculate_personal_score(email)
        
        if personal_score > 0.7:
            confidence = ContactConfidence.HIGH
        elif personal_score > 0.4:
            confidence = ContactConfidence.MEDIUM
        else:
            confidence = ContactConfidence.LOW
        
        return {
            'confidence': confidence,
            'reasoning': f'Personal score: {personal_score:.2f}',
            'personal_score': personal_score
        }
    
    def _calculate_personal_score(self, email: EmailMessage) -> float:
        """Calculate how 'personal' an email appears to be."""
        score = 0.0
        content = email.content.lower()
        subject = email.subject.lower()
        
        # Personal indicators (positive)
        personal_indicators = [
            'hi ', 'hello ', 'dear ', 'thanks', 'thank you',
            'hope you', 'how are you', 'i hope', 'pleased to',
            'nice to meet', 'looking forward', 'best regards',
            'sincerely', 'warmly', 'cheers'
        ]
        
        for indicator in personal_indicators:
            if indicator in content:
                score += 0.1
        
        # Check for personal pronouns
        personal_pronouns = ['i ', 'my ', 'me ', 'myself', 'we ', 'our ', 'us ']
        for pronoun in personal_pronouns:
            if pronoun in content:
                score += 0.05
        
        # Check for questions (indicates engagement)
        if '?' in content:
            score += 0.1
        
        # Business but personal indicators
        business_personal = [
            'meeting', 'call', 'discuss', 'project', 'deadline',
            'schedule', 'availability', 'collaboration'
        ]
        
        for indicator in business_personal:
            if indicator in content:
                score += 0.05
        
        # Negative indicators (automated/bulk)
        automated_indicators = [
            'unsubscribe', 'opt out', 'bulk', 'promotional',
            'this is an automated', 'do not reply', 'newsletter',
            'mailing list', 'click here', 'limited time offer'
        ]
        
        for indicator in automated_indicators:
            if indicator in content:
                score -= 0.3
        
        # Cold sales indicators
        sales_indicators = [
            'increase sales', 'special offer', 'discount',
            'free trial', 'limited time', 'act now',
            'call now', 'exclusive deal'
        ]
        
        for indicator in sales_indicators:
            if indicator in content or indicator in subject:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    async def _check_sender_knowledge(self, sender_email: str) -> Optional[Dict[str, Any]]:
        """Check semantic memory for knowledge about this sender."""
        results = await self.semantic_memory.search(f"{sender_email} sender", limit=1)
        
        if results:
            result = results[0]
            return {
                'trust_level': result.metadata.get('trust_level'),
                'sender_type': result.metadata.get('sender_type'),
                'description': result.content
            }
        
        return None
    
    async def _extract_contact_info(self, email: EmailMessage, person_analysis: Dict[str, Any]) -> Optional[ContactInfo]:
        """Extract detailed contact information from the email."""
        print(f"   📋 Extracting contact details...")
        
        # Start with email address
        contact = ContactInfo(
            email=email.sender,
            confidence=person_analysis['confidence'],
            source_email_id=email.id,
            extraction_reasoning=person_analysis['reasoning']
        )
        
        # Extract name from email address
        local_part = email.sender.split('@')[0]
        
        # Try to parse name from email
        if '.' in local_part:
            parts = local_part.split('.')
            if len(parts) == 2 and all(part.isalpha() for part in parts):
                contact.first_name = parts[0].title()
                contact.last_name = parts[1].title()
                contact.name = f"{contact.first_name} {contact.last_name}"
        
        # Look for signature or contact info in email content
        signature_info = self._extract_from_signature(email.content)
        if signature_info:
            # Update contact with signature info
            if signature_info.get('name') and not contact.name:
                contact.name = signature_info['name']
            
            if signature_info.get('phone'):
                contact.phone = signature_info['phone']
            
            if signature_info.get('organization'):
                contact.organization = signature_info['organization']
            
            if signature_info.get('title'):
                contact.title = signature_info['title']
        
        # Determine contact type
        contact.contact_type = self._determine_contact_type(email, contact)
        
        return contact
    
    def _extract_from_signature(self, content: str) -> Dict[str, str]:
        """Extract contact info from email signature."""
        signature_info = {}
        
        # Split content into lines
        lines = content.split('\n')
        
        # Look for signature section (usually at the end)
        signature_start = -1
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if (line_clean.startswith('--') or 
                'best regards' in line_clean.lower() or
                'sincerely' in line_clean.lower() or
                'thank you' in line_clean.lower()):
                signature_start = i
                break
        
        if signature_start == -1:
            signature_start = max(0, len(lines) - 10)  # Last 10 lines
        
        signature_lines = lines[signature_start:]
        signature_text = '\n'.join(signature_lines)
        
        # Extract phone number
        phone_match = self.phone_pattern.search(signature_text)
        if phone_match:
            signature_info['phone'] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
        
        # Extract name (look for capitalized words)
        for line in signature_lines[:5]:  # Check first few lines
            line_clean = line.strip()
            if line_clean and not line_clean.startswith(('-', '>', '<')):
                # Look for name pattern
                name_matches = self.name_pattern.findall(line_clean)
                if name_matches:
                    # Take the first reasonable name
                    for match in name_matches:
                        if 2 <= len(match.split()) <= 4:  # Reasonable name length
                            signature_info['name'] = match
                            break
                    if 'name' in signature_info:
                        break
        
        # Extract organization and title
        for line in signature_lines:
            line_clean = line.strip()
            
            # Common title patterns
            title_indicators = ['director', 'manager', 'engineer', 'analyst', 'consultant', 
                              'developer', 'specialist', 'coordinator', 'assistant', 'executive']
            
            if any(indicator in line_clean.lower() for indicator in title_indicators):
                signature_info['title'] = line_clean
            
            # Organization patterns (usually company names)
            if ('inc' in line_clean.lower() or 'llc' in line_clean.lower() or 
                'corp' in line_clean.lower() or 'company' in line_clean.lower()):
                signature_info['organization'] = line_clean
        
        return signature_info
    
    def _determine_contact_type(self, email: EmailMessage, contact: ContactInfo) -> ContactType:
        """Determine the type of contact based on available information."""
        domain = email.sender.split('@')[1].lower()
        
        # Personal email domains
        personal_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'icloud.com', 'aol.com', 'protonmail.com'
        }
        
        if domain in personal_domains:
            return ContactType.PERSONAL
        
        # If we have organization info, it's professional
        if contact.organization or contact.title:
            return ContactType.PROFESSIONAL
        
        # Check email content for indicators
        content_lower = email.content.lower()
        
        family_indicators = ['family', 'mom', 'dad', 'brother', 'sister', 'cousin']
        if any(indicator in content_lower for indicator in family_indicators):
            return ContactType.FAMILY
        
        business_indicators = ['meeting', 'project', 'business', 'company', 'client']
        if any(indicator in content_lower for indicator in business_indicators):
            return ContactType.PROFESSIONAL
        
        return ContactType.UNKNOWN
    
    async def _enhance_contact(self, contact: ContactInfo, email: EmailMessage) -> ContactInfo:
        """Enhance contact with additional context and validation."""
        
        # Add metadata about extraction
        contact.metadata.update({
            'extracted_from_subject': email.subject,
            'extraction_date': email.id,  # Using email ID as proxy for date
            'domain': email.sender.split('@')[1],
            'original_content_length': len(email.content)
        })
        
        # Check procedural memory for extraction rules
        extraction_rules = await self.procedural_memory.search("contact extraction", limit=3)
        
        for rule in extraction_rules:
            if 'business' in rule.content.lower() and contact.contact_type == ContactType.PROFESSIONAL:
                contact.metadata['business_extraction_rule'] = rule.content
        
        return contact
    
    async def _store_extraction(self, contact: ContactInfo, email: EmailMessage):
        """Store successful extraction in both contacts collection and episodic memory."""
        
        # Convert to memory types
        mem_contact_type = MemContactType(contact.contact_type.value)
        mem_confidence = MemContactConfidence(contact.confidence.value)
        
        # Store in dedicated contacts collection
        contact_id = await self.contact_memory.add_contact(
            email=contact.email,
            name=contact.name,
            phone=contact.phone,
            organization=contact.organization,
            title=contact.title,
            contact_type=mem_contact_type,
            confidence=mem_confidence,
            source_email_id=contact.source_email_id
        )
        
        # Also store extraction event in episodic memory for learning
        extraction_content = f"Successfully extracted contact: {contact.name or contact.email}"
        if contact.organization:
            extraction_content += f" from {contact.organization}"
        
        metadata = {
            'type': 'contact_extraction',
            'contact_id': contact_id,  # Link to contacts collection
            'contact_email': contact.email,
            'contact_name': contact.name,
            'contact_type': contact.contact_type.value,
            'confidence': contact.confidence.value,
            'source_email_sender': email.sender,
            'source_email_subject': email.subject,
            'extracted_phone': contact.phone,
            'extracted_organization': contact.organization
        }
        
        await self.episodic_memory.add(extraction_content, metadata)
    
    async def get_extracted_contacts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve contacts from the dedicated contacts collection."""
        
        contacts_records = await self.contact_memory.get_all_contacts(limit=limit)
        
        contacts = []
        for contact in contacts_records:
            contacts.append({
                'id': contact.id,
                'email': contact.email,
                'name': contact.name,
                'type': contact.contact_type.value,
                'confidence': contact.confidence.value,
                'phone': contact.phone,
                'organization': contact.organization,
                'title': contact.title,
                'relationship': contact.relationship,
                'tags': contact.tags,
                'email_count': contact.email_count,
                'first_seen': contact.first_seen,
                'last_updated': contact.last_updated,
                'sources': len(contact.sources)
            })
        
        return contacts
    
    async def search_contacts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search contacts in the contacts collection."""
        
        contacts_records = await self.contact_memory.search_contacts(query, limit=limit)
        
        contacts = []
        for contact in contacts_records:
            contacts.append({
                'id': contact.id,
                'email': contact.email,
                'name': contact.name,
                'type': contact.contact_type.value,
                'confidence': contact.confidence.value,
                'phone': contact.phone,
                'organization': contact.organization,
                'title': contact.title,
                'relationship': contact.relationship,
                'tags': contact.tags,
                'email_count': contact.email_count
            })
        
        return contacts


async def demo_contact_extractor():
    """Demonstrate the contact extraction agent."""
    print("👥 CONTACT EXTRACTION DEMO")
    print("=" * 50)
    
    extractor = ContactExtractor()
    
    # Test emails - mix of real people and automated systems
    test_emails = [
        EmailMessage(
            id="1",
            sender="john.smith@acmecorp.com",
            subject="Project Discussion",
            content="""Hi there,

I wanted to discuss the Q4 project timeline with you. Could we schedule a call this week?

Best regards,
John Smith
Senior Project Manager
Acme Corporation
Phone: (555) 123-4567
john.smith@acmecorp.com"""
        ),
        
        EmailMessage(
            id="2",
            sender="sarah.davis@gmail.com", 
            subject="Coffee catch-up?",
            content="""Hey!

Hope you're doing well. Want to grab coffee sometime this week? I'd love to catch up!

Talk soon,
Sarah"""
        ),
        
        EmailMessage(
            id="3",
            sender="noreply@newsletter.com",
            subject="Weekly Tech Newsletter",
            content="""This is an automated newsletter. 

Latest tech news and updates...

To unsubscribe, click here."""
        ),
        
        EmailMessage(
            id="4",
            sender="sales@coldcaller.com",
            subject="Increase Your Sales by 300%!",
            content="""Limited time offer! Our amazing product can increase your sales by 300%!

Act now! Call 1-800-SALES-NOW

This offer expires soon!"""
        ),
        
        EmailMessage(
            id="5",
            sender="dr.lisa.chen@cardiology.org",
            subject="Appointment Confirmation",
            content="""Dear Patient,

Your appointment is confirmed for Tuesday at 2pm.

Best regards,

Dr. Lisa Chen, MD
Cardiology Associates
Phone: (555) 987-6543
123 Medical Center Dr."""
        )
    ]
    
    all_contacts = []
    
    for email in test_emails:
        print(f"\n📧 Processing: {email.subject}")
        contacts = await extractor.extract_contacts(email)
        
        if contacts:
            contact = contacts[0]
            print(f"   ✅ Contact: {contact.name or contact.email}")
            print(f"      Type: {contact.contact_type.value}")
            print(f"      Confidence: {contact.confidence.value}")
            if contact.phone:
                print(f"      Phone: {contact.phone}")
            if contact.organization:
                print(f"      Organization: {contact.organization}")
            
            all_contacts.extend(contacts)
        else:
            print(f"   ❌ No contact extracted")
    
    # Show summary
    print(f"\n📊 EXTRACTION SUMMARY")
    print("=" * 30)
    print(f"Total contacts extracted: {len(all_contacts)}")
    
    by_type = {}
    by_confidence = {}
    
    for contact in all_contacts:
        contact_type = contact.contact_type.value
        confidence = contact.confidence.value
        
        by_type[contact_type] = by_type.get(contact_type, 0) + 1
        by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
    
    print(f"By type: {by_type}")
    print(f"By confidence: {by_confidence}")
    
    # Show stored contacts from contacts collection
    print(f"\n📋 CONTACTS DATABASE")
    print("=" * 30)
    stored = await extractor.get_extracted_contacts(limit=10)
    for contact in stored:
        name = contact['name'] or contact['email']
        print(f"• {name} ({contact['type']}) - {contact['confidence']}")
        if contact['phone']:
            print(f"  📞 {contact['phone']}")
        if contact['organization']:
            print(f"  🏢 {contact['organization']}")
        if contact['title']:
            print(f"  💼 {contact['title']}")
        print(f"  📧 {contact['email_count']} email interactions")
        print(f"  📅 Last updated: {contact['last_updated'][:10]}")
    
    # Show search functionality
    print(f"\n🔍 CONTACT SEARCH")
    print("=" * 20)
    
    # Search for John
    search_results = await extractor.search_contacts("John")
    print(f"Search 'John': {len(search_results)} results")
    for contact in search_results:
        print(f"  • {contact['name']} - {contact['organization'] or 'No org'}")
    
    # Search for Acme
    search_results = await extractor.search_contacts("Acme")
    print(f"Search 'Acme': {len(search_results)} results")
    for contact in search_results:
        print(f"  • {contact['name']} - {contact['title'] or 'No title'}")


if __name__ == "__main__":
    asyncio.run(demo_contact_extractor()) 
"""
Email Management Supervisor Agent

This agent coordinates the email management process by:
1. Receiving incoming emails
2. Consulting memory systems for relevant knowledge
3. Making decisions about spam, priority, and actions
4. Learning from user feedback
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory


class EmailAction(Enum):
    """Possible actions for email processing."""
    PRIORITIZE = "prioritize"
    SPAM_DELETE = "spam_delete" 
    SPAM_QUARANTINE = "spam_quarantine"
    AUTO_RESPOND = "auto_respond"
    EXTRACT_CONTACTS = "extract_contacts"
    CATEGORIZE = "categorize"
    ARCHIVE = "archive"
    REQUIRE_ATTENTION = "require_attention"


class TrustLevel(Enum):
    """Trust levels for email senders."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


@dataclass
class EmailMessage:
    """Represents an email message for processing."""
    id: str
    sender: str
    subject: str
    content: str
    attachments: List[str] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass 
class EmailAnalysis:
    """Results of email analysis."""
    trust_level: TrustLevel
    spam_score: float
    priority_score: float
    recommended_actions: List[EmailAction]
    reasoning: str
    confidence: float


class EmailSupervisor:
    """Main supervisor agent for email management."""
    
    def __init__(self):
        self.procedural_memory = ProceduralMemory(max_items=1000)
        self.semantic_memory = SemanticMemory(max_items=1000) 
        self.episodic_memory = EpisodicMemory(max_items=1000)
        
        self.spam_threshold = 0.7
        self.priority_threshold = 0.6
    
    async def process_email(self, email: EmailMessage) -> EmailAnalysis:
        """Main entry point for processing an email."""
        print(f"🔍 Processing email from {email.sender}: {email.subject}")
        
        # Analyze sender
        sender_info = await self._analyze_sender(email.sender)
        
        # Check spam indicators
        spam_score = await self._analyze_spam(email)
        
        # Determine priority
        priority_score = await self._analyze_priority(email, sender_info)
        
        # Generate recommendations
        actions, reasoning = await self._generate_recommendations(email, sender_info, spam_score, priority_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(sender_info, spam_score, priority_score)
        
        analysis = EmailAnalysis(
            trust_level=sender_info['trust_level'],
            spam_score=spam_score,
            priority_score=priority_score,
            recommended_actions=actions,
            reasoning=reasoning,
            confidence=confidence
        )
        
        print(f"✅ Analysis: Trust={analysis.trust_level.value}, Spam={spam_score:.2f}, Priority={priority_score:.2f}")
        return analysis
    
    async def _analyze_sender(self, sender_email: str) -> Dict[str, Any]:
        """Analyze sender using semantic memory."""
        print(f"   🧠 Analyzing sender: {sender_email}")
        
        # Search for sender info
        results = await self.semantic_memory.search(f"{sender_email} OR {sender_email.split('@')[1] if '@' in sender_email else ''}")
        
        if results:
            info = results[0]
            trust_str = info.metadata.get('trust_level', 'low')
            return {
                'trust_level': TrustLevel(trust_str),
                'sender_type': info.metadata.get('sender_type', 'unknown'),
                'description': info.content
            }
        
        return {
            'trust_level': TrustLevel.LOW,
            'sender_type': 'unknown',
            'description': f"Unknown sender: {sender_email}"
        }
    
    async def _analyze_spam(self, email: EmailMessage) -> float:
        """Analyze spam indicators."""
        print(f"   🚫 Checking spam indicators...")
        
        spam_score = 0.0
        
        # Get spam rules
        spam_rules = await self.procedural_memory.search("spam suspicious malware")
        
        for rule in spam_rules:
            if 'attachment' in rule.content.lower() and email.attachments:
                # Check for suspicious attachments
                suspicious_exts = ['.exe', '.scr', '.bat']
                for attachment in email.attachments:
                    if any(attachment.lower().endswith(ext) for ext in suspicious_exts):
                        spam_score += 0.8
            
            if 'urgent' in rule.content.lower() and 'money' in rule.content.lower():
                # Check for urgent money requests
                content_lower = email.content.lower()
                if 'urgent' in content_lower and any(word in content_lower for word in ['money', 'payment', 'bank']):
                    spam_score += 0.6
        
        return min(spam_score, 1.0)
    
    async def _analyze_priority(self, email: EmailMessage, sender_info: Dict[str, Any]) -> float:
        """Determine priority based on sender and content."""
        print(f"   ⭐ Analyzing priority...")
        
        priority_score = 0.0
        
        # Base priority on trust level
        trust_scores = {
            TrustLevel.HIGHEST: 0.9,
            TrustLevel.HIGH: 0.7,
            TrustLevel.MEDIUM: 0.4,
            TrustLevel.LOW: 0.2,
            TrustLevel.NONE: 0.0
        }
        priority_score += trust_scores[sender_info['trust_level']]
        
        # Check for family/work priority rules
        priority_rules = await self.procedural_memory.search("priority family work")
        
        for rule in priority_rules:
            if 'family' in rule.content.lower() and sender_info['sender_type'] == 'family':
                priority_score += 0.8
            if 'work' in rule.content.lower() and sender_info['sender_type'] in ['colleague', 'hr']:
                priority_score += 0.5
        
        # Check subject for urgent keywords
        urgent_keywords = ['urgent', 'important', 'asap']
        if any(keyword in email.subject.lower() for keyword in urgent_keywords):
            priority_score += 0.3
        
        return min(priority_score, 1.0)
    
    async def _generate_recommendations(self, email: EmailMessage, sender_info: Dict[str, Any], spam_score: float, priority_score: float) -> tuple[List[EmailAction], str]:
        """Generate action recommendations."""
        print(f"   💡 Generating recommendations...")
        
        actions = []
        reasoning_parts = []
        
        # Spam handling
        if spam_score > self.spam_threshold:
            if spam_score > 0.9:
                actions.append(EmailAction.SPAM_DELETE)
                reasoning_parts.append(f"High spam score ({spam_score:.2f})")
            else:
                actions.append(EmailAction.SPAM_QUARANTINE)
                reasoning_parts.append(f"Moderate spam score ({spam_score:.2f})")
        
        # Priority handling
        if priority_score > self.priority_threshold and spam_score < 0.3:
            actions.append(EmailAction.PRIORITIZE)
            reasoning_parts.append(f"High priority ({priority_score:.2f})")
        
        # Trust-based actions
        if sender_info['trust_level'] in [TrustLevel.HIGH, TrustLevel.HIGHEST] and spam_score < 0.2:
            actions.append(EmailAction.REQUIRE_ATTENTION)
            reasoning_parts.append("Trusted sender")
        
        # Contact extraction for business emails
        if sender_info['sender_type'] in ['vendor', 'business'] and spam_score < 0.3:
            actions.append(EmailAction.EXTRACT_CONTACTS)
            reasoning_parts.append("Business contact")
        
        # Default action
        if not actions:
            actions.append(EmailAction.REQUIRE_ATTENTION)
            reasoning_parts.append("Needs manual review")
        
        reasoning = "; ".join(reasoning_parts)
        return actions, reasoning
    
    def _calculate_confidence(self, sender_info: Dict[str, Any], spam_score: float, priority_score: float) -> float:
        """Calculate confidence in the analysis."""
        confidence_factors = []
        
        # Sender knowledge confidence
        if sender_info['sender_type'] != 'unknown':
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.3)
        
        # Spam confidence (high when clearly spam or not spam)
        if spam_score > 0.8 or spam_score < 0.2:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.5)
        
        # Priority confidence
        confidence_factors.append(0.7)  # Simplified
        
        return sum(confidence_factors) / len(confidence_factors)


async def demo_supervisor():
    """Demo the email supervisor."""
    print("🎯 EMAIL SUPERVISOR DEMO")
    print("=" * 50)
    
    supervisor = EmailSupervisor()
    
    test_emails = [
        EmailMessage("1", "john.smith@acmecorp.com", "Weekly Project Update", "Weekly progress report"),
        EmailMessage("2", "mom@familyemail.com", "Family dinner Sunday!", "Hope you can make it!"),
        EmailMessage("3", "winner123@gmail.com", "URGENT: You've Won $1,000,000!", "Send bank details immediately!"),
        EmailMessage("4", "support@techvendor.com", "Support ticket resolved", "Your issue is fixed")
    ]
    
    for email in test_emails:
        print(f"\n📧 {email.subject}")
        analysis = await supervisor.process_email(email)
        print(f"   Actions: {[a.value for a in analysis.recommended_actions]}")
        print(f"   Reasoning: {analysis.reasoning}")
        print(f"   Confidence: {analysis.confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(demo_supervisor()) 
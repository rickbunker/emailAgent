"""
Email Management Supervisor Agent for Document Processing

The central orchestration agent that coordinates the entire email management workflow
for private market asset management. This supervisor makes high-level
decisions about email processing, routing, and actions based on multiple analysis
layers and learned patterns.

Architecture:
    The supervisor acts as the brain of the email system, integrating results from:
    - Spam detection agents for security filtering
    - Contact extraction agents for relationship building
    - Asset document detection for compliance tracking
    - Priority analysis for workflow optimization
    - Memory systems for pattern learning and decision making

Key Responsibilities:
    1. Email intake and initial triage
    2. Coordination of specialized analysis agents
    3. Decision making based on multiple inputs
    4. Action recommendation and execution
    5. Learning from user feedback and outcomes
    6. Workflow optimization based on user patterns

Decision Framework:
    Uses a multi-factor decision matrix considering:
    - Sender trust level and relationship history
    - Content analysis (spam, priority, document type)
    - User preferences and historical patterns
    - Regulatory and compliance requirements
    - Business context and workflow integration

Business Context:
    Designed for finance users who handle sensitive communications
    requiring careful attention to compliance, relationships, and document
    management in high-stakes environments.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, UTC
import json

# Memory system integration
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory

# Logging system integration
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

# Initialize logger
logger = get_logger(__name__)


class EmailAction(Enum):
    """
    Possible actions for email processing with business context.
    
    Defines the complete set of actions the supervisor can recommend
    or execute, each with specific implications for workflow and compliance.
    """
    PRIORITIZE = "prioritize"                    # High-priority user attention needed
    SPAM_DELETE = "spam_delete"                  # Immediate deletion (high confidence spam)
    SPAM_QUARANTINE = "spam_quarantine"          # Quarantine for review (uncertain spam)
    AUTO_RESPOND = "auto_respond"                # Automated response appropriate
    EXTRACT_CONTACTS = "extract_contacts"        # Contact information extraction
    CATEGORIZE = "categorize"                    # Apply content-based categorization
    ARCHIVE = "archive"                          # File for long-term storage
    REQUIRE_ATTENTION = "require_attention"      # Manual review required
    COMPLIANCE_FLAG = "compliance_flag"          # Mark for compliance review
    ASSET_DOCUMENT = "asset_document"            # Identified as asset document
    REGULATORY_FILING = "regulatory_filing"      # Regulatory document detected


class TrustLevel(Enum):
    """
    Trust levels for email senders based on relationship and history.
    
    Represents the system's confidence in the sender's legitimacy and
    the appropriateness of automated processing for their emails.
    """
    NONE = "none"           # Unknown/untrusted sender
    LOW = "low"             # Limited trust, proceed with caution
    MEDIUM = "medium"       # Moderate trust, standard processing
    HIGH = "high"           # High trust, expedited processing
    HIGHEST = "highest"     # Maximum trust, minimal validation needed


class PriorityLevel(Enum):
    """
    Priority levels for email processing and user attention.
    
    Determines how quickly emails should be brought to user attention
    and what level of processing automation is appropriate.
    """
    URGENT = "urgent"       # Immediate attention required
    HIGH = "high"           # High priority, process quickly
    NORMAL = "normal"       # Standard priority processing
    LOW = "low"             # Low priority, can be delayed
    ARCHIVE = "archive"     # Minimal priority, file immediately


@dataclass
class EmailMessage:
    """
    Complete email message data structure for processing.
    
    Represents an email with all metadata needed for processing,
    including content analysis, attachment information, and routing data.
    
    Attributes:
        id: Unique identifier for the email message
        sender: Email address of the sender
        subject: Email subject line
        content: Full email body content (text or HTML)
        attachments: List of attachment filenames
        headers: Complete email headers dictionary
        received_date: When the email was received
        size: Email size in bytes
        thread_id: Conversation thread identifier
        labels: List of email labels or folders
    """
    id: str
    sender: str
    subject: str
    content: str
    attachments: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    received_date: Optional[datetime] = None
    size: Optional[int] = None
    thread_id: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate email message data after initialization."""
        if not self.id:
            raise ValueError("Email ID cannot be empty")
        if not self.sender or '@' not in self.sender:
            raise ValueError(f"Invalid sender email: {self.sender}")
        if self.size is not None and self.size < 0:
            raise ValueError("Email size cannot be negative")


@dataclass 
class EmailAnalysis:
    """
    Complete results of email analysis with actionable insights.
    
    Contains all information needed to make informed decisions about
    email handling, including confidence metrics and detailed reasoning.
    
    Attributes:
        trust_level: Assessed trust level of the sender
        spam_score: Spam likelihood score (0.0-1.0)
        priority_score: Priority assessment score (0.0-1.0)
        priority_level: Categorized priority level
        recommended_actions: List of recommended processing actions
        reasoning: Detailed explanation of analysis decisions
        confidence: Overall confidence in the analysis (0.0-1.0)
        processing_time: Time taken for analysis (seconds)
        metadata: Additional analysis details and metrics
    """
    trust_level: TrustLevel
    spam_score: float
    priority_score: float
    priority_level: PriorityLevel
    recommended_actions: List[EmailAction]
    reasoning: str
    confidence: float
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate analysis results after initialization."""
        if not 0.0 <= self.spam_score <= 1.0:
            raise ValueError(f"Spam score must be 0.0-1.0, got {self.spam_score}")
        if not 0.0 <= self.priority_score <= 1.0:
            raise ValueError(f"Priority score must be 0.0-1.0, got {self.priority_score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.processing_time < 0:
            raise ValueError("Processing time cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for storage or serialization."""
        return {
            'trust_level': self.trust_level.value,
            'spam_score': self.spam_score,
            'priority_score': self.priority_score,
            'priority_level': self.priority_level.value,
            'recommended_actions': [action.value for action in self.recommended_actions],
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'processing_time': self.processing_time,
            'metadata': self.metadata
        }


class EmailSupervisor:
    """
    Central orchestration agent for email management.
    
    The supervisor coordinates all aspects of email processing, from initial
    intake through final action execution. It integrates multiple analysis
    systems and applies learned patterns to make optimal decisions.
    
    The supervisor uses a multi-layered approach:
    1. Sender analysis using relationship and trust data
    2. Content analysis for spam, priority, and document classification
    3. Pattern matching against learned user preferences
    4. Risk assessment for compliance and security
    5. Action recommendation based on integrated analysis
    6. Continuous learning from outcomes and feedback
    
    Attributes:
        procedural_memory: Stores decision rules and processing procedures
        semantic_memory: Stores knowledge about senders, content types, patterns
        episodic_memory: Stores processing history and user feedback
        spam_threshold: Threshold for spam classification (0.0-1.0)
        priority_threshold: Threshold for high priority classification (0.0-1.0)
    """
    
    def __init__(
        self,
        spam_threshold: float = 0.7,
        priority_threshold: float = 0.6
    ) -> None:
        """
        Initialize the email management supervisor.
        
        Args:
            spam_threshold: Score threshold for spam classification
            priority_threshold: Score threshold for high priority classification
            
        Raises:
            ValueError: If thresholds are not between 0.0 and 1.0
        """
        if not 0.0 <= spam_threshold <= 1.0:
            raise ValueError(f"Spam threshold must be 0.0-1.0, got {spam_threshold}")
        if not 0.0 <= priority_threshold <= 1.0:
            raise ValueError(f"Priority threshold must be 0.0-1.0, got {priority_threshold}")
        
        # Initialize memory systems
        self.procedural_memory = ProceduralMemory(max_items=1000)
        self.semantic_memory = SemanticMemory(max_items=1000) 
        self.episodic_memory = EpisodicMemory(max_items=1000)
        
        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing Email Management Supervisor")
        
        # Configuration
        self.spam_threshold = spam_threshold
        self.priority_threshold = priority_threshold
        
        # Decision factors and their weights
        self.trust_weights = {
            TrustLevel.HIGHEST: 1.0,
            TrustLevel.HIGH: 0.8,
            TrustLevel.MEDIUM: 0.5,
            TrustLevel.LOW: 0.2,
            TrustLevel.NONE: 0.0
        }
        
        # Priority keywords and their weights
        self.priority_keywords = {
            'urgent': 0.4,
            'asap': 0.4,
            'important': 0.3,
            'critical': 0.5,
            'deadline': 0.3,
            'time sensitive': 0.4,
            'regulatory': 0.6,
            'compliance': 0.5,
            'audit': 0.5
        }
        
        # Sender type priority modifiers
        self.sender_priority_modifiers = {
            'family': 0.8,
            'colleague': 0.6,
            'hr': 0.7,
            'legal': 0.9,
            'compliance': 0.9,
            'regulator': 1.0,
            'client': 0.8,
            'vendor': 0.3,
            'unknown': 0.1
        }
        
        self.logger.info(
            f"Supervisor initialized with spam_threshold={spam_threshold}, "
            f"priority_threshold={priority_threshold}"
        )
    
    @log_function()
    async def process_email(self, email: EmailMessage) -> EmailAnalysis:
        """
        Main entry point for complete email processing.
        
        Performs complete analysis of an email message and generates
        actionable recommendations based on multiple factors including
        sender trust, content analysis, and learned patterns.
        
        Args:
            email: Email message to process and analyze
            
        Returns:
            EmailAnalysis object with complete processing results
            
        Raises:
            ValueError: If email data is invalid
        """
        start_time = datetime.now()
        self.logger.info(
            f"Processing email from {email.sender}: {email.subject[:50]}..."
        )
        
        try:
            # Step 1: Analyze sender trust and relationship
            sender_info = await self._analyze_sender(email.sender)
            self.logger.debug(
                f"Sender analysis: trust={sender_info['trust_level'].value}, "
                f"type={sender_info['sender_type']}"
            )
            
            # Step 2: Check spam indicators with context
            spam_score = await self._analyze_spam(email, sender_info)
            self.logger.debug(f"Spam analysis: score={spam_score:.3f}")
            
            # Step 3: Determine priority with multiple factors
            priority_score = await self._analyze_priority(email, sender_info)
            priority_level = self._categorize_priority(priority_score)
            self.logger.debug(
                f"Priority analysis: score={priority_score:.3f}, level={priority_level.value}"
            )
            
            # Step 4: Generate complete recommendations
            actions, reasoning = await self._generate_recommendations(
                email, sender_info, spam_score, priority_score
            )
            
            # Step 5: Calculate overall confidence in analysis
            confidence = self._calculate_confidence(sender_info, spam_score, priority_score)
            
            # Step 6: Create complete analysis
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            analysis = EmailAnalysis(
                trust_level=sender_info['trust_level'],
                spam_score=spam_score,
                priority_score=priority_score,
                priority_level=priority_level,
                recommended_actions=actions,
                reasoning=reasoning,
                confidence=confidence,
                processing_time=processing_time,
                metadata={
                    'sender_type': sender_info['sender_type'],
                    'analysis_timestamp': datetime.now(UTC).isoformat(),
                    'email_size': email.size,
                    'has_attachments': len(email.attachments) > 0,
                    'sender_description': sender_info['description']
                }
            )
            
            # Step 7: Store analysis for learning
            await self._store_analysis(email, analysis)
            
            self.logger.info(
                f"Email analysis complete: trust={analysis.trust_level.value}, "
                f"priority={analysis.priority_level.value}, "
                f"actions={len(analysis.recommended_actions)}, "
                f"confidence={analysis.confidence:.3f}, "
                f"time={analysis.processing_time:.3f}s"
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Email processing failed for {email.sender}: {e}")
            # Return safe default analysis
            return EmailAnalysis(
                trust_level=TrustLevel.LOW,
                spam_score=0.5,
                priority_score=0.3,
                priority_level=PriorityLevel.NORMAL,
                recommended_actions=[EmailAction.REQUIRE_ATTENTION],
                reasoning=f"Processing failed: {str(e)}",
                confidence=0.1,
                processing_time=(datetime.now() - start_time).total_seconds(),
                metadata={'error': str(e)}
            )
    
    @log_function()
    async def _analyze_sender(self, sender_email: str) -> Dict[str, Any]:
        """
        Analyze sender using semantic memory and relationship data.
        
        Determines trust level and sender type based on historical interactions,
        relationship data, and learned patterns about email senders.
        
        Args:
            sender_email: Email address to analyze
            
        Returns:
            Dictionary with trust_level, sender_type, and description
        """
        self.logger.debug(f"Analyzing sender: {sender_email}")
        
        try:
            # Search semantic memory for sender information
            search_results = await self.semantic_memory.search(
                query=f"sender:{sender_email}",
                limit=3
            )
            
            # Look for high confidence matches
            for memory_item, score in search_results:
                if score > 0.8:  # High confidence match
                    metadata = memory_item.metadata
                    trust_str = metadata.get('trust_level', 'low')
                    sender_type = metadata.get('sender_type', 'unknown')
                    
                    self.logger.debug(f"Found sender data: trust={trust_str}, type={sender_type}")
                    
                    return {
                        'trust_level': TrustLevel(trust_str),
                        'sender_type': sender_type,
                        'description': memory_item.content,
                        'confidence': score
                    }
            
            # Check domain patterns for new senders
            domain = sender_email.split('@')[1] if '@' in sender_email else ''
            
            # Look for domain-based patterns
            domain_results = await self.semantic_memory.search(
                query=f"domain:{domain}",
                limit=2
            )
            
            for memory_item, score in domain_results:
                if score > 0.7:
                    metadata = memory_item.metadata
                    domain_trust = metadata.get('trust_level', 'low')
                    domain_type = metadata.get('sender_type', 'unknown')
                    
                    self.logger.debug(f"Found domain pattern: trust={domain_trust}, type={domain_type}")
                    
                    return {
                        'trust_level': TrustLevel(domain_trust),
                        'sender_type': domain_type,
                        'description': f"Domain pattern match: {memory_item.content}",
                        'confidence': score
                    }
            
            # Default for unknown senders
            self.logger.debug(f"Unknown sender: {sender_email}")
            return {
                'trust_level': TrustLevel.LOW,
                'sender_type': 'unknown',
                'description': f"New/unknown sender: {sender_email}",
                'confidence': 0.1
            }
            
        except Exception as e:
            self.logger.warning(f"Sender analysis failed for {sender_email}: {e}")
            return {
                'trust_level': TrustLevel.NONE,
                'sender_type': 'unknown',
                'description': f"Analysis failed for: {sender_email}",
                'confidence': 0.0
            }
    
    @log_function()
    async def _analyze_spam(self, email: EmailMessage, sender_info: Dict[str, Any]) -> float:
        """
        Analyze spam indicators with context from sender information.
        
        Uses procedural memory rules and sender context to assess spam likelihood.
        Trusted senders get significant benefits in spam scoring.
        
        Args:
            email: Email message to analyze
            sender_info: Sender analysis results
            
        Returns:
            Spam score between 0.0 (clean) and 1.0 (spam)
        """
        self.logger.debug("Analyzing spam indicators")
        
        try:
            spam_score = 0.0
            
            # Apply trust level modifier (trusted senders get big bonus)
            trust_bonus = self.trust_weights[sender_info['trust_level']]
            spam_score -= trust_bonus * 0.5  # Up to 50% spam score reduction
            
            # Get spam detection rules from procedural memory
            spam_rules = await self.procedural_memory.search(
                query="spam detection rule",
                limit=10
            )
            
            content_lower = email.content.lower()
            subject_lower = email.subject.lower()
            
            # Apply procedural rules
            for memory_item, relevance in spam_rules:
                if relevance > 0.7:  # High relevance
                    rule_data = memory_item.metadata
                    rule_type = rule_data.get('rule_type', '')
                    
                    if rule_type == 'attachment_suspicious':
                        # Check for suspicious attachments
                        suspicious_exts = ['.exe', '.scr', '.bat', '.cmd', '.pif']
                        for attachment in email.attachments:
                            if any(attachment.lower().endswith(ext) for ext in suspicious_exts):
                                spam_score += 0.8
                                self.logger.debug(f"Suspicious attachment: {attachment}")
                    
                    elif rule_type == 'content_pattern':
                        # Check content patterns
                        pattern = rule_data.get('pattern', '')
                        if pattern and pattern in content_lower:
                            penalty = rule_data.get('penalty', 0.2)
                            spam_score += penalty
                            self.logger.debug(f"Content pattern match: {pattern}")
                    
                    elif rule_type == 'urgency_money':
                        # Check for urgent money requests
                        if ('urgent' in content_lower and 
                            any(word in content_lower for word in ['money', 'payment', 'transfer', 'wire'])):
                            spam_score += 0.6
                            self.logger.debug("Urgent money request detected")
            
            # Check for bulk email indicators
            bulk_indicators = ['unsubscribe', 'mailing list', 'bulk mail', 'newsletter']
            bulk_count = sum(1 for indicator in bulk_indicators if indicator in content_lower)
            if bulk_count > 1:
                spam_score += 0.3
                self.logger.debug(f"Bulk email indicators: {bulk_count}")
            
            # Check for excessive promotional language
            promo_words = ['free', 'limited time', 'act now', 'special offer', 'discount']
            promo_count = sum(1 for word in promo_words if word in content_lower)
            if promo_count > 2:
                spam_score += promo_count * 0.1
                self.logger.debug(f"Promotional language: {promo_count} terms")
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, spam_score))
            self.logger.debug(f"Final spam score: {final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            self.logger.warning(f"Spam analysis failed: {e}")
            return 0.5  # Default uncertain score
    
    @log_function()
    async def _analyze_priority(self, email: EmailMessage, sender_info: Dict[str, Any]) -> float:
        """
        Determine priority based on sender, content, and learned patterns.
        
        Uses multiple signals to assess how quickly the email needs attention,
        including sender relationship, content urgency, and business context.
        
        Args:
            email: Email message to analyze
            sender_info: Sender analysis results
            
        Returns:
            Priority score between 0.0 (low) and 1.0 (urgent)
        """
        self.logger.debug("Analyzing priority indicators")
        
        try:
            priority_score = 0.0
            
            # Base priority on sender trust level
            trust_bonus = self.trust_weights[sender_info['trust_level']]
            priority_score += trust_bonus * 0.5
            
            # Apply sender type modifier
            sender_type = sender_info['sender_type']
            type_modifier = self.sender_priority_modifiers.get(sender_type, 0.1)
            priority_score += type_modifier * 0.3
            
            # Check subject and content for priority keywords
            text_to_check = f"{email.subject} {email.content}".lower()
            
            for keyword, weight in self.priority_keywords.items():
                if keyword in text_to_check:
                    priority_score += weight
                    self.logger.debug(f"Priority keyword '{keyword}' found (weight: {weight})")
            
            # Get priority rules from procedural memory
            priority_rules = await self.procedural_memory.search(
                query="priority urgent important",
                limit=5
            )
            
            for memory_item, relevance in priority_rules:
                if relevance > 0.7:
                    rule_data = memory_item.metadata
                    rule_type = rule_data.get('rule_type', '')
                    
                    if rule_type == 'sender_type_priority':
                        # Priority boost based on sender type
                        if sender_type == rule_data.get('sender_type'):
                            boost = rule_data.get('priority_boost', 0.2)
                            priority_score += boost
                            self.logger.debug(f"Sender type priority boost: {boost}")
                    
                    elif rule_type == 'content_priority':
                        # Priority based on content patterns
                        pattern = rule_data.get('pattern', '')
                        if pattern and pattern in text_to_check:
                            boost = rule_data.get('priority_boost', 0.3)
                            priority_score += boost
                            self.logger.debug(f"Content priority pattern: {pattern}")
            
            # Time-based urgency (recent emails get slight boost)
            if email.received_date:
                hours_old = (datetime.now(UTC) - email.received_date).total_seconds() / 3600
                if hours_old < 1:  # Very recent
                    priority_score += 0.1
                elif hours_old > 24:  # Old emails get penalty
                    priority_score -= 0.1
            
            # Attachment considerations
            if email.attachments:
                # Important documents often have attachments
                priority_score += 0.1
                
                # Check for important document types
                doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
                has_docs = any(
                    any(att.lower().endswith(ext) for ext in doc_extensions)
                    for att in email.attachments
                )
                if has_docs:
                    priority_score += 0.15
                    self.logger.debug("Important document attachments detected")
            
            # Ensure score is within bounds
            final_score = max(0.0, min(1.0, priority_score))
            self.logger.debug(f"Final priority score: {final_score:.3f}")
            
            return final_score
            
        except Exception as e:
            self.logger.warning(f"Priority analysis failed: {e}")
            return 0.3  # Default moderate priority
    
    @log_function()
    def _categorize_priority(self, priority_score: float) -> PriorityLevel:
        """
        Convert numeric priority score to categorical priority level.
        
        Args:
            priority_score: Numeric priority score (0.0-1.0)
            
        Returns:
            Categorical priority level
        """
        if priority_score >= 0.8:
            return PriorityLevel.URGENT
        elif priority_score >= 0.6:
            return PriorityLevel.HIGH
        elif priority_score >= 0.3:
            return PriorityLevel.NORMAL
        elif priority_score >= 0.1:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.ARCHIVE
    
    @log_function()
    async def _generate_recommendations(
        self,
        email: EmailMessage,
        sender_info: Dict[str, Any],
        spam_score: float,
        priority_score: float
    ) -> Tuple[List[EmailAction], str]:
        """
        Generate complete action recommendations based on analysis.
        
        Combines all analysis factors to recommend appropriate actions
        for email processing and user workflow optimization.
        
        Args:
            email: Email message being processed
            sender_info: Sender analysis results
            spam_score: Spam likelihood score
            priority_score: Priority assessment score
            
        Returns:
            Tuple of (recommended_actions, reasoning_explanation)
        """
        self.logger.debug("Generating action recommendations")
        
        actions = []
        reasoning_parts = []
        
        try:
            # Spam handling (highest priority)
            if spam_score > self.spam_threshold:
                if spam_score > 0.9:
                    actions.append(EmailAction.SPAM_DELETE)
                    reasoning_parts.append(f"High spam confidence ({spam_score:.2f})")
                else:
                    actions.append(EmailAction.SPAM_QUARANTINE)
                    reasoning_parts.append(f"Probable spam ({spam_score:.2f})")
            
            # If not spam, proceed with other actions
            elif spam_score <= self.spam_threshold:
                
                # Priority handling
                if priority_score > self.priority_threshold:
                    actions.append(EmailAction.PRIORITIZE)
                    reasoning_parts.append(f"High priority ({priority_score:.2f})")
                
                # Trust-based actions
                trust_level = sender_info['trust_level']
                
                if trust_level in [TrustLevel.HIGH, TrustLevel.HIGHEST]:
                    # High trust senders get streamlined processing
                    if priority_score > 0.4:
                        actions.append(EmailAction.REQUIRE_ATTENTION)
                        reasoning_parts.append("Trusted sender with important content")
                    else:
                        actions.append(EmailAction.CATEGORIZE)
                        reasoning_parts.append("Trusted sender, auto-categorize")
                
                elif trust_level == TrustLevel.MEDIUM:
                    # Medium trust gets standard processing
                    actions.append(EmailAction.CATEGORIZE)
                    if priority_score > 0.5:
                        actions.append(EmailAction.REQUIRE_ATTENTION)
                        reasoning_parts.append("Moderate trust with elevated priority")
                    else:
                        reasoning_parts.append("Standard processing for known sender")
                
                else:  # LOW or NONE trust
                    # Unknown senders need more scrutiny
                    actions.append(EmailAction.REQUIRE_ATTENTION)
                    reasoning_parts.append("Unknown sender requires review")
                
                # Content-based actions
                if email.attachments:
                    # Always extract contacts from emails with attachments
                    actions.append(EmailAction.EXTRACT_CONTACTS)
                    reasoning_parts.append("Attachments present, extract contacts")
                    
                    # Check for asset documents
                    doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
                    has_docs = any(
                        any(att.lower().endswith(ext) for ext in doc_extensions)
                        for att in email.attachments
                    )
                    if has_docs:
                        actions.append(EmailAction.ASSET_DOCUMENT)
                        reasoning_parts.append("Document attachments suggest asset materials")
                
                # Regulatory and compliance checks
                content_lower = f"{email.subject} {email.content}".lower()
                compliance_keywords = ['sec', 'finra', 'audit', 'compliance', 'regulatory']
                
                if any(keyword in content_lower for keyword in compliance_keywords):
                    actions.append(EmailAction.COMPLIANCE_FLAG)
                    actions.append(EmailAction.REGULATORY_FILING)
                    reasoning_parts.append("Regulatory/compliance content detected")
                
                # Auto-response for specific scenarios
                auto_response_triggers = ['out of office', 'vacation', 'thank you']
                if (trust_level in [TrustLevel.HIGH, TrustLevel.HIGHEST] and
                    any(trigger in content_lower for trigger in auto_response_triggers)):
                    actions.append(EmailAction.AUTO_RESPOND)
                    reasoning_parts.append("Appropriate for automated response")
                
                # Archive low-priority emails from trusted sources
                if (trust_level in [TrustLevel.MEDIUM, TrustLevel.HIGH] and
                    priority_score < 0.2):
                    actions.append(EmailAction.ARCHIVE)
                    reasoning_parts.append("Low priority from trusted source")
            
            # Always extract contacts from legitimate emails
            if spam_score < 0.3 and EmailAction.EXTRACT_CONTACTS not in actions:
                actions.append(EmailAction.EXTRACT_CONTACTS)
                reasoning_parts.append("Legitimate email, extract contact information")
            
            # Ensure we have at least one action
            if not actions:
                actions.append(EmailAction.REQUIRE_ATTENTION)
                reasoning_parts.append("Default action: manual review")
            
            reasoning = "; ".join(reasoning_parts)
            
            self.logger.debug(f"Generated {len(actions)} actions: {[a.value for a in actions]}")
            
            return actions, reasoning
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return [EmailAction.REQUIRE_ATTENTION], f"Recommendation generation failed: {e}"
    
    @log_function()
    def _calculate_confidence(
        self,
        sender_info: Dict[str, Any],
        spam_score: float,
        priority_score: float
    ) -> float:
        """
        Calculate overall confidence in the analysis results.
        
        Considers multiple factors to assess how confident we should be
        in the analysis and recommendations.
        
        Args:
            sender_info: Sender analysis results
            spam_score: Spam assessment score
            priority_score: Priority assessment score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Sender confidence
        sender_confidence = sender_info.get('confidence', 0.1)
        confidence_factors.append(sender_confidence * 0.4)  # 40% weight
        
        # Trust level confidence (higher trust = higher confidence)
        trust_confidence = self.trust_weights[sender_info['trust_level']]
        confidence_factors.append(trust_confidence * 0.3)  # 30% weight
        
        # Spam score confidence (extreme scores are more confident)
        if spam_score > 0.8 or spam_score < 0.2:
            spam_confidence = 0.9  # High confidence in extreme scores
        elif spam_score > 0.6 or spam_score < 0.4:
            spam_confidence = 0.7  # Medium confidence
        else:
            spam_confidence = 0.4  # Low confidence in uncertain range
        confidence_factors.append(spam_confidence * 0.2)  # 20% weight
        
        # Priority score confidence
        if priority_score > 0.7 or priority_score < 0.3:
            priority_confidence = 0.8
        else:
            priority_confidence = 0.5
        confidence_factors.append(priority_confidence * 0.1)  # 10% weight
        
        # Calculate weighted average
        total_confidence = sum(confidence_factors)
        
        # Ensure within bounds
        final_confidence = max(0.0, min(1.0, total_confidence))
        
        self.logger.debug(f"Calculated confidence: {final_confidence:.3f}")
        
        return final_confidence
    
    @log_function()
    async def _store_analysis(self, email: EmailMessage, analysis: EmailAnalysis) -> None:
        """
        Store analysis results in episodic memory for learning.
        
        Records the complete analysis for future pattern recognition
        and decision improvement.
        
        Args:
            email: Email message that was analyzed
            analysis: Analysis results to store
        """
        try:
            # Store in episodic memory
            content = (
                f"Email analysis: {email.sender} - "
                f"trust={analysis.trust_level.value}, "
                f"priority={analysis.priority_level.value}, "
                f"actions={len(analysis.recommended_actions)}"
            )
            
            metadata = {
                'analysis_type': 'email_supervision',
                'sender': email.sender,
                'subject': email.subject[:100],  # Truncate long subjects
                'trust_level': analysis.trust_level.value,
                'spam_score': analysis.spam_score,
                'priority_score': analysis.priority_score,
                'priority_level': analysis.priority_level.value,
                'actions': [action.value for action in analysis.recommended_actions],
                'confidence': analysis.confidence,
                'processing_time': analysis.processing_time,
                'timestamp': datetime.now(UTC).isoformat(),
                'email_id': email.id
            }
            
            await self.episodic_memory.add(content, metadata)
            self.logger.debug(f"Stored analysis for {email.sender}")
            
        except Exception as e:
            self.logger.warning(f"Failed to store analysis: {e}")
    
    @log_function()
    async def provide_feedback(
        self,
        email_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any]
    ) -> None:
        """
        Process user feedback to improve future decisions.
        
        Learns from user corrections and preferences to improve
        future email processing accuracy.
        
        Args:
            email_id: ID of the email being given feedback on
            feedback_type: Type of feedback (spam, priority, action, etc.)
            feedback_data: Detailed feedback information
        """
        try:
            self.logger.info(f"Processing feedback for email {email_id}: {feedback_type}")
            
            # Store feedback in episodic memory
            content = f"User feedback: {feedback_type} for email {email_id}"
            
            metadata = {
                'feedback_type': feedback_type,
                'email_id': email_id,
                'feedback_data': feedback_data,
                'timestamp': datetime.now(UTC).isoformat(),
                'learning_signal': True
            }
            
            await self.episodic_memory.add(content, metadata)
            
            # Update semantic patterns based on feedback
            if feedback_type == 'spam_correction':
                # Learn about spam patterns
                sender = feedback_data.get('sender')
                is_spam = feedback_data.get('is_spam', False)
                
                if sender:
                    trust_level = 'none' if is_spam else 'medium'
                    sender_type = 'spam' if is_spam else 'verified'
                    
                    await self.semantic_memory.add(
                        content=f"Sender feedback: {sender} is {'spam' if is_spam else 'legitimate'}",
                        metadata={
                            'sender_email': sender,
                            'trust_level': trust_level,
                            'sender_type': sender_type,
                            'user_verified': True,
                            'feedback_date': datetime.now(UTC).isoformat()
                        }
                    )
            
            elif feedback_type == 'priority_correction':
                # Learn about priority patterns
                sender = feedback_data.get('sender')
                correct_priority = feedback_data.get('correct_priority')
                
                if sender and correct_priority:
                    await self.semantic_memory.add(
                        content=f"Priority feedback: {sender} emails are {correct_priority} priority",
                        metadata={
                            'sender_email': sender,
                            'priority_level': correct_priority,
                            'user_verified': True,
                            'feedback_date': datetime.now(UTC).isoformat()
                        }
                    )
            
            self.logger.info(f"Feedback processed and stored for {email_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process feedback: {e}")
    
    @log_function()
    async def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about email processing performance.
        
        Returns:
            Dictionary with processing metrics and statistics
        """
        try:
            # Search for recent analyses
            recent_analyses = await self.episodic_memory.search(
                query="email analysis",
                limit=100
            )
            
            stats = {
                'total_processed': len(recent_analyses),
                'trust_distribution': {},
                'priority_distribution': {},
                'action_distribution': {},
                'avg_processing_time': 0.0,
                'avg_confidence': 0.0
            }
            
            total_time = 0.0
            total_confidence = 0.0
            
            for memory_item, score in recent_analyses:
                if score > 0.7:  # High relevance
                    metadata = memory_item.metadata
                    
                    # Trust level distribution
                    trust = metadata.get('trust_level', 'unknown')
                    stats['trust_distribution'][trust] = stats['trust_distribution'].get(trust, 0) + 1
                    
                    # Priority level distribution
                    priority = metadata.get('priority_level', 'unknown')
                    stats['priority_distribution'][priority] = stats['priority_distribution'].get(priority, 0) + 1
                    
                    # Action distribution
                    actions = metadata.get('actions', [])
                    for action in actions:
                        stats['action_distribution'][action] = stats['action_distribution'].get(action, 0) + 1
                    
                    # Timing and confidence
                    processing_time = metadata.get('processing_time', 0.0)
                    confidence = metadata.get('confidence', 0.0)
                    
                    total_time += processing_time
                    total_confidence += confidence
            
            # Calculate averages
            if stats['total_processed'] > 0:
                stats['avg_processing_time'] = total_time / stats['total_processed']
                stats['avg_confidence'] = total_confidence / stats['total_processed']
            
            self.logger.info(f"Processing statistics: {stats['total_processed']} emails processed")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {e}")
            return {'error': str(e)}


@log_function()
async def demo_supervisor() -> None:
    """
    Demonstration of the email supervisor system.
    
    Shows how to use the EmailSupervisor with sample email data
    and displays complete analysis results.
    """
    print("🎯 Email Management Supervisor Demo")
    print("=" * 50)
    
    # Initialize supervisor
    supervisor = EmailSupervisor()
    
    # Sample emails for demonstration
    test_emails = [
        EmailMessage(
            id="demo_001",
            sender="colleague@business.com",
            subject="Quarterly Review Meeting - Action Required",
            content="""Hi team,

I need to schedule our quarterly review meeting for next week. 
This is time sensitive as we have the board presentation on Friday.

Please let me know your availability by Wednesday.

Best regards,
John""",
            attachments=["Q4_Review_Agenda.pdf"],
            received_date=datetime.now(UTC)
        ),
        EmailMessage(
            id="demo_002",
            sender="compliance@regulator.gov",
            subject="URGENT: Regulatory Filing Due Date Reminder",
            content="""Dear Compliance Officer,

This is a reminder that your Form ADV filing is due within 10 days.
Failure to file on time may result in regulatory action.

Please ensure all required documentation is submitted.

Regulatory Affairs Division""",
            attachments=["Form_ADV_Instructions.pdf", "Filing_Checklist.xlsx"],
            received_date=datetime.now(UTC)
        ),
        EmailMessage(
            id="demo_003",
            sender="noreply@spam-site.tk",
            subject="URGENT!!! Make Money Fast - Limited Time!!!",
            content="""CONGRATULATIONS!!! You've been selected for our exclusive money-making opportunity!

ACT NOW to secure your financial future! This limited time offer expires soon!

Click here to claim your $10,000 bonus!!!""",
            attachments=[],
            received_date=datetime.now(UTC)
        )
    ]
    
    # Process each email
    for email in test_emails:
        print(f"\n📧 Processing: {email.subject}")
        print(f"   From: {email.sender}")
        print(f"   Attachments: {len(email.attachments)}")
        
        analysis = await supervisor.process_email(email)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Trust Level: {analysis.trust_level.value}")
        print(f"   Priority Level: {analysis.priority_level.value}")
        print(f"   Spam Score: {analysis.spam_score:.3f}")
        print(f"   Priority Score: {analysis.priority_score:.3f}")
        print(f"   Confidence: {analysis.confidence:.3f}")
        print(f"   Processing Time: {analysis.processing_time:.3f}s")
        
        print(f"\n💡 Recommended Actions:")
        for action in analysis.recommended_actions:
            print(f"   • {action.value}")
        
        print(f"\n🧠 Reasoning: {analysis.reasoning}")
    
    # Show processing statistics
    stats = await supervisor.get_processing_statistics()
    print(f"\n📈 Processing Statistics:")
    print(f"   Total Processed: {stats.get('total_processed', 0)}")
    print(f"   Average Processing Time: {stats.get('avg_processing_time', 0):.3f}s")
    print(f"   Average Confidence: {stats.get('avg_confidence', 0):.3f}")
    
    trust_dist = stats.get('trust_distribution', {})
    if trust_dist:
        print(f"   Trust Distribution: {trust_dist}")
    
    print("\n✨ Demo completed!")


if __name__ == "__main__":
    # Run demo if executed directly
    asyncio.run(demo_supervisor()) 
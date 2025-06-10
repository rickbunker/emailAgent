"""
Spam Detection Agent for Email Document Management

A hybrid spam detection system designed for private market asset
management professionals who need reliable email filtering without false positives
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
    Designed for finance professionals who cannot afford to miss important
    emails from clients, counterparties, or regulators. Emphasis on minimizing
    false positives while maintaining strong protection against threats.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

import asyncio
import re
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import socket
import hashlib
from datetime import datetime, UTC
from urllib.parse import urlparse
import json

# External dependencies (install with pip if needed)
try:
    import requests
    import dns.resolver
except ImportError:
    # Graceful degradation if optional dependencies not available
    requests = None
    dns = None

# Memory system integration
from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory
from ..memory.contact import ContactMemory

# SpamAssassin integration
from ..tools.spamassassin_integration import SpamAssassinIntegration

# Logging system integration
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

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
    headers: Dict[str, str] = field(default_factory=dict)
    received_date: Optional[datetime] = None
    size: Optional[int] = None
    attachments: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate email data after initialization."""
        if not self.id:
            raise ValueError("Email ID cannot be empty")
        if not self.sender or '@' not in self.sender:
            raise ValueError(f"Invalid sender email: {self.sender}")
        if self.size is not None and self.size < 0:
            raise ValueError("Email size cannot be negative")


class SpamConfidence(Enum):
    """
    Confidence levels for spam detection with precise thresholds.
    
    These levels help downstream systems make appropriate decisions
    about email handling (block, quarantine, deliver with warning, etc.).
    """
    DEFINITELY_SPAM = "definitely_spam"      # 90%+ confidence - safe to block
    LIKELY_SPAM = "likely_spam"             # 70-90% confidence - quarantine
    SUSPICIOUS = "suspicious"               # 40-70% confidence - flag for review
    UNCERTAIN = "uncertain"                 # 20-40% confidence - deliver with caution
    LIKELY_CLEAN = "likely_clean"           # 5-20% confidence - deliver normally
    DEFINITELY_CLEAN = "definitely_clean"   # <5% confidence - whitelist


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
    spamassassin_score: Optional[float] = None
    reasons: List[SpamReason] = field(default_factory=list)
    blacklist_hits: List[str] = field(default_factory=list)
    content_flags: List[str] = field(default_factory=list)
    recommendation: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def __post_init__(self) -> None:
        """Validate spam analysis data after initialization."""
        if not 0.0 <= self.spam_score <= 100.0:
            raise ValueError(f"Spam score must be 0-100, got {self.spam_score}")
        if self.processing_time < 0:
            raise ValueError("Processing time cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage or serialization."""
        return {
            'is_spam': self.is_spam,
            'confidence': self.confidence.value,
            'spam_score': self.spam_score,
            'spamassassin_score': self.spamassassin_score,
            'reasons': [r.value for r in self.reasons],
            'blacklist_hits': self.blacklist_hits,
            'content_flags': self.content_flags,
            'recommendation': self.recommendation,
            'details': self.details,
            'processing_time': self.processing_time
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
        # Initialize memory systems
        self.procedural_memory = ProceduralMemory(max_items=1000)
        self.semantic_memory = SemanticMemory(max_items=1000)
        self.episodic_memory = EpisodicMemory(max_items=1000)
        self.contact_memory = ContactMemory(max_items=5000)
        
        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing Spam Detection Agent")
        
        # Spam trigger patterns from research and experience
        self.spam_words = [
            'free', 'earn', 'money', 'winner', 'cash', 'prize', 'urgent',
            'limited time', 'act now', 'double your income', 'guaranteed',
            'risk free', 'no obligation', 'call now', 'click here',
            'special offer', 'discount', 'save money', 'cheap', 'deal',
            'lose weight', 'viagra', 'cialis', 'pharmacy', 'debt relief',
            'work from home', 'make money fast', 'get rich quick'
        ]
        
        self.suspicious_patterns = [
            r'\$+',                # Multiple dollar signs
            r'%+',                 # Multiple percent signs  
            r'@+',                 # Multiple @ symbols
            r'[!]{2,}',            # Multiple exclamation marks
            r'[\?]{2,}',           # Multiple question marks
            r'[A-Z]{10,}',         # Long stretches of caps
            r'[\d]{1,3}%\s*OFF',   # Percentage discount patterns
            r'FREE\s*[!]+',        # FREE with emphasis
            r'URGENT[!]*',         # Urgent with emphasis
        ]
        
        # DNS blacklists to check (major reputation services)
        self.blacklists = [
            'zen.spamhaus.org',           # Spamhaus composite
            'bl.spamcop.net',             # SpamCop blocking list
            'dnsbl.sorbs.net',            # SORBS aggregate
            'psbl.surriel.com',           # Passive Spam Block List
            'dnsbl.njabl.org',            # Not Just Another Bogus List
            'cbl.abuseat.org',            # Composite Blocking List
            'pbl.spamhaus.org',           # Policy Block List
            'sbl.spamhaus.org',           # Spam Block List
            'css.spamhaus.org',           # CSS reputation
            'xbl.spamhaus.org',           # Exploits Block List
        ]
        
        # Initialize SpamAssassin integration
        try:
            self.spamassassin = SpamAssassinIntegration(threshold=spamassassin_threshold)
            self.logger.info(f"SpamAssassin initialized with threshold {spamassassin_threshold}")
        except Exception as e:
            self.logger.warning(f"SpamAssassin initialization failed: {e}")
            self.spamassassin = None
        
        # Phishing indicators
        self.phishing_patterns = [
            r'verify\s+your\s+account',
            r'click\s+here\s+to\s+confirm',
            r'suspended\s+account',
            r'expire.*?\d+.*?hours?',
            r'update.*?payment.*?information',
            r'security.*?alert',
            r'unauthorized.*?access',
        ]
        
        self.logger.info("Spam Detection Agent initialized successfully")
    
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
        
        try:
            # Initialize analysis with defaults
            analysis = SpamAnalysis(
                is_spam=False,
                confidence=SpamConfidence.LIKELY_CLEAN,
                spam_score=0.0
            )
            
            # Step 1: Check if sender is a trusted contact (high priority)
            trusted_contact = await self._check_trusted_contact(email.sender)
            if trusted_contact:
                analysis.spam_score -= 30  # Significant trust bonus
                analysis.details['trusted_contact'] = trusted_contact
                self.logger.info(f"Trusted contact detected: {trusted_contact}")
            
            # Step 2: Check spam history for this sender
            spam_history = await self._check_spam_history(email.sender)
            if spam_history:
                analysis.spam_score += 50
                analysis.reasons.append(SpamReason.USER_PREVIOUS_SPAM)
                analysis.details['spam_history'] = spam_history
                self.logger.warning(f"Previous spam detected from {email.sender}")
            
            # Step 3: Run SpamAssassin analysis if available
            if self.spamassassin:
                sa_result = await self._run_spamassassin(email)
                if sa_result is not None:
                    sa_score, sa_details = sa_result
                    analysis.spamassassin_score = sa_score
                    analysis.spam_score += sa_score * 2  # Weight SpamAssassin results
                    analysis.details['spamassassin_details'] = sa_details
                    if sa_score >= self.spamassassin.threshold:
                        analysis.reasons.append(SpamReason.SPAMASSASSIN_HIGH_SCORE)
                    self.logger.debug(f"SpamAssassin score: {sa_score}")
            else:
                self.logger.debug("SpamAssassin not available, skipping")
            
            # Step 4: Check sender IP/domain against blacklists
            blacklist_results = await self._check_blacklists(email.sender)
            if blacklist_results:
                analysis.blacklist_hits.extend(blacklist_results)
                analysis.spam_score += len(blacklist_results) * 20  # Significant penalty
                
                # Categorize by type of blacklist hit
                domain_hits = [hit for hit in blacklist_results if 'domain' in hit.lower()]
                ip_hits = [hit for hit in blacklist_results if hit not in domain_hits]
                
                if domain_hits:
                    analysis.reasons.append(SpamReason.BLACKLISTED_DOMAIN)
                if ip_hits:
                    analysis.reasons.append(SpamReason.BLACKLISTED_IP)
                
                self.logger.warning(f"Blacklist hits: {len(blacklist_results)}")
            
            # Step 5: Analyze email content
            content_score, content_flags = self._analyze_content(email)
            analysis.spam_score += content_score
            analysis.content_flags.extend(content_flags)
            
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
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Spam analysis failed for {email.sender}: {e}")
            # Return safe default
            return SpamAnalysis(
                is_spam=False,
                confidence=SpamConfidence.UNCERTAIN,
                spam_score=50.0,
                recommendation="Analysis failed - manual review recommended",
                details={'error': str(e)},
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    @log_function()
    async def _check_trusted_contact(self, sender_email: str) -> Optional[str]:
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
                query=sender_email,
                limit=1
            )
            
            if search_results:
                memory_item, score = search_results[0]
                if score > 0.8:  # High confidence match
                    contact_data = memory_item.metadata
                    confidence = contact_data.get('confidence', 'unknown')
                    contact_type = contact_data.get('contact_type', 'unknown')
                    
                    # Return trust information
                    if confidence in ['high', 'medium'] and contact_type != 'vendor':
                        return f"{contact_type}_{confidence}"
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to check trusted contact for {sender_email}: {e}")
            return None
    
    @log_function()
    async def _check_spam_history(self, sender_email: str) -> Optional[Dict[str, Any]]:
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
                query=f"spam {sender_email}",
                limit=3
            )
            
            spam_count = 0
            recent_spam = False
            
            for memory_item, score in search_results:
                if score > 0.7:  # Good match
                    metadata = memory_item.metadata
                    if metadata.get('classification') == 'spam':
                        spam_count += 1
                        
                        # Check if recent (last 30 days)
                        classification_date = metadata.get('date')
                        if classification_date:
                            try:
                                class_dt = datetime.fromisoformat(classification_date.replace('Z', '+00:00'))
                                days_ago = (datetime.now(UTC) - class_dt).days
                                if days_ago <= 30:
                                    recent_spam = True
                            except:
                                pass
            
            if spam_count > 0:
                return {
                    'spam_count': spam_count,
                    'recent_spam': recent_spam,
                    'sender': sender_email
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to check spam history for {sender_email}: {e}")
            return None
    
    @log_function()
    async def _run_spamassassin(self, email: EmailMessage) -> Optional[Tuple[float, str]]:
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
                return (result['score'], result.get('summary', ''))
            
            return None
            
        except Exception as e:
            self.logger.warning(f"SpamAssassin analysis failed: {e}")
            return None
    
    @log_function()
    async def _check_blacklists(self, sender_email: str) -> List[str]:
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
        domain = sender_email.split('@')[1] if '@' in sender_email else sender_email
        
        try:
            # Get IP address for domain
            try:
                ip_result = socket.gethostbyname(domain)
                ip_parts = ip_result.split('.')
                reversed_ip = '.'.join(reversed(ip_parts))
            except socket.gaierror:
                self.logger.debug(f"Could not resolve IP for domain {domain}")
                return hits
            
            # Check each blacklist
            for blacklist in self.blacklists:
                try:
                    query = f"{reversed_ip}.{blacklist}"
                    result = dns.resolver.resolve(query, 'A')
                    
                    # If we get a result, the IP is blacklisted
                    if result:
                        hits.append(f"{blacklist} (IP: {ip_result})")
                        self.logger.debug(f"Blacklist hit: {blacklist} for IP {ip_result}")
                
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    # Not found in this blacklist (good)
                    continue
                except Exception as e:
                    self.logger.debug(f"Blacklist check failed for {blacklist}: {e}")
                    continue
            
            # Also check domain-based blacklists
            domain_blacklists = ['dbl.spamhaus.org', 'multi.surbl.org']
            for blacklist in domain_blacklists:
                try:
                    query = f"{domain}.{blacklist}"
                    result = dns.resolver.resolve(query, 'A')
                    if result:
                        hits.append(f"{blacklist} (domain: {domain})")
                        self.logger.debug(f"Domain blacklist hit: {blacklist} for {domain}")
                
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    continue
                except Exception as e:
                    self.logger.debug(f"Domain blacklist check failed for {blacklist}: {e}")
                    continue
            
            return hits
            
        except Exception as e:
            self.logger.warning(f"Blacklist checking failed: {e}")
            return []
    
    @log_function()
    def _analyze_content(self, email: EmailMessage) -> Tuple[float, List[str]]:
        """
        Analyze email content for spam indicators.
        
        Args:
            email: Email to analyze
            
        Returns:
            Tuple of (spam_score_increase, content_flags)
        """
        content = f"{email.subject} {email.content}".lower()
        flags = []
        score = 0.0
        
        # Check for spam words
        spam_word_count = 0
        for word in self.spam_words:
            if word in content:
                spam_word_count += 1
                score += 2.0
        
        if spam_word_count > 3:
            flags.append(f"spam_words_{spam_word_count}")
        
        # Check for suspicious patterns
        pattern_count = 0
        for pattern in self.suspicious_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            if matches > 0:
                pattern_count += matches
                score += matches * 1.5
        
        if pattern_count > 2:
            flags.append(f"suspicious_patterns_{pattern_count}")
        
        # Check for excessive capitalization
        caps_ratio = sum(1 for c in email.subject + email.content if c.isupper()) / max(len(email.subject + email.content), 1)
        if caps_ratio > 0.3:
            score += 10.0
            flags.append("excessive_caps")
        
        # Check for excessive punctuation
        punct_count = len(re.findall(r'[!?]{2,}', content))
        if punct_count > 2:
            score += punct_count * 2.0
            flags.append("excessive_punctuation")
        
        # Check for suspicious links
        url_count = len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content))
        if url_count > 3:
            score += url_count * 3.0
            flags.append(f"many_links_{url_count}")
        
        # Check for suspicious domains in URLs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.club', '.download']
        for tld in suspicious_tlds:
            if tld in content:
                score += 5.0
                flags.append(f"suspicious_tld_{tld}")
        
        # Check for financial/urgency indicators
        urgency_words = ['urgent', 'immediate', 'expire', 'limited time', 'act now', 'hurry']
        urgency_count = sum(1 for word in urgency_words if word in content)
        if urgency_count > 1:
            score += urgency_count * 3.0
            flags.append("urgency_indicators")
        
        self.logger.debug(f"Content analysis: score={score:.1f}, flags={flags}")
        
        return score, flags
    
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
        for pattern in self.phishing_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            if matches > 0:
                score += matches * 8.0  # High penalty for phishing patterns
                self.logger.debug(f"Phishing pattern match: {pattern}")
        
        # Check for credential harvesting terms
        cred_terms = ['username', 'password', 'login', 'sign in', 'verify account']
        cred_count = sum(1 for term in cred_terms if term in content)
        if cred_count > 2:
            score += cred_count * 5.0
        
        # Check for impersonation attempts
        impersonation_terms = ['bank', 'paypal', 'amazon', 'microsoft', 'apple', 'google']
        domain = email.sender.split('@')[1] if '@' in email.sender else ''
        
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
        spf_header = headers.get('received-spf', '').lower()
        if 'fail' in spf_header:
            score += 15.0
        elif 'softfail' in spf_header:
            score += 8.0
        elif 'none' in spf_header or not spf_header:
            score += 5.0
        
        # Check DKIM
        dkim_header = headers.get('dkim-signature', '')
        if not dkim_header:
            score += 5.0
        
        # Check DMARC
        auth_results = headers.get('authentication-results', '').lower()
        if 'dmarc=fail' in auth_results:
            score += 20.0
        elif 'dmarc=none' in auth_results or 'dmarc' not in auth_results:
            score += 3.0
        
        return score
    
    @log_function()
    async def _apply_spam_rules(self, email: EmailMessage, analysis: SpamAnalysis) -> float:
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
                query=f"spam detection rule",
                limit=5
            )
            
            additional_score = 0.0
            
            for memory_item, score in search_results:
                if score > 0.7:  # Good relevance match
                    rule_data = memory_item.metadata
                    rule_type = rule_data.get('rule_type', '')
                    
                    # Apply different types of learned rules
                    if rule_type == 'sender_pattern':
                        pattern = rule_data.get('pattern', '')
                        if pattern and pattern in email.sender:
                            additional_score += rule_data.get('penalty', 10.0)
                    
                    elif rule_type == 'content_pattern':
                        pattern = rule_data.get('pattern', '')
                        if pattern and pattern in email.content.lower():
                            additional_score += rule_data.get('penalty', 5.0)
                    
                    elif rule_type == 'subject_pattern':
                        pattern = rule_data.get('pattern', '')
                        if pattern and pattern in email.subject.lower():
                            additional_score += rule_data.get('penalty', 8.0)
            
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
    async def _store_spam_analysis(self, email: EmailMessage, analysis: SpamAnalysis) -> None:
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
                'analysis_type': 'spam_detection',
                'sender': email.sender,
                'subject': email.subject,
                'classification': 'spam' if analysis.is_spam else 'clean',
                'confidence': analysis.confidence.value,
                'spam_score': analysis.spam_score,
                'reasons': [r.value for r in analysis.reasons],
                'date': datetime.now(UTC).isoformat(),
                'email_id': email.id
            }
            
            await self.episodic_memory.add(content, metadata)
            self.logger.debug(f"Stored spam analysis for {email.sender}")
            
        except Exception as e:
            self.logger.warning(f"Failed to store spam analysis: {e}")
    
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
                'feedback_type': 'user_spam_report',
                'sender': email.sender,
                'subject': email.subject,
                'classification': 'spam',
                'user_feedback': user_feedback,
                'date': datetime.now(UTC).isoformat(),
                'email_id': email.id
            }
            
            await self.episodic_memory.add(content, metadata)
            
            # Update semantic memory with sender information
            await self.semantic_memory.add(
                content=f"Spam sender: {email.sender}",
                metadata={
                    'sender_email': email.sender,
                    'sender_type': 'spam',
                    'trust_level': 'none',
                    'user_marked': True,
                    'last_updated': datetime.now(UTC).isoformat()
                }
            )
            
            self.logger.info(f"User spam feedback recorded for {email.sender}")
            
        except Exception as e:
            self.logger.error(f"Failed to record spam feedback: {e}")
    
    @log_function()
    async def mark_as_not_spam(self, email: EmailMessage, user_feedback: str = "") -> None:
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
                'feedback_type': 'user_ham_report',
                'sender': email.sender,
                'subject': email.subject,
                'classification': 'clean',
                'user_feedback': user_feedback,
                'date': datetime.now(UTC).isoformat(),
                'email_id': email.id
            }
            
            await self.episodic_memory.add(content, metadata)
            
            # Update semantic memory to mark as trusted
            await self.semantic_memory.add(
                content=f"Trusted sender: {email.sender}",
                metadata={
                    'sender_email': email.sender,
                    'sender_type': 'trusted',
                    'trust_level': 'high',
                    'user_verified': True,
                    'last_updated': datetime.now(UTC).isoformat()
                }
            )
            
            self.logger.info(f"User not-spam feedback recorded for {email.sender}")
            
        except Exception as e:
            self.logger.error(f"Failed to record not-spam feedback: {e}")
    
    @log_function()
    async def get_spam_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about spam detection performance.
        
        Returns:
            Dictionary with spam detection metrics and statistics
        """
        try:
            # Search for recent spam analyses
            recent_analyses = await self.episodic_memory.search(
                query="spam analysis",
                limit=100
            )
            
            stats = {
                'total_analyses': len(recent_analyses),
                'spam_detected': 0,
                'clean_emails': 0,
                'confidence_distribution': {},
                'common_reasons': {},
                'user_feedback_count': 0
            }
            
            for memory_item, score in recent_analyses:
                if score > 0.7:  # Good match
                    metadata = memory_item.metadata
                    classification = metadata.get('classification', 'unknown')
                    
                    if classification == 'spam':
                        stats['spam_detected'] += 1
                    elif classification == 'clean':
                        stats['clean_emails'] += 1
                    
                    # Track confidence distribution
                    confidence = metadata.get('confidence', 'unknown')
                    stats['confidence_distribution'][confidence] = stats['confidence_distribution'].get(confidence, 0) + 1
                    
                    # Track common reasons
                    reasons = metadata.get('reasons', [])
                    for reason in reasons:
                        stats['common_reasons'][reason] = stats['common_reasons'].get(reason, 0) + 1
            
            # Get user feedback statistics
            feedback_results = await self.episodic_memory.search(
                query="user feedback",
                limit=50
            )
            stats['user_feedback_count'] = len([r for r in feedback_results if r[1] > 0.7])
            
            self.logger.info(f"Spam statistics: {stats['total_analyses']} analyses, {stats['spam_detected']} spam")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get spam statistics: {e}")
            return {'error': str(e)}


@log_function()
async def demo_spam_detector() -> None:
    """
    Demonstration of the spam detection system.
    
    Shows how to use the SpamDetector with sample email data
    and displays the analysis results.
    """
    print("🛡️ Spam Detection Agent Demo")
    print("=" * 50)
    
    # Initialize detector
    detector = SpamDetector()
    
    # Sample emails for demonstration
    test_emails = [
        EmailMessage(
            id="demo_001",
            sender="colleague@business.com",
            subject="Quarterly Review Meeting",
            content="""Hi team,

I wanted to schedule our quarterly review meeting for next week. 
Please let me know your availability.

Best regards,
John""",
            headers={"Received-SPF": "pass"}
        ),
        EmailMessage(
            id="demo_002",
            sender="noreply@spamsite.tk",
            subject="URGENT!!! WIN $1000000 NOW!!!",
            content="""CONGRATULATIONS!!! You have WON the LOTTERY!!!

CLICK HERE to claim your $1,000,000 prize NOW!!!
This offer expires in 24 hours!!!

ACT NOW!!! Don't miss this LIMITED TIME offer!!!""",
            headers={}
        ),
        EmailMessage(
            id="demo_003",
            sender="security@phishing-site.com",
            subject="Account Security Alert",
            content="""Your account has been suspended due to suspicious activity.

Please verify your account by clicking here and entering your username and password.

Failure to verify within 24 hours will result in permanent suspension.""",
            headers={"Received-SPF": "fail"}
        )
    ]
    
    # Analyze each email
    for email in test_emails:
        print(f"\n📧 Analyzing: {email.subject}")
        print(f"   From: {email.sender}")
        
        analysis = await detector.analyze_spam(email)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Classification: {'SPAM' if analysis.is_spam else 'CLEAN'}")
        print(f"   Confidence: {analysis.confidence.value}")
        print(f"   Spam Score: {analysis.spam_score:.1f}/100")
        print(f"   Recommendation: {analysis.recommendation}")
        
        if analysis.reasons:
            print(f"   Reasons: {', '.join([r.value for r in analysis.reasons])}")
        
        if analysis.blacklist_hits:
            print(f"   Blacklist Hits: {', '.join(analysis.blacklist_hits)}")
        
        if analysis.content_flags:
            print(f"   Content Flags: {', '.join(analysis.content_flags)}")
        
        print(f"   Processing Time: {analysis.processing_time:.3f}s")
    
    # Show statistics
    stats = await detector.get_spam_statistics()
    print(f"\n📈 Detection Statistics:")
    print(f"   Total Analyses: {stats.get('total_analyses', 0)}")
    print(f"   Spam Detected: {stats.get('spam_detected', 0)}")
    print(f"   Clean Emails: {stats.get('clean_emails', 0)}")
    
    print("\n✨ Demo completed!")


if __name__ == "__main__":
    # Run demo if executed directly
    asyncio.run(demo_spam_detector()) 
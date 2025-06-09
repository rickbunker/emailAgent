"""
Spam Detection Agent

A hybrid spam detection system that combines:
1. Apache SpamAssassin for core spam detection
2. External blacklist checking services
3. Our own intelligent layer using memory systems
4. Contact-aware filtering (known contacts get different treatment)
5. Learning from user feedback

Based on proven techniques from spam filtering research.
"""

import asyncio
import re
import subprocess
import tempfile
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests
import socket
import dns.resolver
from datetime import datetime, UTC

from ..memory.procedural import ProceduralMemory
from ..memory.semantic import SemanticMemory
from ..memory.episodic import EpisodicMemory
from ..memory.contact import ContactMemory


# SpamAssassin integration
from ..tools.spamassassin_integration import SpamAssassinIntegration


# Email message data structure
@dataclass
class EmailMessage:
    """Represents an email message for analysis."""
    id: str
    sender: str
    subject: str
    content: str
    headers: Dict[str, str] = field(default_factory=dict)


class SpamConfidence(Enum):
    """Confidence levels for spam detection."""
    DEFINITELY_SPAM = "definitely_spam"      # 90%+ confidence
    LIKELY_SPAM = "likely_spam"             # 70-90% confidence  
    SUSPICIOUS = "suspicious"               # 40-70% confidence
    UNCERTAIN = "uncertain"                 # 20-40% confidence
    LIKELY_CLEAN = "likely_clean"           # 5-20% confidence
    DEFINITELY_CLEAN = "definitely_clean"   # <5% confidence


class SpamReason(Enum):
    """Reasons why an email was flagged as spam."""
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


@dataclass
class SpamAnalysis:
    """Results of spam analysis."""
    is_spam: bool
    confidence: SpamConfidence
    spam_score: float  # 0-100 scale
    spamassassin_score: Optional[float] = None
    reasons: List[SpamReason] = None
    blacklist_hits: List[str] = None
    content_flags: List[str] = None
    recommendation: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
        if self.blacklist_hits is None:
            self.blacklist_hits = []
        if self.content_flags is None:
            self.content_flags = []
        if self.details is None:
            self.details = {}


class SpamDetector:
    """
    Hybrid spam detection agent.
    
    Combines Apache SpamAssassin, blacklist checking, and our own
    intelligent analysis using memory systems and contact awareness.
    """
    
    def __init__(self):
        self.procedural_memory = ProceduralMemory(max_items=1000)
        self.semantic_memory = SemanticMemory(max_items=1000)
        self.episodic_memory = EpisodicMemory(max_items=1000)
        self.contact_memory = ContactMemory(max_items=5000)
        
        # Spam trigger patterns from research
        self.spam_words = [
            'free', 'earn', 'money', 'winner', 'cash', 'prize', 'urgent',
            'limited time', 'act now', 'double your income', 'guaranteed',
            'risk free', 'no obligation', 'call now', 'click here',
            'special offer', 'discount', 'save money', 'cheap', 'deal'
        ]
        
        self.suspicious_patterns = [
            r'\$+',           # Multiple dollar signs
            r'%+',            # Multiple percent signs  
            r'@+',            # Multiple @ symbols
            r'[!]{2,}',       # Multiple exclamation marks
            r'[\?]{2,}',      # Multiple question marks
            r'[A-Z]{10,}',    # Long stretches of caps
        ]
        
        # DNS blacklists to check
        self.blacklists = [
            'zen.spamhaus.org',           # Spamhaus
            'bl.spamcop.net',             # SpamCop
            'dnsbl.sorbs.net',            # SORBS
            'psbl.surriel.com',           # Passive Spam Block List
            'dnsbl.njabl.org',            # Not Just Another Bogus List
            'cbl.abuseat.org',            # Composite Blocking List
            'pbl.spamhaus.org',           # Policy Block List
            'sbl.spamhaus.org',           # Spam Block List
        ]
        
        # Initialize SpamAssassin integration
        self.spamassassin = SpamAssassinIntegration(threshold=5.0)
    
    async def analyze_spam(self, email: EmailMessage) -> SpamAnalysis:
        """
        Main entry point for spam analysis.
        
        Args:
            email: Email message to analyze
            
        Returns:
            SpamAnalysis: Detailed spam analysis results
        """
        print(f"🛡️ Analyzing spam for: {email.sender}")
        
        analysis = SpamAnalysis(
            is_spam=False,
            confidence=SpamConfidence.LIKELY_CLEAN,
            spam_score=0.0
        )
        
        # Step 1: Check if sender is a known contact (trusted)
        trusted_contact = await self._check_trusted_contact(email.sender)
        if trusted_contact:
            analysis.spam_score -= 20  # Significant trust bonus
            analysis.details['trusted_contact'] = trusted_contact
            print(f"   ✅ Trusted contact: {trusted_contact}")
        
        # Step 2: Check previous spam history
        spam_history = await self._check_spam_history(email.sender)
        if spam_history:
            analysis.spam_score += 40
            analysis.reasons.append(SpamReason.USER_PREVIOUS_SPAM)
            analysis.details['spam_history'] = spam_history
            print(f"   ⚠️ Previous spam from this sender")
        
        # Step 3: Run SpamAssassin analysis
        sa_result = await self._run_spamassassin(email)
        if sa_result is not None:
            sa_score, sa_details = sa_result
            analysis.spamassassin_score = sa_score
            analysis.spam_score += sa_score
            analysis.details['spamassassin_details'] = sa_details
            if sa_score >= 5.0:  # SpamAssassin threshold
                analysis.reasons.append(SpamReason.SPAMASSASSIN_HIGH_SCORE)
            print(f"   📊 SpamAssassin: {sa_score} [{sa_details[:50]}...]")
        else:
            print("   ⚠️ SpamAssassin unavailable or failed")
        
        # Step 4: Check sender IP/domain against blacklists
        blacklist_results = await self._check_blacklists(email.sender)
        if blacklist_results:
            analysis.blacklist_hits.extend(blacklist_results)
            analysis.spam_score += len(blacklist_results) * 15
            if any('domain' in result for result in blacklist_results):
                analysis.reasons.append(SpamReason.BLACKLISTED_DOMAIN)
            else:
                analysis.reasons.append(SpamReason.BLACKLISTED_IP)
            print(f"   🚫 Blacklist hits: {len(blacklist_results)}")
        
        # Step 5: Content analysis
        content_score, content_flags = self._analyze_content(email)
        analysis.spam_score += content_score
        analysis.content_flags.extend(content_flags)
        if content_score > 20:
            analysis.reasons.append(SpamReason.SUSPICIOUS_CONTENT)
        
        # Step 6: Check for phishing indicators
        phishing_score = self._check_phishing_indicators(email)
        analysis.spam_score += phishing_score
        if phishing_score > 15:
            analysis.reasons.append(SpamReason.PHISHING_INDICATORS)
        
        # Step 7: Check authentication
        auth_score = self._check_authentication(email)
        analysis.spam_score += auth_score
        if auth_score > 10:
            analysis.reasons.append(SpamReason.NO_AUTHENTICATION)
        
        # Step 8: Apply procedural memory rules
        rule_adjustments = await self._apply_spam_rules(email, analysis)
        analysis.spam_score += rule_adjustments
        
        # Step 9: Determine final classification
        analysis = self._classify_spam_score(analysis)
        
        # Step 10: Store analysis for learning
        await self._store_spam_analysis(email, analysis)
        
        return analysis
    
    async def _check_trusted_contact(self, sender_email: str) -> Optional[str]:
        """Check if sender is a trusted contact."""
        contact = await self.contact_memory.find_contact_by_email(sender_email)
        
        if contact:
            # High confidence contacts are trusted
            if contact.confidence.value == 'high':
                return f"{contact.name or contact.email} (trusted contact)"
            
            # Known contacts with relationship info
            if contact.relationship:
                return f"{contact.name or contact.email} ({contact.relationship})"
        
        # Check semantic memory for trusted senders
        trusted_results = await self.semantic_memory.search(
            f"{sender_email} trusted sender",
            filter={"must": [{"key": "metadata.trust_level", "match": {"value": "high"}}]},
            limit=1
        )
        
        if trusted_results:
            return trusted_results[0].content
        
        return None
    
    async def _check_spam_history(self, sender_email: str) -> Optional[Dict[str, Any]]:
        """Check if this sender has been marked as spam before."""
        spam_results = await self.episodic_memory.search(
            f"marked spam {sender_email}",
            filter={"must": [{"key": "metadata.type", "match": {"value": "spam_feedback"}}]},
            limit=3
        )
        
        if spam_results:
            return {
                'spam_count': len(spam_results),
                'last_spam': spam_results[0].metadata.get('created_at'),
                'patterns': [result.content for result in spam_results]
            }
        
        return None
    
    async def _run_spamassassin(self, email: EmailMessage) -> Optional[Tuple[float, str]]:
        """Run SpamAssassin analysis using our integrated SpamAssassin module."""
        try:
            # Format the email for SpamAssassin analysis
            formatted_email = self.spamassassin.format_email_for_analysis(
                sender=email.sender,
                subject=email.subject,
                content=email.content,
                message_id=f"<{email.id}@emailagent>"
            )
            
            # Run SpamAssassin check
            result = self.spamassassin.check_spam(formatted_email)
            
            if result:
                # Return score and details in the format expected by the rest of the code
                details = f"rules_hit: {','.join(result.rules_hit[:5])}"  # Limit to first 5 rules
                return (result.score, details)
            else:
                return None
                
        except Exception as e:
            print(f"[WARN] SpamAssassin integration error: {e}")
            return None
    
    async def _check_blacklists(self, sender_email: str) -> List[str]:
        """Check sender domain/IP against DNS blacklists."""
        domain = sender_email.split('@')[1] if '@' in sender_email else sender_email
        hits = []
        
        print(f"   🔍 Checking {domain} against {len(self.blacklists)} blacklists...")
        
        # Try to resolve domain to IP
        ip_address = None
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ip_address = str(answers[0])
            print(f"   📍 Resolved {domain} -> {ip_address}")
        except Exception as e:
            print(f"   ⚠️ Could not resolve {domain}: {e}")
        
        # Check domain and IP against blacklists
        checked_count = 0
        for blacklist in self.blacklists:
            try:
                checked_count += 1
                
                # Check domain reputation
                query_domain = f"{domain}.{blacklist}"
                try:
                    result = dns.resolver.resolve(query_domain, 'A')
                    # If we get a result, domain is blacklisted
                    blacklist_ip = str(result[0])
                    hits.append(f"domain:{blacklist}:{blacklist_ip}")
                    print(f"   🚫 BLACKLISTED: {domain} on {blacklist} ({blacklist_ip})")
                except dns.resolver.NXDOMAIN:
                    # Not blacklisted (expected)
                    pass
                except Exception as e:
                    print(f"   ⚠️ Domain check error for {blacklist}: {e}")
                
                # Check IP if available
                if ip_address:
                    reversed_ip = '.'.join(reversed(ip_address.split('.')))
                    query_ip = f"{reversed_ip}.{blacklist}"
                    try:
                        result = dns.resolver.resolve(query_ip, 'A')
                        # If we get a result, IP is blacklisted
                        blacklist_ip = str(result[0])
                        hits.append(f"ip:{blacklist}:{blacklist_ip}")
                        print(f"   🚫 BLACKLISTED: {ip_address} on {blacklist} ({blacklist_ip})")
                    except dns.resolver.NXDOMAIN:
                        # Not blacklisted (expected)
                        pass
                    except Exception as e:
                        print(f"   ⚠️ IP check error for {blacklist}: {e}")
                        
            except Exception as e:
                print(f"   ❌ Blacklist check failed for {blacklist}: {e}")
                continue
        
        print(f"   ✅ Checked {checked_count} blacklists, found {len(hits)} hits")
        return hits
    
    def _analyze_content(self, email: EmailMessage) -> Tuple[float, List[str]]:
        """Analyze email content for spam indicators."""
        score = 0.0
        flags = []
        
        content = email.content.lower()
        subject = email.subject.lower()
        full_text = f"{subject} {content}"
        
        # Check for spam words
        spam_word_count = 0
        for word in self.spam_words:
            if word in full_text:
                spam_word_count += 1
        
        if spam_word_count > 0:
            score += spam_word_count * 2
            flags.append(f"spam_words:{spam_word_count}")
        
        # Check suspicious patterns
        for pattern in self.suspicious_patterns:
            matches = re.findall(pattern, email.content)
            if matches:
                score += len(matches) * 3
                flags.append(f"pattern:{pattern}:{len(matches)}")
        
        # Check for excessive links
        link_count = len(re.findall(r'http[s]?://\S+', email.content))
        if link_count > 5:
            score += (link_count - 5) * 2
            flags.append(f"excessive_links:{link_count}")
        
        # Check for image-to-text ratio (>40% images is suspicious)
        image_count = len(re.findall(r'<img\s+[^>]*src=', email.content))
        text_length = len(re.sub(r'<[^>]*>', '', email.content).strip())
        
        if image_count > 0 and text_length < image_count * 20:  # Rough heuristic
            score += 10
            flags.append(f"high_image_ratio:{image_count}")
        
        # Check for ALL CAPS
        caps_words = re.findall(r'\b[A-Z]{3,}\b', email.content)
        if len(caps_words) > 3:
            score += len(caps_words) * 1.5
            flags.append(f"excessive_caps:{len(caps_words)}")
        
        return score, flags
    
    def _check_phishing_indicators(self, email: EmailMessage) -> float:
        """Check for phishing indicators."""
        score = 0.0
        content = email.content.lower()
        
        # Urgent action requests
        urgent_phrases = [
            'verify your account', 'suspended account', 'click immediately',
            'confirm identity', 'urgent action required', 'expires today'
        ]
        
        for phrase in urgent_phrases:
            if phrase in content:
                score += 5
        
        # Suspicious sender/content mismatches
        sender_domain = email.sender.split('@')[1] if '@' in email.sender else ''
        
        # Check for domain spoofing attempts
        legit_domains = ['paypal', 'amazon', 'apple', 'microsoft', 'google', 'bank']
        for domain in legit_domains:
            if domain in content and domain not in sender_domain:
                score += 10  # Claiming to be from a company but different domain
        
        return score
    
    def _check_authentication(self, email: EmailMessage) -> float:
        """Check email authentication (simplified)."""
        score = 0.0
        
        # In a real implementation, you'd check SPF, DKIM, DMARC headers
        # For demo purposes, we'll do basic checks
        
        sender_domain = email.sender.split('@')[1] if '@' in email.sender else ''
        
        # Check for suspicious sender patterns
        if re.search(r'\d{5,}', email.sender):  # Numbers in email
            score += 5
        
        if sender_domain.count('.') > 2:  # Too many subdomains
            score += 3
        
        # Check for missing subject
        if not email.subject.strip():
            score += 8
        
        return score
    
    async def _apply_spam_rules(self, email: EmailMessage, analysis: SpamAnalysis) -> float:
        """Apply custom spam rules from procedural memory."""
        
        # Get spam detection rules
        rules = await self.procedural_memory.search(
            "spam detection rule",
            filter={"must": [{"key": "metadata.type", "match": {"value": "rule"}}]},
            limit=5
        )
        
        score_adjustment = 0.0
        
        for rule in rules:
            rule_content = rule.content.lower()
            
            # Apply domain-specific rules
            if 'sender domain' in rule_content:
                sender_domain = email.sender.split('@')[1]
                if sender_domain in rule_content:
                    adjustment = rule.metadata.get('spam_score_adjustment', 0)
                    score_adjustment += adjustment
                    print(f"   📋 Applied rule: {rule.content[:50]}... ({adjustment:+.1f})")
        
        return score_adjustment
    
    def _classify_spam_score(self, analysis: SpamAnalysis) -> SpamAnalysis:
        """Classify the final spam score into confidence levels."""
        
        score = analysis.spam_score
        
        if score >= 80:
            analysis.is_spam = True
            analysis.confidence = SpamConfidence.DEFINITELY_SPAM
            analysis.recommendation = "Block immediately. High spam confidence."
        elif score >= 60:
            analysis.is_spam = True
            analysis.confidence = SpamConfidence.LIKELY_SPAM
            analysis.recommendation = "Move to spam folder. Review if needed."
        elif score >= 30:
            analysis.is_spam = False  # But suspicious
            analysis.confidence = SpamConfidence.SUSPICIOUS
            analysis.recommendation = "Flag for manual review. Potentially suspicious."
        elif score >= 15:
            analysis.is_spam = False
            analysis.confidence = SpamConfidence.UNCERTAIN
            analysis.recommendation = "Monitor sender. Slight concern."
        elif score >= 5:
            analysis.is_spam = False
            analysis.confidence = SpamConfidence.LIKELY_CLEAN
            analysis.recommendation = "Likely legitimate. Allow delivery."
        else:
            analysis.is_spam = False
            analysis.confidence = SpamConfidence.DEFINITELY_CLEAN
            analysis.recommendation = "Clean email. Safe to deliver."
        
        return analysis
    
    async def _store_spam_analysis(self, email: EmailMessage, analysis: SpamAnalysis):
        """Store spam analysis results for learning."""
        
        content = f"Spam analysis for {email.sender}: {analysis.confidence.value} (score: {analysis.spam_score:.1f})"
        
        metadata = {
            'type': 'spam_analysis',
            'sender_email': email.sender,
            'spam_score': analysis.spam_score,
            'confidence': analysis.confidence.value,
            'is_spam': analysis.is_spam,
            'spamassassin_score': analysis.spamassassin_score,
            'blacklist_hits': len(analysis.blacklist_hits),
            'content_flags': len(analysis.content_flags),
            'reasons': [reason.value for reason in analysis.reasons]
        }
        
        await self.episodic_memory.add(content, metadata)
    
    async def mark_as_spam(self, email: EmailMessage, user_feedback: str = ""):
        """User marks an email as spam for learning."""
        
        content = f"User marked as spam: {email.sender} - {email.subject}"
        if user_feedback:
            content += f" | Feedback: {user_feedback}"
        
        metadata = {
            'type': 'spam_feedback',
            'sender_email': email.sender,
            'subject': email.subject,
            'feedback': user_feedback,
            'marked_at': datetime.now(UTC).isoformat()
        }
        
        await self.episodic_memory.add(content, metadata)
        print(f"📝 Learned: {email.sender} marked as spam")
    
    async def mark_as_not_spam(self, email: EmailMessage, user_feedback: str = ""):
        """User marks an email as NOT spam for learning."""
        
        content = f"User marked as NOT spam: {email.sender} - {email.subject}"
        if user_feedback:
            content += f" | Feedback: {user_feedback}"
        
        metadata = {
            'type': 'not_spam_feedback',
            'sender_email': email.sender,
            'subject': email.subject,
            'feedback': user_feedback,
            'marked_at': datetime.now(UTC).isoformat()
        }
        
        await self.episodic_memory.add(content, metadata)
        print(f"📝 Learned: {email.sender} marked as legitimate")




async def demo_spam_detector():
    """Demonstrate the spam detection agent."""
    print("🛡️ SPAM DETECTION DEMO")
    print("=" * 50)
    
    detector = SpamDetector()
    
    # Test emails
    test_emails = [
        EmailMessage(
            "1", "john.smith@acmecorp.com", "Q4 Project Update",
            "Hi there, just wanted to update you on our Q4 project progress. Everything is on track!"
        ),
        EmailMessage(
            "2", "winner123@suspicious-domain.net", "CONGRATULATIONS!!! YOU WON $1,000,000!!!",
            "FREE MONEY!!! Click here NOW!!! Limited time offer!!! URGENT ACTION REQUIRED!!!"
        ),
        EmailMessage(
            "3", "noreply@phishing-site.com", "Your PayPal Account Suspended",
            "Your account has been suspended. Verify your identity immediately by clicking this link."
        ),
        EmailMessage(
            "4", "newsletter@techcompany.com", "Weekly Tech Updates",
            "Here are this week's top technology news and insights from our research team."
        )
    ]
    
    for email in test_emails:
        print(f"\n📧 Analyzing: {email.subject}")
        print(f"   From: {email.sender}")
        
        analysis = await detector.analyze_spam(email)
        
        print(f"   🎯 Result: {analysis.confidence.value}")
        print(f"   📊 Score: {analysis.spam_score:.1f}")
        print(f"   ⚖️ Decision: {'SPAM' if analysis.is_spam else 'CLEAN'}")
        
        if analysis.spamassassin_score is not None:
            print(f"   🔬 SpamAssassin: {analysis.spamassassin_score:.1f}")
        
        if analysis.blacklist_hits:
            print(f"   🚫 Blacklisted: {', '.join(analysis.blacklist_hits)}")
        
        if analysis.content_flags:
            print(f"   ⚠️ Content flags: {', '.join(analysis.content_flags[:3])}")
        
        if analysis.reasons:
            print(f"   📋 Reasons: {', '.join([r.value for r in analysis.reasons[:3]])}")
        
        print(f"   💡 Recommendation: {analysis.recommendation}")
    
    # Demo user feedback
    print(f"\n📝 USER FEEDBACK DEMO")
    print("=" * 30)
    
    # Mark the suspicious email as spam
    await detector.mark_as_spam(
        test_emails[1], 
        "Obviously fake lottery spam"
    )
    
    # Mark the legitimate email as not spam
    await detector.mark_as_not_spam(
        test_emails[0],
        "This is from my colleague John"
    )
    
    print("User feedback stored for learning!")


if __name__ == "__main__":
    asyncio.run(demo_spam_detector()) 
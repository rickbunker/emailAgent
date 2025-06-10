#!/usr/bin/env python3
"""
SpamAssassin Integration for Email Agent

A comprehensive interface to Apache SpamAssassin for sophisticated email spam detection
in private market asset management environments. Provides seamless integration with both
command-line and daemon modes with extensive logging and monitoring capabilities.

Features:
    - Multi-mode SpamAssassin integration (spamassassin command and spamc daemon)
    - Comprehensive spam analysis with detailed scoring and rule breakdown
    - Professional logging with detailed debugging capabilities
    - Business-context email formatting for asset management workflows
    - Production-grade error handling and timeout management
    - Configurable thresholds and analysis parameters

Business Context:
    Designed for private market asset management firms processing sensitive financial
    communications where false positives must be minimized and legitimate business
    correspondence must be preserved. Integrates with contact extraction and memory
    systems for continuous learning and adaptation.

Technical Architecture: 
    - Command-line mode: Uses spamassassin executable for comprehensive analysis
    - Daemon mode: Uses spamc client for high-performance batch processing
    - Fallback mechanisms ensure reliability across deployment environments
    - Detailed output parsing for actionable spam intelligence

Version: 1.0.0
Author: Email Agent Development Team
License: Private - Asset Management Use Only
"""

import subprocess
import re
import tempfile
import os
import asyncio
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import shutil
import datetime

# Logging system
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

# Initialize logger
logger = get_logger(__name__)

class SpamAssassinMode(Enum):
    """SpamAssassin operation modes."""
    COMMAND = "spamassassin"      # Command-line mode (comprehensive)
    DAEMON = "spamc"              # Daemon client mode (fast)
    UNAVAILABLE = "unavailable"   # SpamAssassin not available

class SpamConfidence(Enum):
    """Spam detection confidence levels for business context."""
    DEFINITELY_SPAM = "definitely_spam"      # Score >= 10.0 - Block immediately
    LIKELY_SPAM = "likely_spam"             # Score >= 5.0 - Standard spam threshold  
    SUSPICIOUS = "suspicious"               # Score >= 2.0 - Requires review
    LEGITIMATE = "legitimate"               # Score < 2.0 - Pass through
    UNKNOWN = "unknown"                     # Analysis failed

@dataclass
class SpamAnalysisResult:
    """
    Comprehensive SpamAssassin analysis result.
    
    Contains detailed scoring information, triggered rules, and business-context
    classification for informed decision-making in asset management environments.
    
    Attributes:
        score: SpamAssassin numeric score (higher = more likely spam)
        threshold: Configured spam threshold for classification
        is_spam: Boolean spam determination based on threshold
        confidence: Business confidence level for routing decisions
        details: Human-readable summary of analysis
        rules_hit: List of SpamAssassin rules that triggered
        rule_scores: Individual scores for each triggered rule
        raw_output: Complete SpamAssassin output for debugging
        processing_time: Analysis duration in seconds
        mode_used: SpamAssassin mode used for analysis
        error_message: Error details if analysis failed
        
    Business Intelligence:
        - DEFINITELY_SPAM: Block and quarantine immediately
        - LIKELY_SPAM: Standard business spam handling  
        - SUSPICIOUS: Route to human review for false positive prevention
        - LEGITIMATE: Pass through to business workflows
    """
    score: float
    threshold: float
    is_spam: bool
    confidence: SpamConfidence
    details: str
    rules_hit: List[str] = field(default_factory=list)
    rule_scores: Dict[str, float] = field(default_factory=dict)
    raw_output: str = ""
    processing_time: float = 0.0
    mode_used: SpamAssassinMode = SpamAssassinMode.UNAVAILABLE
    error_message: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate analysis result data integrity."""
        if self.score < 0 and not self.error_message:
            logger.warning(f"Negative spam score detected: {self.score}")
        
        if self.is_spam and self.score < self.threshold:
            logger.warning(f"Spam classification inconsistency: is_spam={self.is_spam}, score={self.score}, threshold={self.threshold}")

class SpamAssassinIntegration:
    """
    Professional SpamAssassin integration for email spam detection.
    
    Provides comprehensive spam analysis capabilities with business-context
    classification designed for private market asset management environments
    where false positives have significant business impact.
    
    Features:
        - Multi-mode operation (command-line and daemon)
        - Configurable thresholds and business logic
        - Comprehensive logging and monitoring
        - Production-grade error handling
        - Performance optimization for batch processing
        
    Business Context:
        Designed for financial services environments processing sensitive
        asset management communications where legitimate business emails
        must never be incorrectly classified as spam.
    """
    
    # Standard SpamAssassin configuration
    DEFAULT_THRESHOLD = 5.0
    HIGH_CONFIDENCE_THRESHOLD = 10.0
    SUSPICIOUS_THRESHOLD = 2.0
    ANALYSIS_TIMEOUT = 60  # seconds
    
    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        """
        Initialize SpamAssassin integration with comprehensive environment detection.
        
        Automatically detects available SpamAssassin modes and validates
        configuration for optimal performance in the deployment environment.
        
        Args:
            threshold: Spam classification threshold (default: 5.0)
            
        Raises:
            ValueError: If threshold is invalid
            
        Note:
            Will log warnings if SpamAssassin is unavailable but continue
            operation to allow graceful degradation in production environments.
        """
        if threshold <= 0:
            raise ValueError(f"Spam threshold must be positive, got: {threshold}")
            
        self.logger = get_logger(f"{__name__}.SpamAssassinIntegration")
        self.threshold = threshold
        self.high_threshold = max(threshold * 2, self.HIGH_CONFIDENCE_THRESHOLD)
        self.suspicious_threshold = min(threshold * 0.4, self.SUSPICIOUS_THRESHOLD)
        
        # Detection and validation
        self.available_modes = self._detect_spamassassin_modes()
        self.primary_mode = self._select_primary_mode()
        
        # Performance tracking
        self.analysis_count = 0
        self.total_processing_time = 0.0
        self.error_count = 0
        
        self.logger.info(f"SpamAssassin integration initialized - threshold: {threshold}, primary_mode: {self.primary_mode.value}")
    
    @log_function()
    def _detect_spamassassin_modes(self) -> List[SpamAssassinMode]:
        """
        Detect available SpamAssassin modes on the system.
        
        Tests both command-line and daemon client modes to determine
        optimal configuration for the deployment environment.
        
        Returns:
            List of available SpamAssassin modes
        """
        available_modes = []
        
        # Test spamassassin command (most comprehensive)
        spamassassin_path = shutil.which('spamassassin')
        if spamassassin_path:
            try:
                result = subprocess.run(
                    ['spamassassin', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    available_modes.append(SpamAssassinMode.COMMAND)
                    version_info = result.stdout.strip().split('\n')[0]
                    self.logger.info(f"SpamAssassin command mode available: {version_info}")
                else:
                    self.logger.warning(f"SpamAssassin command test failed: {result.stderr}")
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                self.logger.warning(f"SpamAssassin command detection failed: {e}")
        
        # Test spamc daemon client (fastest for batch processing)
        spamc_path = shutil.which('spamc')
        if spamc_path:
            try:
                result = subprocess.run(
                    ['spamc', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    available_modes.append(SpamAssassinMode.DAEMON)
                    self.logger.info("SpamAssassin daemon client (spamc) available")
                    self.logger.info("Note: spamc requires spamd daemon to be running")
                else:
                    self.logger.warning(f"SpamAssassin daemon client test failed: {result.stderr}")
            except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                self.logger.warning(f"SpamAssassin daemon client detection failed: {e}")
        
        if not available_modes:
            self.logger.warning("SpamAssassin not available on system")
            self.logger.info("Install SpamAssassin: 'apt-get install spamassassin' (Ubuntu) or 'brew install spamassassin' (macOS)")
            available_modes.append(SpamAssassinMode.UNAVAILABLE)
        
        return available_modes
    
    @log_function()
    def _select_primary_mode(self) -> SpamAssassinMode:
        """
        Select primary SpamAssassin mode based on availability and performance.
        
        Prefers command-line mode for comprehensive analysis, falls back to
        daemon mode for performance, or returns unavailable for graceful degradation.
        
        Returns:
            Primary SpamAssassin mode to use
        """
        if SpamAssassinMode.COMMAND in self.available_modes:
            self.logger.info("Selected SpamAssassin command mode (comprehensive analysis)")
            return SpamAssassinMode.COMMAND
        elif SpamAssassinMode.DAEMON in self.available_modes:
            self.logger.info("Selected SpamAssassin daemon mode (high performance)")
            return SpamAssassinMode.DAEMON
        else:
            self.logger.warning("SpamAssassin unavailable - spam detection disabled")
            return SpamAssassinMode.UNAVAILABLE
    
    @log_function()
    async def analyze_email(self, email_content: str, sender: str = "", subject: str = "") -> SpamAnalysisResult:
        """
        Perform comprehensive SpamAssassin analysis of email content.
        
        Analyzes email content using the best available SpamAssassin mode
        with comprehensive error handling and business-context classification.
        
        Args:
            email_content: Raw email content or formatted email message
            sender: Sender email address for enhanced analysis context
            subject: Email subject line for enhanced analysis context
            
        Returns:
            Comprehensive spam analysis result with business intelligence
            
        Raises:
            ValueError: If email_content is empty or invalid
            
        Business Logic:
            - DEFINITELY_SPAM (≥10.0): Immediate blocking recommended
            - LIKELY_SPAM (≥5.0): Standard spam threshold
            - SUSPICIOUS (≥2.0): Human review recommended (false positive prevention)
            - LEGITIMATE (<2.0): Pass through to business workflows
        """
        if not email_content or not email_content.strip():
            raise ValueError("Email content cannot be empty")
        
        start_time = asyncio.get_event_loop().time()
        
        # Format email for analysis if additional context provided
        if sender or subject:
            formatted_content = self._format_email_for_analysis(email_content, sender, subject)
        else:
            formatted_content = email_content
        
        # Perform analysis based on available mode
        if self.primary_mode == SpamAssassinMode.UNAVAILABLE:
            self.logger.warning("SpamAssassin unavailable - returning default legitimate classification")
            return self._create_unavailable_result(start_time)
        
        try:
            if self.primary_mode == SpamAssassinMode.COMMAND:
                result = await self._analyze_with_spamassassin_command(formatted_content)
            else:  # DAEMON mode
               result = await self._analyze_with_spamc_daemon(formatted_content)
            
            # Calculate processing time
            processing_time = asyncio.get_event_loop().time() - start_time
            result.processing_time = processing_time
            
            # Update statistics
            self.analysis_count += 1
            self.total_processing_time += processing_time
            
            self.logger.debug(f"SpamAssassin analysis complete - score: {result.score}, confidence: {result.confidence.value}, time: {processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            self.error_count += 1
            processing_time = asyncio.get_event_loop().time() - start_time
            
            self.logger.error(f"SpamAssassin analysis failed: {e}")
            
            return SpamAnalysisResult(
                score=0.0,
                threshold=self.threshold,
                is_spam=False,
                confidence=SpamConfidence.UNKNOWN,
                details=f"Analysis failed: {str(e)}",
                processing_time=processing_time,
                mode_used=self.primary_mode,
                error_message=str(e)
            )
    
    @log_function()
    async def _analyze_with_spamassassin_command(self, email_content: str) -> SpamAnalysisResult:
        """
        Analyze email using spamassassin command with comprehensive output parsing.
        
        Args:
            email_content: Formatted email content for analysis
            
        Returns:
            Detailed spam analysis result
            
        Raises:
            subprocess.TimeoutExpired: If analysis times out
            RuntimeError: If SpamAssassin execution fails
        """
        try:
            # Use comprehensive spamassassin flags for detailed analysis
            process = subprocess.Popen(
                ['spamassassin', '-D', '-t', '--cf', 'report_safe 0'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=email_content, timeout=self.ANALYSIS_TIMEOUT)
            
            return self._parse_spamassassin_output(stdout, stderr, process.returncode, SpamAssassinMode.COMMAND)
            
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error(f"SpamAssassin command timeout after {self.ANALYSIS_TIMEOUT} seconds")
            raise RuntimeError(f"SpamAssassin analysis timeout ({self.ANALYSIS_TIMEOUT}s)")
        except Exception as e:
            self.logger.error(f"SpamAssassin command execution failed: {e}")
            raise RuntimeError(f"SpamAssassin execution error: {e}")
    
    @log_function()
    async def _analyze_with_spamc_daemon(self, email_content: str) -> SpamAnalysisResult:
        """
        Analyze email using spamc daemon client for high-performance analysis.
        
        Args:
            email_content: Formatted email content for analysis
            
        Returns:
            Spam analysis result from daemon
            
        Raises:
            subprocess.TimeoutExpired: If analysis times out
            RuntimeError: If spamc execution fails
        """
        try:
            # Use spamc with report flag for detailed output
            process = subprocess.Popen(
                ['spamc', '-R'],  # -R flag for full report
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=email_content, timeout=self.ANALYSIS_TIMEOUT)
            
            # Check for daemon availability
            if len(stdout.strip()) < 10 or stdout.strip() == "0/0":
                self.logger.warning("spamc returned minimal output - daemon may not be running")
                # Fallback to command mode if available
                if SpamAssassinMode.COMMAND in self.available_modes:
                    self.logger.info("Falling back to SpamAssassin command mode")
                    return await self._analyze_with_spamassassin_command(email_content)
                else:
                    raise RuntimeError("SpamAssassin daemon unavailable and no command fallback")
            
            return self._parse_spamc_output(stdout, stderr, SpamAssassinMode.DAEMON)
            
        except subprocess.TimeoutExpired:
            process.kill()
            self.logger.error(f"SpamAssassin daemon timeout after {self.ANALYSIS_TIMEOUT} seconds")
            raise RuntimeError(f"SpamAssassin daemon timeout ({self.ANALYSIS_TIMEOUT}s)")
        except Exception as e:
            self.logger.error(f"SpamAssassin daemon execution failed: {e}")
            raise RuntimeError(f"SpamAssassin daemon error: {e}")
    
    @log_function()
    def _parse_spamassassin_output(self, stdout: str, stderr: str, exit_code: int, mode: SpamAssassinMode) -> SpamAnalysisResult:
        """
        Parse comprehensive spamassassin command output.
        
        Extracts detailed scoring information, triggered rules, and analysis
        metadata from SpamAssassin command output format.
        
        Args:
            stdout: SpamAssassin standard output
            stderr: SpamAssassin standard error
            exit_code: Process exit code
            mode: SpamAssassin mode used
            
        Returns:
            Parsed spam analysis result
        """
        score = 0.0
        threshold = self.threshold
        rules_hit = []
        rule_scores = {}
        details = ""
        
        lines = stdout.split('\n')
        
        # Parse X-Spam-Status header (may span multiple lines)
        spam_status_section = []
        in_spam_status = False
        
        for line in lines:
            if line.startswith('X-Spam-Status:'):
                in_spam_status = True
                spam_status_section.append(line)
            elif in_spam_status and line.startswith(' '):
                spam_status_section.append(line)
            elif in_spam_status:
                break
        
        spam_status_line = ' '.join(spam_status_section)
        
        if spam_status_line:
            # Extract score: X-Spam-Status: Yes, score=8.5 required=5.0 tests=RULE1,RULE2
            score_match = re.search(r'score=([-\d\.]+)', spam_status_line)
            threshold_match = re.search(r'required=([\d\.]+)', spam_status_line)
            tests_match = re.search(r'tests=([^\s]+)', spam_status_line)
            
            if score_match:
                score = float(score_match.group(1))
            if threshold_match:
                threshold = float(threshold_match.group(1))
            if tests_match and tests_match.group(1) != 'none':
                rules_hit = [rule.strip() for rule in tests_match.group(1).split(',') if rule.strip()]
            
            details = spam_status_line.replace('X-Spam-Status:', '').strip()
        
        # Extract individual rule scores from X-Spam-Report if available
        for line in lines:
            if line.startswith('X-Spam-Report:') or (line.startswith(' ') and 'pts rule name' in line):
                # Parse rule breakdown: * 1.5 RULE_NAME Description
                rule_matches = re.findall(r'\*\s+([-\d\.]+)\s+([A-Z_][A-Z0-9_]*)', line)
                for rule_score_str, rule_name in rule_matches:
                    rule_scores[rule_name] = float(rule_score_str)
        
        # Determine business confidence level
        confidence = self._calculate_confidence_level(score)
        is_spam = score >= threshold
        
        return SpamAnalysisResult(
            score=score,
            threshold=threshold,
            is_spam=is_spam,
            confidence=confidence,
            details=details,
            rules_hit=rules_hit,
            rule_scores=rule_scores,
            raw_output=stdout,
            mode_used=mode
        )
    
    @log_function()
    def _parse_spamc_output(self, stdout: str, stderr: str, mode: SpamAssassinMode) -> SpamAnalysisResult:
        """
        Parse spamc daemon client output format.
        
        Extracts spam analysis information from spamc client output
        which includes modified email headers with spam assessment.
        
        Args:
            stdout: spamc standard output  
            stderr: spamc standard error
            mode: SpamAssassin mode used
            
        Returns:
            Parsed spam analysis result
        """
        score = 0.0
        threshold = self.threshold
        rules_hit = []
        rule_scores = {}
        details = ""
        
        lines = stdout.split('\n')
        
        for line in lines:
            if line.startswith('X-Spam-Status:'):
                # Parse: X-Spam-Status: No, score=-0.1 required=5.0 tests=DKIM_SIGNED,DKIM_VALID
                score_match = re.search(r'score=([-\d\.]+)', line)
                threshold_match = re.search(r'required=([\d\.]+)', line)
                tests_match = re.search(r'tests=([^\s]+)', line)
                
                if score_match:
                    score = float(score_match.group(1))
                if threshold_match:
                    threshold = float(threshold_match.group(1))
                if tests_match and tests_match.group(1) != 'none':
                    rules_hit = [rule.strip() for rule in tests_match.group(1).split(',') if rule.strip()]
                
                details = line.replace('X-Spam-Status:', '').strip()
                break
        
        # Look for X-Spam-Report for detailed rule scores
        in_report = False
        for line in lines:
            if line.startswith('X-Spam-Report:'):
                in_report = True
                continue
            elif in_report and line.startswith(' '):
                # Parse rule breakdown in report
                rule_matches = re.findall(r'\*\s+([-\d\.]+)\s+([A-Z_][A-Z0-9_]*)', line)
                for rule_score_str, rule_name in rule_matches:
                    rule_scores[rule_name] = float(rule_score_str)
            elif in_report and not line.startswith(' '):
                break
        
        # Determine business confidence level
        confidence = self._calculate_confidence_level(score)
        is_spam = score >= threshold
        
        return SpamAnalysisResult(
            score=score,
            threshold=threshold,
            is_spam=is_spam,
            confidence=confidence,
            details=details,
            rules_hit=rules_hit,
            rule_scores=rule_scores,
            raw_output=stdout,
            mode_used=mode
        )
    
    @log_function()
    def _calculate_confidence_level(self, score: float) -> SpamConfidence:
        """
        Calculate business confidence level based on SpamAssassin score.
        
        Maps numeric spam scores to business-context confidence levels
        for informed routing decisions in asset management environments.
        
        Args:
            score: SpamAssassin numeric score
            
        Returns:
            Business confidence level for routing decisions
            
        Business Logic:
            - DEFINITELY_SPAM: Score ≥ high_threshold (typically 10.0)
            - LIKELY_SPAM: Score ≥ threshold (typically 5.0)  
            - SUSPICIOUS: Score ≥ suspicious_threshold (typically 2.0)
            - LEGITIMATE: Score < suspicious_threshold
        """
        if score >= self.high_threshold:
            return SpamConfidence.DEFINITELY_SPAM
        elif score >= self.threshold:
            return SpamConfidence.LIKELY_SPAM
        elif score >= self.suspicious_threshold:
            return SpamConfidence.SUSPICIOUS
        else:
            return SpamConfidence.LEGITIMATE
    
    @log_function()
    def _format_email_for_analysis(self, content: str, sender: str = "", subject: str = "") -> str:
        """
        Format email content for optimal SpamAssassin analysis.
        
        Creates properly formatted email message with headers that enable
        SpamAssassin to perform comprehensive analysis including sender
        reputation, subject analysis, and content inspection.
        
        Args:
            content: Raw email content or body
            sender: Sender email address
            subject: Email subject line
            
        Returns:
            Properly formatted email message for SpamAssassin
        """
        # If content already contains headers, use as-is
        if content.startswith(('From:', 'To:', 'Subject:', 'Date:', 'Return-Path:')):
            self.logger.debug("Email content already contains headers")
            return content
        
        # Build minimal headers for analysis
        headers = []
        
        if sender:
            headers.append(f"From: {sender}")
            headers.append(f"Return-Path: <{sender}>")
        
        if subject:
            headers.append(f"Subject: {subject}")
        
        # Add standard headers for better analysis
        headers.extend([
            "Date: " + str(datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')),
            "Message-ID: <spamassassin-analysis@emailagent.local>",
            "MIME-Version: 1.0",
            "Content-Type: text/plain; charset=utf-8",
            ""  # Empty line to separate headers from body
        ])
        
        formatted_email = '\n'.join(headers) + '\n' + content
        
        self.logger.debug(f"Formatted email for analysis - headers: {len(headers)-1}, body_length: {len(content)}")
        
        return formatted_email
    
    @log_function()
    def _create_unavailable_result(self, start_time: float) -> SpamAnalysisResult:
        """
        Create default result when SpamAssassin is unavailable.
        
        Provides graceful degradation with legitimate classification
        to prevent false positives in production environments.
        
        Args:
            start_time: Analysis start time for duration calculation
            
        Returns:
            Default legitimate classification result
        """
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return SpamAnalysisResult(
            score=0.0,
            threshold=self.threshold,
            is_spam=False,
            confidence=SpamConfidence.LEGITIMATE,
            details="SpamAssassin unavailable - default legitimate classification",
            processing_time=processing_time,
            mode_used=SpamAssassinMode.UNAVAILABLE,
            error_message="SpamAssassin not available on system"
        )
    
    @log_function()
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance and analysis statistics.
        
        Provides operational metrics for monitoring SpamAssassin
        integration performance and reliability in production.
        
        Returns:
            Dictionary containing performance metrics and statistics
        """
        avg_processing_time = (
            self.total_processing_time / self.analysis_count 
            if self.analysis_count > 0 else 0.0
        )
        
        error_rate = (
            self.error_count / self.analysis_count * 100 
            if self.analysis_count > 0 else 0.0
        )
        
        return {
            'total_analyses': self.analysis_count,
            'total_processing_time': round(self.total_processing_time, 3),
            'average_processing_time': round(avg_processing_time, 3),
            'error_count': self.error_count,
            'error_rate_percent': round(error_rate, 2),
            'primary_mode': self.primary_mode.value,
            'available_modes': [mode.value for mode in self.available_modes],
            'thresholds': {
                'spam_threshold': self.threshold,
                'high_confidence_threshold': self.high_threshold,
                'suspicious_threshold': self.suspicious_threshold
            }
        }
    
    @log_function()
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of SpamAssassin integration.
        
        Tests SpamAssassin availability and basic functionality to ensure
        reliable operation in production environments.
        
        Returns:
            Health check results with detailed status information
            
        Note:
            Uses a minimal test email to validate end-to-end functionality
            without triggering spam detection systems.
        """
        health_status = {
            'available': self.primary_mode != SpamAssassinMode.UNAVAILABLE,
            'primary_mode': self.primary_mode.value,
            'available_modes': [mode.value for mode in self.available_modes],
            'configuration_valid': True,
            'test_analysis_successful': False,
            'error_message': None
        }
        
        if self.primary_mode == SpamAssassinMode.UNAVAILABLE:
            health_status['error_message'] = "SpamAssassin not available on system"
            return health_status
        
        # Test with minimal legitimate email
        test_email = """From: test@example.com
Subject: Test Message
Date: """ + str(datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')) + """

This is a test message for SpamAssassin health check.
"""
        
        try:
            result = await self.analyze_email(test_email)
            if result.error_message is None:
                health_status['test_analysis_successful'] = True
            else:
                health_status['error_message'] = result.error_message
                
        except Exception as e:
            health_status['error_message'] = f"Health check failed: {str(e)}"
        
        return health_status

# Convenience function for simple spam checking
@log_function()
async def check_email_spam(sender: str, subject: str, content: str, 
                          threshold: float = 5.0) -> Optional[SpamAnalysisResult]:
    """
    Convenience function for quick email spam analysis.
    
    Provides simplified interface for one-off spam checking without
    maintaining a persistent SpamAssassinIntegration instance.
    
    Args:
        sender: Sender email address
        subject: Email subject line  
        content: Email body content
        threshold: Spam classification threshold
        
    Returns:
        Spam analysis result or None if SpamAssassin unavailable
        
    Example:
        >>> result = await check_email_spam(
        ...     sender="user@example.com",
        ...     subject="Important Business Update", 
        ...     content="Quarterly financial results..."
        ... )
        >>> if result and result.confidence == SpamConfidence.LEGITIMATE:
        ...     print("Email is legitimate business communication")
    """
    logger.info(f"Quick spam check for email from {sender}")
    
    integration = SpamAssassinIntegration(threshold=threshold)
    
    if integration.primary_mode == SpamAssassinMode.UNAVAILABLE:
        logger.warning("SpamAssassin unavailable for quick spam check")
        return None
    
    try:
        result = await integration.analyze_email(content, sender, subject)
        logger.info(f"Quick spam check complete - score: {result.score}, confidence: {result.confidence.value}")
        return result
    except Exception as e:
        logger.error(f"Quick spam check failed: {e}")
        return None 
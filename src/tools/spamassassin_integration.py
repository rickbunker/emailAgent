#!/usr/bin/env python3
"""
SpamAssassin integration for the email agent.

This module provides a clean interface to SpamAssassin for spam detection,
handling the complexity of running SpamAssassin and parsing its output.
"""

import subprocess
import re
import tempfile
import os
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SpamAssassinResult:
    """Result from SpamAssassin analysis."""
    score: float
    threshold: float
    is_spam: bool
    details: str
    rules_hit: list
    raw_output: str

class SpamAssassinIntegration:
    """Handles SpamAssassin integration for spam detection."""
    
    def __init__(self, threshold: float = 5.0):
        """
        Initialize SpamAssassin integration.
        
        Args:
            threshold: Spam threshold score (default 5.0)
        """
        self.threshold = threshold
        self.available = self._check_availability()
        
    def _check_availability(self) -> bool:
        """Check if SpamAssassin is available on the system."""
        # Try spamassassin command first (doesn't need daemon)
        try:
            result = subprocess.run(
                ['spamassassin', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[INFO] SpamAssassin (spamassassin) available")
                self.mode = 'spamassassin'
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        # Try spamc only as fallback (requires daemon)
        try:
            result = subprocess.run(
                ['spamc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[INFO] SpamAssassin (spamc) available - note: requires spamd daemon")
                self.mode = 'spamc'
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
            
        print("[WARN] SpamAssassin not available on system")
        self.mode = None
        return False
    
    def check_spam(self, email_content: str) -> Optional[SpamAssassinResult]:
        """
        Check if email content is spam using SpamAssassin.
        
        Args:
            email_content: Raw email content to analyze
            
        Returns:
            SpamAssassinResult or None if SpamAssassin unavailable
        """
        if not self.available:
            return None
            
        try:
            if self.mode == 'spamc':
                return self._check_with_spamc(email_content)
            elif self.mode == 'spamassassin':
                return self._check_with_spamassassin(email_content)
        except Exception as e:
            print(f"[ERROR] SpamAssassin check failed: {e}")
            return None
    
    def _check_with_spamc(self, email_content: str) -> Optional[SpamAssassinResult]:
        """Check spam using spamc (faster client-server mode)."""
        try:
            # Try with -R flag for full report
            process = subprocess.Popen(
                ['spamc', '-R'],  # -R flag for full report
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=email_content, timeout=30)
            
            # If spamc fails (like "0/0" output), fall back to spamassassin command
            if len(stdout.strip()) < 10 or stdout.strip() == "0/0":
                print("[DEBUG] spamc returned minimal output, falling back to spamassassin command")
                return self._check_with_spamassassin(email_content)
            
            return self._parse_spamc_output(stdout, stderr)
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("[WARN] SpamAssassin spamc timeout")
            return None
        except Exception as e:
            print(f"[ERROR] spamc error: {e}")
            return None
    
    def _check_with_spamassassin(self, email_content: str) -> Optional[SpamAssassinResult]:
        """Check spam using spamassassin command with proper configuration."""
        try:
            # Use -D for debug output which gives us detailed scoring
            # -t for adding headers
            process = subprocess.Popen(
                ['spamassassin', '-D', '-t'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=email_content, timeout=60)
            
            return self._parse_spamassassin_output(stdout, stderr, process.returncode)
            
        except subprocess.TimeoutExpired:
            process.kill()
            print("[WARN] SpamAssassin command timeout")
            return None
        except Exception as e:
            print(f"[ERROR] spamassassin command error: {e}")
            return None
    
    def _parse_spamc_output(self, stdout: str, stderr: str) -> Optional[SpamAssassinResult]:
        """Parse spamc output format."""
        # spamc with -c returns headers with spam info
        lines = stdout.split('\n')
        
        score = 0.0
        threshold = self.threshold
        details = ""
        rules_hit = []
        
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
                if tests_match:
                    rules_hit = tests_match.group(1).split(',')
                    
                details = line
                break
        
        is_spam = score >= threshold
        
        return SpamAssassinResult(
            score=score,
            threshold=threshold,
            is_spam=is_spam,
            details=details,
            rules_hit=rules_hit,
            raw_output=stdout
        )
    
    def _parse_spamassassin_output(self, stdout: str, stderr: str, exit_code: int) -> Optional[SpamAssassinResult]:
        """Parse spamassassin command output format."""
        score = 0.0
        threshold = 5.0  # Default SpamAssassin threshold
        details = ""
        rules_hit = []
        
        lines = stdout.split('\n')
        
        # Look for X-Spam-Status header (may span multiple lines)
        spam_status_lines = []
        in_spam_status = False
        
        for line in lines:
            if line.startswith('X-Spam-Status:'):
                in_spam_status = True
                spam_status_lines.append(line)
            elif in_spam_status and line.startswith('\t'):
                # Continuation line (starts with tab)
                spam_status_lines.append(line.strip())
            elif in_spam_status and line.strip() and not line.startswith('X-'):
                # Another type of continuation
                spam_status_lines.append(line.strip())
            elif in_spam_status and line.startswith('X-'):
                # New header, end of X-Spam-Status
                break
            elif in_spam_status and not line.strip():
                # Empty line might end the header
                break
        
        if spam_status_lines:
            # Join all the X-Spam-Status lines
            full_status = ' '.join(spam_status_lines)
            
            # Parse score
            score_match = re.search(r'score=([-\d\.]+)', full_status)
            if score_match:
                score = float(score_match.group(1))
            
            # Parse threshold
            threshold_match = re.search(r'required=([\d\.]+)', full_status)
            if threshold_match:
                threshold = float(threshold_match.group(1))
            
            # Parse tests/rules - look for tests= followed by rule names
            tests_match = re.search(r'tests=([^$]+)', full_status)
            if tests_match:
                tests_str = tests_match.group(1).strip()
                # Split on commas and clean up whitespace
                rules_hit = [rule.strip() for rule in tests_str.split(',') if rule.strip()]
            
            details = full_status
        
        # If no X-Spam-Status found, look for other indicators
        if score == 0.0:
            for line in lines:
                if line.startswith('X-Spam-Level:'):
                    # Count asterisks to get approximate score
                    asterisks = line.count('*')
                    if asterisks > 0:
                        score = float(asterisks)
                        details = line
        
        # Build details string
        if not details:
            if rules_hit:
                details = f"Rules: {', '.join(rules_hit[:5])}"
            else:
                details = f"Score: {score}, Threshold: {threshold}"
        
        is_spam = score >= threshold
        
        return SpamAssassinResult(
            score=score,
            threshold=threshold,
            is_spam=is_spam,
            details=details,
            rules_hit=rules_hit,
            raw_output=stdout
        )
    
    def format_email_for_analysis(self, sender: str, subject: str, content: str, 
                                message_id: str = None) -> str:
        """
        Format email content for SpamAssassin analysis.
        
        Args:
            sender: Email sender address
            subject: Email subject line
            content: Email body content
            message_id: Optional message ID
            
        Returns:
            Properly formatted email for SpamAssassin
        """
        import datetime
        
        if not message_id:
            message_id = f"<emailagent-{hash(content)%100000}@localhost>"
            
        formatted_email = f"""From: {sender}
Subject: {subject}
Date: {datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}
Message-ID: {message_id}
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

{content}
"""
        return formatted_email

# Convenience function for easy usage
def check_email_spam(sender: str, subject: str, content: str, 
                    threshold: float = 5.0) -> Optional[SpamAssassinResult]:
    """
    Convenience function to check if an email is spam.
    
    Args:
        sender: Email sender address
        subject: Email subject line  
        content: Email body content
        threshold: Spam threshold score
        
    Returns:
        SpamAssassinResult or None if unavailable
    """
    integration = SpamAssassinIntegration(threshold=threshold)
    if not integration.available:
        return None
        
    formatted_email = integration.format_email_for_analysis(sender, subject, content)
    return integration.check_spam(formatted_email) 
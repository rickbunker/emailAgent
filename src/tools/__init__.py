"""
Tools package for the email agent.

This package contains utilities and integrations for email processing.
"""

from .spamassassin_integration import SpamAssassinIntegration, check_email_spam

__all__ = ['SpamAssassinIntegration', 'check_email_spam'] 
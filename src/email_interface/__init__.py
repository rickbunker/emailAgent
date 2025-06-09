"""
Email integration package for the email agent.

This package provides interfaces and implementations for connecting to
various email systems like Gmail, Microsoft 365, IMAP servers, etc.
"""

from .base import (
    BaseEmailInterface,
    Email,
    EmailAddress,
    EmailAttachment,
    EmailSearchCriteria,
    EmailSendRequest,
    EmailImportance,
    EmailSystemError,
    AuthenticationError,
    ConnectionError,
    PermissionError,
    EmailNotFoundError
)

# Import implementations
from .gmail import GmailInterface
from .msgraph import MicrosoftGraphInterface
from .factory import EmailInterfaceFactory, EmailSystemType

__all__ = [
    'BaseEmailInterface',
    'Email',
    'EmailAddress', 
    'EmailAttachment',
    'EmailSearchCriteria',
    'EmailSendRequest',
    'EmailImportance',
    'EmailSystemError',
    'AuthenticationError',
    'ConnectionError',
    'PermissionError',
    'EmailNotFoundError',
    'GmailInterface',
    'MicrosoftGraphInterface',
    'EmailInterfaceFactory',
    'EmailSystemType'
] 
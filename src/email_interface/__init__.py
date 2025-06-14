"""
Email Integration Package for EmailAgent

Complete email system integration package for private market asset management
environments. Provides unified interfaces, implementations, and factory patterns
for connecting to various enterprise email systems with consistent APIs.

Features:
    - Unified email interface abstractions
    - Multiple email system implementations (Gmail, Microsoft Graph)
    - Factory pattern for dynamic email system instantiation
    - Complete data models for emails, attachments, and search
    - error handling with business-context exceptions
    - Type-safe email operations with validation

Business Context:
    Designed for asset management firms requiring email integration
    across diverse organizational infrastructures including Google Workspace,
    Microsoft 365, and legacy exchange systems. Maintains consistent
    operational patterns while supporting multi-tenant deployments.

Technical Architecture:
    - Abstract base interface with async operations
    - Concrete implementations for major email providers
    - Factory pattern with configuration-driven instantiation
    - Complete data models with validation
    - exception hierarchy for error handling

Supported Email Systems:
    - Gmail: Google Workspace integration via Gmail API
    - Microsoft Graph: Office 365/Exchange Online via Graph API
    - Outlook: Alias for Microsoft Graph (legacy compatibility)
    - Office365: Alias for Microsoft Graph (common naming)

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
# Core logging system
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function

# Initialize package logger
logger = get_logger(__name__)

# Core base classes and data models
from .base import (  # Exception hierarchy
    AuthenticationError,
    BaseEmailInterface,
    ConnectionError,
    Email,
    EmailAddress,
    EmailAttachment,
    EmailImportance,
    EmailNotFoundError,
    EmailSearchCriteria,
    EmailSendRequest,
    EmailSystemError,
    PermissionError,
)

# Factory and utility classes
from .factory import EmailInterfaceFactory, EmailSystemType

# Email system implementations
from .gmail import GmailInterface
from .msgraph import MicrosoftGraphInterface

# Package metadata
__version__ = "1.0.0"
__author__ = "Email Agent Development Team"
__license__ = "for Inveniam use only"

# Public API exports
__all__ = [
    # Core interfaces and data models
    "BaseEmailInterface",
    "Email",
    "EmailAddress",
    "EmailAttachment",
    "EmailSearchCriteria",
    "EmailSendRequest",
    "EmailImportance",
    # Exception hierarchy
    "EmailSystemError",
    "AuthenticationError",
    "ConnectionError",
    "PermissionError",
    "EmailNotFoundError",
    # Email system implementations
    "GmailInterface",
    "MicrosoftGraphInterface",
    # Factory and configuration
    "EmailInterfaceFactory",
    "EmailSystemType",
    # Package metadata
    "__version__",
    "__author__",
    "__license__",
]

# Package initialization logging
logger.info(f"Email integration package initialized - Version {__version__}")
logger.debug("Available email interfaces: Gmail, Microsoft Graph")
logger.debug(f"Supported system types: {[t.value for t in EmailSystemType]}")


# Package-level convenience functions
@log_function()
def create_email_interface(system_type: str, **kwargs) -> BaseEmailInterface:
    """
    Convenience function to create email interface instances.

    Provides package-level access to the factory pattern for creating
    email interfaces with simplified parameter handling.

    Args:
        system_type: Email system identifier ('gmail', 'microsoft_graph', etc.)
        **kwargs: System-specific configuration parameters

    Returns:
        Configured email interface instance

    Raises:
        EmailSystemError: If system type unsupported or creation fails

    Example:
        >>> from email_interface import create_email_interface
        >>> gmail = create_email_interface('gmail', credentials_file='creds.json')
        >>> msgraph = create_email_interface('microsoft_graph', client_id='...')
    """
    logger.info(f"Creating email interface via convenience function: {system_type}")
    return EmailInterfaceFactory.create(system_type, **kwargs)


@log_function()
def get_supported_systems() -> list:
    """
    Get list of supported email systems.

    Returns:
        List of supported email system type strings

    Example:
        >>> from email_interface import get_supported_systems
        >>> systems = get_supported_systems()
        >>> print(systems)
        ['gmail', 'microsoft_graph', 'outlook', 'office365']
    """
    return EmailInterfaceFactory.get_supported_types()


@log_function()
def validate_system_config(system_type: str, config: dict) -> dict:
    """
    Validate email system configuration.

    Args:
        system_type: Email system identifier
        config: Configuration dictionary to validate

    Returns:
        Validation result dictionary with status, errors, and warnings

    Example:
        >>> from email_interface import validate_system_config
        >>> result = validate_system_config('gmail', {'credentials_file': 'test.json'})
        >>> print(result['status'])
        'valid'
    """
    logger.info(f"Validating system configuration for: {system_type}")
    return EmailInterfaceFactory.validate_credentials(system_type, config)

"""
Base Email Interface for Document Management

This module provides the abstract interface that all email system integrations
must implement, enabling the email agent to work seamlessly with different email
systems (Gmail, Microsoft Graph, IMAP, Exchange, etc.) through a unified interface.

Features:
    - Unified email data models with complete metadata
    - Async/await patterns for optimal performance
    - Type-safe interfaces with full type hint coverage
    - Complete logging for debugging and monitoring
    - Extensible attachment handling with lazy loading
    - Rich search capabilities with flexible criteria
    - Error handling with specific exception types
    - Authentication management with credential abstraction

Architecture:
    The base interface defines core email operations:
    - Connection management and authentication
    - Email listing, retrieval, and search operations
    - Email composition and sending capabilities
    - Mailbox management (labels, folders, flags)
    - Attachment handling with content streaming
    
Email Data Models:
    - EmailAddress: Structured email address with display name
    - EmailAttachment: Attachment metadata with lazy content loading
    - Email: Complete email message with rich metadata
    - EmailSearchCriteria: Flexible search and filtering options
    - EmailSendRequest: Complete email composition structure

Implementation Requirements:
    All email system implementations must inherit from BaseEmailInterface
    and implement all abstract methods with proper error handling and logging.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# Logging system integration
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function, log_debug, log_info

# Initialize logger
logger = get_logger(__name__)


@dataclass
class EmailAddress:
    """
    Represents an email address with optional display name.
    
    Provides a structured representation of email addresses that handles
    both simple addresses and those with display names, commonly used
    in email headers and recipient lists.
    
    Attributes:
        address: The actual email address (e.g., 'user@example.com')
        name: Optional display name (e.g., 'John Doe')
    """
    address: str
    name: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate email address format after initialization."""
        if not self.address or '@' not in self.address:
            raise ValueError(f"Invalid email address: {self.address}")
    
    def __str__(self) -> str:
        """
        Format email address for display.
        
        Returns:
            Formatted string like 'John Doe <user@example.com>' or 'user@example.com'
        """
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


@dataclass
class EmailAttachment:
    """
    Represents an email attachment with metadata and lazy content loading.
    
    Supports efficient attachment handling by loading content only when needed,
    reducing memory usage for large attachments or when processing many emails.
    
    Attributes:
        filename: Original filename of the attachment
        content_type: MIME content type (e.g., 'application/pdf')
        size: Size in bytes
        attachment_id: Email system-specific attachment identifier
        content: Actual file content (loaded on demand)
    """
    filename: str
    content_type: str
    size: int
    attachment_id: Optional[str] = None
    content: Optional[bytes] = None
    
    def __post_init__(self) -> None:
        """Validate attachment metadata after initialization."""
        if not self.filename:
            raise ValueError("Attachment filename cannot be empty")
        if self.size < 0:
            raise ValueError("Attachment size cannot be negative")
    
    @property
    def is_loaded(self) -> bool:
        """Check if attachment content has been loaded."""
        return self.content is not None
    
    @property
    def file_extension(self) -> str:
        """Get file extension from filename."""
        return Path(self.filename).suffix.lower()


class EmailImportance(Enum):
    """
    Email importance levels following standard email conventions.
    
    Maps to common email client importance/priority settings and
    can be used for filtering and routing decisions.
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class Email:
    """
    Represents a complete email message with complete metadata.
    
    Provides a unified data structure that captures all relevant email
    information across different email systems, enabling consistent
    processing regardless of the underlying email provider.
    
    Attributes:
        id: Unique email identifier within the email system
        thread_id: Thread/conversation identifier (if supported)
        subject: Email subject line
        sender: Email address of the sender
        recipients: List of primary recipients (To field)
        cc: List of carbon copy recipients
        bcc: List of blind carbon copy recipients
        body_text: Plain text body content
        body_html: HTML body content
        attachments: List of email attachments
        importance: Email importance/priority level
        is_read: Whether the email has been read
        is_flagged: Whether the email is flagged/starred
        sent_date: When the email was sent
        received_date: When the email was received
        headers: Complete email headers dictionary
        labels: List of labels/folders (Gmail labels or folder names)
        message_id: RFC message ID for threading
        in_reply_to: Message ID this email replies to
        raw_data: Original API response for debugging/use
    """
    id: str
    thread_id: Optional[str]
    subject: str
    sender: EmailAddress
    recipients: List[EmailAddress] = field(default_factory=list)
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    importance: EmailImportance = EmailImportance.NORMAL
    is_read: bool = False
    is_flagged: bool = False
    sent_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    headers: Dict[str, str] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Validate email data after initialization."""
        if not self.id:
            raise ValueError("Email ID cannot be empty")
        if not self.subject:
            logger.warning(f"Email {self.id} has empty subject")
    
    @property
    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return len(self.attachments) > 0
    
    @property
    def total_attachment_size(self) -> int:
        """Calculate total size of all attachments in bytes."""
        return sum(att.size for att in self.attachments)
    
    @property
    def body_content(self) -> str:
        """Get the best available body content (HTML preferred, then text)."""
        return self.body_html or self.body_text or ""


@dataclass
class EmailSearchCriteria:
    """
    Flexible criteria for searching and filtering emails.
    
    Provides a complete set of search parameters that can be used
    across different email systems to find specific emails based on
    content, metadata, dates, and other attributes.
    
    Attributes:
        query: Free text search query
        sender: Filter by sender email address
        recipient: Filter by recipient email address
        subject: Filter by subject line content
        has_attachments: Filter by attachment presence
        is_unread: Filter by read status
        is_flagged: Filter by flag/star status
        date_after: Filter emails after this date
        date_before: Filter emails before this date
        labels: Filter by labels/folders
        max_results: Maximum number of results to return
    """
    query: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None
    subject: Optional[str] = None
    has_attachments: Optional[bool] = None
    is_unread: Optional[bool] = None
    is_flagged: Optional[bool] = None
    date_after: Optional[datetime] = None
    date_before: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    max_results: int = 50
    
    def __post_init__(self) -> None:
        """Validate search criteria after initialization."""
        if self.max_results <= 0:
            raise ValueError("max_results must be positive")
        if self.date_after and self.date_before and self.date_after > self.date_before:
            raise ValueError("date_after cannot be later than date_before")


@dataclass
class EmailSendRequest:
    """
    Request structure for sending emails with complete options.
    
    Encapsulates all information needed to compose and send an email,
    including recipients, content, attachments, and metadata.
    
    Attributes:
        to: List of primary recipients
        subject: Email subject line
        body_text: Plain text body content
        body_html: HTML body content
        cc: List of carbon copy recipients
        bcc: List of blind carbon copy recipients
        attachments: List of attachments to include
        importance: Email importance/priority level
        reply_to_message_id: ID of message being replied to
        thread_id: Thread/conversation ID for threading
    """
    to: List[EmailAddress]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)
    attachments: List[EmailAttachment] = field(default_factory=list)
    importance: EmailImportance = EmailImportance.NORMAL
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate email send request after initialization."""
        if not self.to:
            raise ValueError("Email must have at least one recipient")
        if not self.subject:
            logger.warning("Email has empty subject")
        if not self.body_text and not self.body_html:
            raise ValueError("Email must have either text or HTML body content")


# Exception hierarchy for email system errors
class EmailSystemError(Exception):
    """
    Base exception for email system errors.
    
    All email system-specific exceptions inherit from this base class,
    allowing for complete error handling across different email providers.
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class AuthenticationError(EmailSystemError):
    """
    Raised when authentication fails.
    
    Indicates invalid credentials, expired tokens, or insufficient
    permissions for the requested email system operation.
    """
    pass


class ConnectionError(EmailSystemError):
    """
    Raised when connection to email system fails.
    
    Indicates network issues, service unavailability, or configuration
    problems preventing communication with the email system.
    """
    pass


class PermissionError(EmailSystemError):
    """
    Raised when operation requires permissions not granted.
    
    Indicates the authenticated user lacks sufficient permissions
    to perform the requested operation on the email system.
    """
    pass


class EmailNotFoundError(EmailSystemError):
    """
    Raised when requested email is not found.
    
    Indicates the specified email ID does not exist or is not
    accessible to the authenticated user.
    """
    pass


class QuotaExceededError(EmailSystemError):
    """
    Raised when email system quota is exceeded.
    
    Indicates rate limiting, storage limits, or other quota
    restrictions have been reached.
    """
    pass


class BaseEmailInterface(ABC):
    """
    Abstract base class for email system integrations.
    
    Defines the standard interface that all email system implementations
    (Gmail, Microsoft Graph, IMAP, Exchange, etc.) must implement to
    ensure consistent behavior across different email providers.
    
    All methods are async to support high-performance email processing
    and include complete logging for debugging and monitoring.
    
    Attributes:
        is_connected: Boolean indicating connection status
        user_email: Email address of the authenticated user
        display_name: Display name of the authenticated user
    """
    
    def __init__(self) -> None:
        """Initialize the email interface."""
        self.is_connected: bool = False
        self.user_email: Optional[str] = None
        self.display_name: Optional[str] = None
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Initializing email interface")
    
    @abstractmethod
    @log_function()
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to the email system using provided credentials.
        
        Establishes an authenticated connection to the email system and
        initializes the interface for email operations.
        
        Args:
            credentials: Authentication credentials (format varies by implementation)
                        Common keys include: client_id, client_secret, refresh_token,
                        access_token, username, password, server, port
            
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            AuthenticationError: If credentials are invalid or expired
            ConnectionError: If unable to connect to email system
            ValueError: If credentials format is invalid
        """
        pass
    
    @abstractmethod
    @log_function()
    async def disconnect(self) -> None:
        """
        Disconnect from the email system.
        
        Cleanly closes the connection and clears any cached authentication
        tokens or session data.
        """
        pass
    
    @abstractmethod
    @log_function()
    async def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information.
        
        Retrieves detailed information about the authenticated user,
        including email address, display name, and system-specific metadata.
        
        Returns:
            Dictionary containing profile information with keys:
            - email: User's email address
            - name: User's display name
            - id: System-specific user ID
            - Additional provider-specific fields
            
        Raises:
            ConnectionError: If not connected to email system
            PermissionError: If insufficient permissions to access profile
        """
        pass
    
    @abstractmethod
    @log_function()
    async def list_emails(self, criteria: EmailSearchCriteria) -> List[Email]:
        """
        List emails matching the given criteria.
        
        Searches the user's mailbox for emails matching the specified
        criteria and returns a list of Email objects with metadata.
        
        Args:
            criteria: Search criteria for filtering emails
            
        Returns:
            List of Email objects matching criteria (may be empty)
            
        Raises:
            PermissionError: If insufficient permissions to access emails
            ConnectionError: If not connected to email system
            ValueError: If search criteria are invalid
        """
        pass
    
    @abstractmethod
    @log_function()
    async def get_email(self, email_id: str, include_attachments: bool = False) -> Email:
        """
        Get a specific email by ID.
        
        Retrieves a complete Email object for the specified ID, optionally
        including attachment content for immediate processing.
        
        Args:
            email_id: Unique identifier of the email
            include_attachments: Whether to load attachment content immediately
            
        Returns:
            Complete Email object with metadata and content
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to access email
            ConnectionError: If not connected to email system
        """
        pass
    
    @abstractmethod
    @log_function()
    async def send_email(self, request: EmailSendRequest) -> str:
        """
        Send an email.
        
        Composes and sends an email according to the provided request,
        handling recipients, content, attachments, and metadata.
        
        Args:
            request: Email send request with recipients, content, etc.
            
        Returns:
            Message ID of the sent email
            
        Raises:
            PermissionError: If insufficient permissions to send email
            ConnectionError: If not connected to email system
            ValueError: If send request is invalid
            QuotaExceededError: If sending quota exceeded
        """
        pass
    
    @abstractmethod
    @log_function()
    async def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.
        
        Updates the read status of the specified email to indicate
        it has been viewed by the user.
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            True if operation successful, False otherwise
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to modify email
        """
        pass
    
    @abstractmethod
    @log_function()
    async def mark_as_unread(self, email_id: str) -> bool:
        """
        Mark an email as unread.
        
        Updates the read status of the specified email to indicate
        it has not been viewed by the user.
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            True if operation successful, False otherwise
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to modify email
        """
        pass
    
    @abstractmethod
    @log_function()
    async def delete_email(self, email_id: str) -> bool:
        """
        Delete an email.
        
        Permanently removes the specified email from the mailbox.
        Some implementations may move to trash instead of permanent deletion.
        
        Args:
            email_id: Unique identifier of the email
            
        Returns:
            True if operation successful, False otherwise
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to delete email
        """
        pass
    
    @abstractmethod
    @log_function()
    async def get_labels(self) -> List[str]:
        """
        Get available labels/folders.
        
        Retrieves a list of all available labels (Gmail) or folders
        (other systems) that can be used for email organization.
        
        Returns:
            List of label/folder names
            
        Raises:
            PermissionError: If insufficient permissions to access labels
            ConnectionError: If not connected to email system
        """
        pass
    
    @abstractmethod
    @log_function()
    async def add_label(self, email_id: str, label: str) -> bool:
        """
        Add a label to an email.
        
        Adds the specified label or moves the email to the specified
        folder, depending on the email system implementation.
        
        Args:
            email_id: Unique identifier of the email
            label: Label name or folder path to add
            
        Returns:
            True if operation successful, False otherwise
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to modify labels
            ValueError: If label name is invalid
        """
        pass
    
    @abstractmethod
    @log_function()
    async def remove_label(self, email_id: str, label: str) -> bool:
        """
        Remove a label from an email.
        
        Removes the specified label from the email or moves it out
        of the specified folder, depending on the email system implementation.
        
        Args:
            email_id: Unique identifier of the email
            label: Label name or folder path to remove
            
        Returns:
            True if operation successful, False otherwise
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to modify labels
            ValueError: If label name is invalid
        """
        pass
    
    @log_function()
    async def stream_emails(self, criteria: EmailSearchCriteria) -> AsyncGenerator[Email, None]:
        """
        Stream emails matching criteria for memory-efficient processing.
        
        Provides an async generator interface for processing large numbers
        of emails without loading them all into memory simultaneously.
        
        Args:
            criteria: Search criteria for filtering emails
            
        Yields:
            Email objects matching criteria
            
        Raises:
            PermissionError: If insufficient permissions to access emails
            ConnectionError: If not connected to email system
        """
        emails = await self.list_emails(criteria)
        for email in emails:
            yield email
    
    @log_function()
    def _parse_email_address(self, address_str: str) -> EmailAddress:
        """
        Parse email address string into structured format.
        
        Handles various email address formats including display names
        and extracts the components into an EmailAddress object.
        
        Args:
            address_str: Email address string to parse
            
        Returns:
            Parsed EmailAddress object
            
        Raises:
            ValueError: If address format is invalid
        """
        if not address_str:
            raise ValueError("Email address string cannot be empty")
        
        # Handle format: "Display Name <email@domain.com>"
        if '<' in address_str and '>' in address_str:
            parts = address_str.split('<')
            if len(parts) == 2:
                name = parts[0].strip().strip('"\'')
                email = parts[1].strip().rstrip('>')
                return EmailAddress(address=email, name=name if name else None)
        
        # Handle simple format: "email@domain.com"
        return EmailAddress(address=address_str.strip())
    
    @log_function()
    def _format_email_address(self, email_addr: EmailAddress) -> str:
        """
        Format EmailAddress object as string.
        
        Converts an EmailAddress object back to a properly formatted
        string representation suitable for email headers.
        
        Args:
            email_addr: EmailAddress object to format
            
        Returns:
            Formatted email address string
        """
        return str(email_addr)
    
    @log_function()
    async def get_attachment_content(self, email_id: str, attachment_id: str) -> bytes:
        """
        Get attachment content by ID.
        
        Retrieves the binary content of a specific attachment for
        processing or storage. Default implementation loads the full
        email and returns the attachment content.
        
        Args:
            email_id: Unique identifier of the email
            attachment_id: Unique identifier of the attachment
            
        Returns:
            Binary content of the attachment
            
        Raises:
            EmailNotFoundError: If email or attachment not found
            PermissionError: If insufficient permissions to access attachment
        """
        email = await self.get_email(email_id, include_attachments=True)
        for attachment in email.attachments:
            if attachment.attachment_id == attachment_id and attachment.content:
                return attachment.content
        
        raise EmailNotFoundError(f"Attachment {attachment_id} not found in email {email_id}")
    
    @log_function()
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on email system connection.
        
        Validates that the email system is accessible and the connection
        is functioning properly. Useful for monitoring and diagnostics.
        
        Returns:
            Dictionary containing health status information:
            - connected: Boolean connection status
            - user_email: Authenticated user email
            - last_check: Timestamp of health check
            - Additional provider-specific metrics
        """
        try:
            if not self.is_connected:
                return {
                    "connected": False,
                    "user_email": None,
                    "last_check": datetime.now().isoformat(),
                    "error": "Not connected"
                }
            
            profile = await self.get_profile()
            return {
                "connected": True,
                "user_email": profile.get("email"),
                "display_name": profile.get("name"),
                "last_check": datetime.now().isoformat(),
                "profile_accessible": True
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "connected": False,
                "user_email": self.user_email,
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            } 
"""
Base email interface for the email agent.

This module provides the abstract interface that all email system integrations
must implement. This allows the email agent to work with different email
systems (Gmail, Microsoft 365, IMAP, etc.) through a common interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

@dataclass
class EmailAddress:
    """Represents an email address with optional display name."""
    address: str
    name: Optional[str] = None
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address

@dataclass
class EmailAttachment:
    """Represents an email attachment."""
    filename: str
    content_type: str
    size: int
    attachment_id: Optional[str] = None  # For referencing in the email system
    content: Optional[bytes] = None  # Actual file content (loaded on demand)

class EmailImportance(Enum):
    """Email importance levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

@dataclass
class Email:
    """Represents an email message."""
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
    labels: List[str] = field(default_factory=list)  # Gmail labels or folder names
    message_id: Optional[str] = None  # RFC message ID
    in_reply_to: Optional[str] = None  # ID of message this replies to
    raw_data: Optional[Dict[str, Any]] = None  # Original API response for debugging

@dataclass
class EmailSearchCriteria:
    """Criteria for searching emails."""
    query: Optional[str] = None  # Free text search
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

@dataclass
class EmailSendRequest:
    """Request to send an email."""
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

class EmailSystemError(Exception):
    """Base exception for email system errors."""
    pass

class AuthenticationError(EmailSystemError):
    """Raised when authentication fails."""
    pass

class ConnectionError(EmailSystemError):
    """Raised when connection to email system fails."""
    pass

class PermissionError(EmailSystemError):
    """Raised when operation requires permissions not granted."""
    pass

class EmailNotFoundError(EmailSystemError):
    """Raised when requested email is not found."""
    pass

class BaseEmailInterface(ABC):
    """
    Abstract base class for email system integrations.
    
    All email system implementations (Gmail, Microsoft Graph, IMAP, etc.)
    must inherit from this class and implement all abstract methods.
    """
    
    def __init__(self):
        self.is_connected = False
        self.user_email = None
        self.display_name = None
    
    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to the email system using provided credentials.
        
        Args:
            credentials: Authentication credentials (format varies by implementation)
            
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            AuthenticationError: If credentials are invalid
            ConnectionError: If unable to connect to email system
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the email system."""
        pass
    
    @abstractmethod
    async def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information.
        
        Returns:
            Dict with profile info including email, name, etc.
        """
        pass
    
    @abstractmethod
    async def list_emails(self, criteria: EmailSearchCriteria) -> List[Email]:
        """
        List emails matching the given criteria.
        
        Args:
            criteria: Search criteria for filtering emails
            
        Returns:
            List of Email objects matching criteria
            
        Raises:
            PermissionError: If insufficient permissions to access emails
        """
        pass
    
    @abstractmethod
    async def get_email(self, email_id: str, include_attachments: bool = False) -> Email:
        """
        Get a specific email by ID.
        
        Args:
            email_id: Unique identifier of the email
            include_attachments: Whether to load attachment content
            
        Returns:
            Email object
            
        Raises:
            EmailNotFoundError: If email with given ID doesn't exist
            PermissionError: If insufficient permissions to access email
        """
        pass
    
    @abstractmethod
    async def send_email(self, request: EmailSendRequest) -> str:
        """
        Send an email.
        
        Args:
            request: Email send request with recipients, content, etc.
            
        Returns:
            str: ID of the sent email
            
        Raises:
            PermissionError: If insufficient permissions to send emails
            EmailSystemError: If sending fails
        """
        pass
    
    @abstractmethod
    async def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            email_id: ID of email to mark as read
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    async def mark_as_unread(self, email_id: str) -> bool:
        """
        Mark an email as unread.
        
        Args:
            email_id: ID of email to mark as unread
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    async def delete_email(self, email_id: str) -> bool:
        """
        Delete an email.
        
        Args:
            email_id: ID of email to delete
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    async def get_labels(self) -> List[str]:
        """
        Get available labels/folders.
        
        Returns:
            List of label/folder names
        """
        pass
    
    @abstractmethod
    async def add_label(self, email_id: str, label: str) -> bool:
        """
        Add a label to an email.
        
        Args:
            email_id: ID of email
            label: Label to add
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    async def remove_label(self, email_id: str, label: str) -> bool:
        """
        Remove a label from an email.
        
        Args:
            email_id: ID of email
            label: Label to remove
            
        Returns:
            bool: True if successful
        """
        pass
    
    # Optional streaming methods for large datasets
    async def stream_emails(self, criteria: EmailSearchCriteria) -> AsyncGenerator[Email, None]:
        """
        Stream emails matching criteria (default implementation uses list_emails).
        
        Implementations can override this for more efficient streaming.
        """
        emails = await self.list_emails(criteria)
        for email in emails:
            yield email
    
    # Helper methods
    def _parse_email_address(self, address_str: str) -> EmailAddress:
        """Parse email address string into EmailAddress object."""
        if '<' in address_str and '>' in address_str:
            # Format: "Display Name <email@domain.com>"
            name = address_str.split('<')[0].strip().strip('"')
            address = address_str.split('<')[1].split('>')[0].strip()
            return EmailAddress(address=address, name=name if name else None)
        else:
            # Simple format: "email@domain.com"
            return EmailAddress(address=address_str.strip())
    
    def _format_email_address(self, email_addr: EmailAddress) -> str:
        """Format EmailAddress object as string."""
        if email_addr.name:
            return f'"{email_addr.name}" <{email_addr.address}>'
        return email_addr.address 
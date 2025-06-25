"""
Gmail Email Interface

A complete Gmail API integration for email management in private market
asset management environments. Provides seamless Google Workspace integration with
business authentication, error handling, and monitoring capabilities.

Features:
    - OAuth 2.0 authentication with Google Identity platform
    - Complete email management (read, send, delete, labels)
    - search capabilities with Gmail-specific filters
    - Attachment handling with metadata extraction and processing
    - Production-grade error handling and retry logic
    - Complete logging and performance monitoring
    - Contacts integration for sender validation

Business Context:
    Designed for private market asset management firms using Google Workspace
    for processing sensitive financial communications, deal documents, and
    investor correspondence with institutional-grade security and compliance.

Technical Architecture:
    - Google Auth library for OAuth 2.0 flows
    - Gmail API v1 for complete email operations
    - Async operations with thread pool execution for blocking calls
    - error mapping and business-context exceptions
    - Thread pool execution for blocking Google API calls

Integration Points:
    - Asset document processing pipelines
    - Contact extraction and sender validation
    - Spam detection and security scanning
    - Memory systems for learning and adaptation

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import asyncio
import base64
import contextlib
import email
import os

# Logging system
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

# # Third-party imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function  # noqa: E402

from .base import (  # noqa: E402
    AuthenticationError,
    BaseEmailInterface,
    ConnectionError,
    Email,
    EmailAttachment,
    EmailImportance,
    EmailNotFoundError,
    EmailSearchCriteria,
    EmailSendRequest,
    EmailSystemError,
)

# Initialize logger
logger = get_logger(__name__)


class GmailInterface(BaseEmailInterface):
    """
    Gmail API integration for email management.

    Provides complete email management capabilities through Gmail API v1
    with production-grade authentication, error handling, and monitoring designed
    for private market asset management environments using Google Workspace.

    Features:
        - OAuth 2.0 authentication with Google Identity platform
        - Complete email operations (CRUD, search, labels)
        - Gmail search query support with filters
        - attachment handling with metadata extraction
        - Business-context error handling and retry logic
        - Performance monitoring and health checking
        - Contacts integration for sender validation

    Business Context:
        Designed for asset management firms requiring reliable Google Workspace
        integration for processing sensitive financial communications, investor
        updates, and deal-related correspondence with business security.

    Technical Architecture:
        - Google Auth libraries for OAuth 2.0 authentication
        - Gmail API v1 for email operations
        - Thread pool for blocking API operations
        - Complete error mapping and handling
        - logging and monitoring
    """

    # Gmail API scopes for complete email access
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/contacts.readonly",  # For contact integration
    ]

    # API configuration and limits
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100
    REQUEST_TIMEOUT = 30
    RETRY_ATTEMPTS = 3

    def __init__(self) -> None:
        """
        Initialize Gmail interface with complete configuration.

        Sets up the Gmail API client with OAuth 2.0 authentication,
        thread pool for blocking operations, and logging
        for production deployment in asset management environments.

        Raises:
            RuntimeError: If required Google libraries are missing

        Note:
            Requires valid Google OAuth 2.0 credentials for Gmail API access
            with appropriate scopes for email management operations.
        """
        super().__init__()

        self.logger = get_logger(f"{__name__}.GmailInterface")
        self.logger.info("Initializing Gmail email interface")

        # Core components
        self.service = None
        self.credentials: Credentials | None = None
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gmail")

        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0.0

        self.logger.info("Gmail interface initialized successfully")

    @log_function()
    async def connect(self, credentials: dict[str, Any]) -> bool:
        """
        Establish connection to Gmail using OAuth 2.0 authentication.

        Performs complete OAuth 2.0 authentication flow with Google Identity
        platform including token caching, refresh logic, and interactive authentication
        when required. Provides user experience for business environments.

        Args:
            credentials: Authentication configuration containing one of:
                - 'credentials_file': Path to OAuth 2.0 credentials.json (first-time auth)
                - 'token_file': Path to token.json file (existing auth)
                - 'token_data': Direct token data dictionary

        Returns:
            True if connection successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If network connection fails
            ValueError: If credentials configuration is invalid

        Business Flow:
            1. Validate credentials configuration
            2. Check for cached authentication tokens
            3. Attempt silent token refresh if expired
            4. Launch interactive authentication if needed
            5. Validate connection with profile retrieval
            6. Initialize Gmail service client
        """
        try:
            self.logger.info("Starting Gmail authentication flow")

            creds = None

            # Load existing token if available
            if "token_file" in credentials and os.path.exists(
                credentials["token_file"]
            ):
                self.logger.info(
                    f"Loading cached token from {credentials['token_file']}"
                )
                creds = Credentials.from_authorized_user_file(
                    credentials["token_file"], self.SCOPES
                )
            elif "token_data" in credentials:
                self.logger.info("Loading token from provided token data")
                creds = Credentials.from_authorized_user_info(
                    credentials["token_data"], self.SCOPES
                )

            # Handle token validation and refresh
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    self.logger.info("Refreshing expired Gmail token")
                    # Refresh expired token
                    await self._run_in_executor(creds.refresh, Request())
                    self.logger.info("Gmail token refreshed successfully")
                else:
                    # Perform full OAuth flow
                    if "credentials_file" not in credentials:
                        raise AuthenticationError(
                            "No credentials file provided for initial Gmail authentication"
                        )

                    self.logger.info("Starting interactive Gmail OAuth flow")
                    creds = await self._perform_oauth_flow(
                        credentials["credentials_file"]
                    )

                # Save refreshed/new token for future use
                if "token_file" in credentials:
                    self.logger.info(
                        f"Saving Gmail token to {credentials['token_file']}"
                    )
                    with open(credentials["token_file"], "w") as token:
                        token.write(creds.to_json())

            # Build Gmail service
            self.credentials = creds
            self.service = await self._run_in_executor(
                lambda: build("gmail", "v1", credentials=creds)
            )

            # Validate connection by getting user profile
            profile = await self.get_profile()
            self.user_email = profile.get("email")
            self.display_name = profile.get("name")
            self.is_connected = True

            self.logger.info(f"Gmail connection established for {self.user_email}")
            return True

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Gmail connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Gmail: {e}") from e

    @log_function()
    async def _perform_oauth_flow(self, credentials_file: str) -> Credentials:
        """
        Perform interactive OAuth 2.0 flow with Google Identity platform.

        Launches interactive authentication flow using system web browser
        with user experience optimized for business environments.

        Args:
            credentials_file: Path to Google OAuth 2.0 credentials JSON file

        Returns:
            Validated Google credentials object

        Raises:
            AuthenticationError: If OAuth flow fails
            FileNotFoundError: If credentials file doesn't exist
        """
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"Gmail credentials file not found: {credentials_file}"
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, self.SCOPES
            )

            self.logger.info("Starting Gmail OAuth 2.0 flow")
            logger.info("🌐 Opening browser for Gmail authentication...")
            logger.info("   Please complete authentication in the browser window")

            # Run OAuth flow with local server
            creds = await self._run_in_executor(flow.run_local_server, port=0)

            self.logger.info("Gmail OAuth flow completed successfully")
            logger.info("✅ Gmail authentication successful!")

            return creds

        except Exception as e:
            self.logger.error(f"Gmail OAuth flow failed: {e}")
            raise AuthenticationError(f"Gmail OAuth authentication failed: {e}") from e

    @log_function()
    async def disconnect(self) -> None:
        """
        Disconnect from Gmail and cleanup resources.

        Properly closes service connections, clears authentication tokens,
        and resets connection state with complete cleanup.
        """
        self.logger.info("Disconnecting from Gmail")

        # Clear service and credentials
        self.service = None
        self.credentials = None

        # Reset connection state
        self.is_connected = False
        self.user_email = None
        self.display_name = None

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        self.logger.info("Gmail disconnection complete")

    @log_function()
    async def get_profile(self) -> dict[str, Any]:
        """
        Retrieve user profile information from Gmail.

        Gets complete user profile including email address, display name,
        and Gmail-specific information for business context and logging.

        Returns:
            Dictionary containing user profile information

        Raises:
            ConnectionError: If not connected to Gmail
            EmailSystemError: If profile retrieval fails
        """
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            # Get Gmail profile information
            gmail_profile = await self._run_in_executor(
                self.service.users().getProfile(userId="me").execute
            )

            # Extract user information
            email_address = gmail_profile.get("emailAddress", "")
            name = email_address.split("@")[0] if email_address else "Gmail User"

            profile = {
                "email": email_address,
                "name": name,
                "messages_total": gmail_profile.get("messagesTotal", 0),
                "threads_total": gmail_profile.get("threadsTotal", 0),
                "history_id": gmail_profile.get("historyId"),
            }

            self.logger.info(f"Retrieved Gmail profile for {email_address}")
            return profile

        except HttpError as e:
            self.logger.error(f"Gmail profile retrieval failed: {e}")
            raise EmailSystemError(f"Failed to get Gmail profile: {e}") from e
        except Exception as e:
            self.logger.error(f"Gmail profile error: {e}")
            raise EmailSystemError(f"Profile retrieval error: {e}") from e

    @log_function()
    async def _run_in_executor(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute blocking Gmail API calls in thread pool.

        Provides async interface for blocking Google API calls with
        proper error handling and performance tracking.

        Args:
            func: Blocking function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Propagates any exception from the function call
        """
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        try:
            result = await loop.run_in_executor(self.executor, func, *args, **kwargs)

            # Update performance tracking
            execution_time = loop.time() - start_time
            self.request_count += 1
            self.total_request_time += execution_time

            return result

        except Exception as e:
            self.error_count += 1
            execution_time = loop.time() - start_time
            self.total_request_time += execution_time

            self.logger.error(f"Gmail API call failed: {func.__name__} - {e}")
            raise

    async def list_emails(self, criteria: EmailSearchCriteria) -> list[Email]:
        """List emails matching criteria."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            # Build Gmail search query
            query_parts = []

            if criteria.query:
                query_parts.append(criteria.query)
            if criteria.sender:
                query_parts.append(f"from:{criteria.sender}")
            if criteria.recipient:
                query_parts.append(f"to:{criteria.recipient}")
            if criteria.subject:
                query_parts.append(f"subject:{criteria.subject}")
            if criteria.has_attachments:
                query_parts.append("has:attachment")
            if criteria.is_unread is True:
                query_parts.append("is:unread")
            elif criteria.is_unread is False:
                query_parts.append("is:read")
            if criteria.is_flagged:
                query_parts.append("is:starred")
            if criteria.date_after:
                date_str = criteria.date_after.strftime("%Y/%m/%d")
                query_parts.append(f"after:{date_str}")
            if criteria.date_before:
                date_str = criteria.date_before.strftime("%Y/%m/%d")
                query_parts.append(f"before:{date_str}")
            for label in criteria.labels:
                query_parts.append(f"label:{label}")

            query = " ".join(query_parts) if query_parts else None

            # Search for messages
            result = await self._run_in_executor(
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=criteria.max_results)
                .execute
            )

            messages = result.get("messages", [])

            # Get full message details
            emails = []
            # Include attachments if not explicitly excluded
            include_attachments = criteria.has_attachments is not False

            for msg in messages:
                try:
                    email_obj = await self.get_email(
                        msg["id"], include_attachments=include_attachments
                    )
                    emails.append(email_obj)
                except Exception as e:
                    logger.warning("Failed to get email %s: %s", msg["id"], e)
                    continue

            return emails

        except HttpError as e:
            raise EmailSystemError(f"Failed to list Gmail messages: {e}") from e

    async def get_email(
        self, email_id: str, include_attachments: bool = False
    ) -> Email:
        """Get a specific email by ID."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            # Get message
            message = await self._run_in_executor(
                self.service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute
            )

            return await self._parse_gmail_message(message, include_attachments)

        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found") from e
            raise EmailSystemError(f"Failed to get Gmail message: {e}") from e

    async def send_email(self, request: EmailSendRequest) -> str:
        """Send an email via Gmail."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            # Create message
            if request.body_html:
                message = MIMEMultipart("alternative")
                if request.body_text:
                    message.attach(MIMEText(request.body_text, "plain"))
                message.attach(MIMEText(request.body_html, "html"))
            else:
                message = MIMEText(request.body_text or "", "plain")

            # Set headers
            message["to"] = ", ".join([addr.address for addr in request.to])
            message["subject"] = request.subject

            if request.cc:
                message["cc"] = ", ".join([addr.address for addr in request.cc])
            if request.bcc:
                message["bcc"] = ", ".join([addr.address for addr in request.bcc])

            # Handle reply threading
            if request.reply_to_message_id:
                message["In-Reply-To"] = request.reply_to_message_id
                message["References"] = request.reply_to_message_id

            # Add attachments
            if request.attachments:
                if not isinstance(message, MIMEMultipart):
                    # Convert to multipart
                    text_part = message
                    message = MIMEMultipart()
                    message.attach(text_part)
                    # Copy headers
                    for key, value in text_part.items():
                        if key.lower() not in [
                            "content-type",
                            "content-transfer-encoding",
                        ]:
                            message[key] = value

                for attachment in request.attachments:
                    if attachment.content:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.content)
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {attachment.filename}",
                        )
                        message.attach(part)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send message
            result = await self._run_in_executor(
                self.service.users()
                .messages()
                .send(userId="me", body={"raw": raw_message})
                .execute
            )

            return result["id"]

        except HttpError as e:
            raise EmailSystemError(f"Failed to send Gmail message: {e}") from e

    async def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read."""
        return await self._modify_labels(email_id, remove_labels=["UNREAD"])

    async def mark_as_unread(self, email_id: str) -> bool:
        """Mark email as unread."""
        return await self._modify_labels(email_id, add_labels=["UNREAD"])

    async def delete_email(self, email_id: str) -> bool:
        """Delete an email (move to trash)."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            await self._run_in_executor(
                self.service.users().messages().trash(userId="me", id=email_id).execute
            )
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found") from e
            raise EmailSystemError(f"Failed to delete Gmail message: {e}") from e

    async def get_labels(self) -> list[str]:
        """Get all Gmail labels."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            result = await self._run_in_executor(
                self.service.users().labels().list(userId="me").execute
            )

            labels = result.get("labels", [])
            return [label["name"] for label in labels]

        except HttpError as e:
            raise EmailSystemError(f"Failed to get Gmail labels: {e}") from e

    async def add_label(self, email_id: str, label: str) -> bool:
        """Add a label to an email."""
        return await self._modify_labels(email_id, add_labels=[label])

    async def remove_label(self, email_id: str, label: str) -> bool:
        """Remove a label from an email."""
        return await self._modify_labels(email_id, remove_labels=[label])

    async def get_contacts(self) -> list[dict[str, Any]]:
        """Get all Gmail contacts."""
        if not self.credentials:
            raise ConnectionError("Not connected to Gmail")

        try:
            # Build People API service
            people_service = await self._run_in_executor(
                build, "people", "v1", credentials=self.credentials
            )

            contacts = []
            next_page_token = None
            page_count = 0

            # Fetch all contacts using pagination
            while True:
                page_count += 1
                logger.debug("Fetching contacts page %d", page_count)

                # Build request parameters
                request_params = {
                    "resourceName": "people/me",
                    "personFields": "names,emailAddresses",
                    "pageSize": 1000,  # Maximum allowed per page
                }

                if next_page_token:
                    request_params["pageToken"] = next_page_token

                # Get contacts page
                results = await self._run_in_executor(
                    people_service.people().connections().list(**request_params).execute
                )

                connections = results.get("connections", [])
                logger.debug("Page %d: Found %d contacts", page_count, len(connections))

                # Process contacts from this page
                for person in connections:
                    contact = {"name": "", "emails": []}

                    # Get name
                    names = person.get("names", [])
                    if names:
                        contact["name"] = names[0].get("displayName", "")

                    # Get email addresses
                    emails = person.get("emailAddresses", [])
                    for email_data in emails:
                        email_addr = email_data.get("value", "").lower()
                        if email_addr:
                            contact["emails"].append(email_addr)

                    # Only add contacts that have email addresses
                    if contact["emails"]:
                        contacts.append(contact)

                # Check if there are more pages
                next_page_token = results.get("nextPageToken")
                if not next_page_token:
                    break

                # Safety limit to prevent infinite loops
                if page_count > 10:
                    logger.warning(
                        "Stopped at page %d to prevent infinite loop", page_count
                    )
                    break

            logger.info(
                "Total contacts with emails: %d (from %d pages)",
                len(contacts),
                page_count,
            )
            return contacts

        except Exception as e:
            logger.warning("Could not fetch contacts: %s", e)
            return []

    # Helper methods
    async def _modify_labels(
        self,
        email_id: str,
        add_labels: list[str] = None,
        remove_labels: list[str] = None,
    ) -> bool:
        """Modify labels on an email."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")

        try:
            body = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels

            await self._run_in_executor(
                self.service.users()
                .messages()
                .modify(userId="me", id=email_id, body=body)
                .execute
            )
            return True

        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found") from e
            raise EmailSystemError(f"Failed to modify Gmail message labels: {e}") from e

    async def _parse_gmail_message(
        self, message: dict[str, Any], include_attachments: bool = False
    ) -> Email:
        """Parse Gmail API message into Email object."""

        headers = {}
        for header in message["payload"].get("headers", []):
            headers[header["name"].lower()] = header["value"]

        # Extract basic fields
        subject = headers.get("subject", "")
        sender = self._parse_email_address(headers.get("from", ""))
        message_id = headers.get("message-id")
        in_reply_to = headers.get("in-reply-to")

        # Parse recipients
        recipients = []
        if "to" in headers:
            for addr in headers["to"].split(","):
                recipients.append(self._parse_email_address(addr.strip()))

        cc = []
        if "cc" in headers:
            for addr in headers["cc"].split(","):
                cc.append(self._parse_email_address(addr.strip()))

        # Parse dates
        sent_date = None
        if "date" in headers:
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                sent_date = email.utils.parsedate_to_datetime(headers["date"])

        # Parse body
        body_text, body_html = await self._extract_body(message["payload"])

        # Parse attachments
        attachments = []
        if include_attachments:
            attachments = await self._extract_attachments(
                message["payload"], message["id"]
            )

        # Determine importance
        importance = EmailImportance.NORMAL
        priority = headers.get("x-priority", headers.get("priority", ""))
        if priority in ["1", "high"]:
            importance = EmailImportance.HIGH
        elif priority in ["5", "low"]:
            importance = EmailImportance.LOW

        # Parse labels and flags
        labels = []
        is_read = "UNREAD" not in message.get("labelIds", [])
        is_flagged = "STARRED" in message.get("labelIds", [])

        for label_id in message.get("labelIds", []):
            if label_id not in ["UNREAD", "STARRED", "IMPORTANT"]:
                labels.append(label_id)

        return Email(
            id=message["id"],
            thread_id=message.get("threadId"),
            subject=subject,
            sender=sender,
            recipients=recipients,
            cc=cc,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            importance=importance,
            is_read=is_read,
            is_flagged=is_flagged,
            sent_date=sent_date,
            received_date=sent_date,  # Gmail doesn't separate sent/received
            headers=headers,
            labels=labels,
            message_id=message_id,
            in_reply_to=in_reply_to,
            raw_data=message,
        )

    async def _extract_body(
        self, payload: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Extract text and HTML body from Gmail message payload."""
        body_text = None
        body_html = None

        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    body_text = await self._decode_body_data(part["body"])
                elif part["mimeType"] == "text/html":
                    body_html = await self._decode_body_data(part["body"])
                elif part["mimeType"].startswith("multipart/"):
                    # Nested multipart
                    nested_text, nested_html = await self._extract_body(part)
                    if nested_text:
                        body_text = nested_text
                    if nested_html:
                        body_html = nested_html
        else:
            # Single part message
            if payload["mimeType"] == "text/plain":
                body_text = await self._decode_body_data(payload["body"])
            elif payload["mimeType"] == "text/html":
                body_html = await self._decode_body_data(payload["body"])

        return body_text, body_html

    async def _decode_body_data(self, body_data: dict[str, Any]) -> str | None:
        """Decode Gmail message body data."""
        if "data" not in body_data:
            return None

        try:
            data = body_data["data"]
            # Gmail uses URL-safe base64 encoding
            decoded = base64.urlsafe_b64decode(data + "===")  # Add padding
            return decoded.decode("utf-8")
        except Exception as e:
            logger.warning("Failed to decode body data: %s", e)
            return None

    async def _extract_attachments(
        self, payload: dict[str, Any], message_id: str
    ) -> list[EmailAttachment]:
        """Extract attachments from Gmail message."""
        attachments = []

        if "parts" in payload:
            for part in payload["parts"]:
                if "filename" in part and part["filename"]:
                    # This is an attachment
                    attachment = EmailAttachment(
                        filename=part["filename"],
                        content_type=part["mimeType"],
                        size=part["body"].get("size", 0),
                        attachment_id=part["body"].get("attachmentId"),
                    )

                    # Optionally load content
                    if part["body"].get("attachmentId"):
                        try:
                            logger.info(
                                f"Downloading content for {attachment.filename} from Gmail message {message_id}"
                            )
                            att_data = await self._run_in_executor(
                                self.service.users()
                                .messages()
                                .attachments()
                                .get(
                                    userId="me",
                                    messageId=message_id,
                                    id=part["body"]["attachmentId"],
                                )
                                .execute
                            )
                            attachment.content = base64.urlsafe_b64decode(
                                att_data["data"]
                            )
                            logger.info(
                                f"Successfully downloaded {attachment.filename}: {len(attachment.content)} bytes"
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to download attachment {attachment.filename} from Gmail message {message_id}: {e}"
                            )
                            # Keep the attachment in the list but without content
                    else:
                        logger.warning(
                            f"Gmail attachment {attachment.filename} has no attachment ID - cannot download content"
                        )

                    attachments.append(attachment)

        return attachments

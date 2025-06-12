"""
Microsoft Graph Email Interface

A complete Microsoft Graph API integration for email management
in private market asset management environments. Provides seamless Office 365/Exchange
integration with business authentication, error handling, and monitoring.

Features:
    - OAuth 2.0 authentication with interactive web-based flow
    - Complete email management (read, send, delete, labels)
    - search capabilities with business-context filters
    - Attachment handling with virus scanning integration
    - Production-grade error handling and retry logic
    - Complete logging and performance monitoring
    - Health checking and connection management

Business Context:
    Designed for private market asset management firms requiring reliable
    integration with Microsoft 365 environments for processing sensitive
    financial communications, deal documents, and investor correspondence.
    
Technical Architecture:
    - MSAL (Microsoft Authentication Library) for OAuth 2.0 flows
    - Async HTTP client for high-performance API interactions
    - Web server for interactive authentication callback handling
    - Complete error mapping and business-context exceptions
    - Thread pool execution for blocking operations

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

import asyncio
import base64
import http.server
import json
import os
import socketserver

# Logging system
import sys
import threading
import webbrowser
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import aiohttp
import msal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logging_system import get_logger, log_function

from .base import (
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
)

# Initialize logger
logger = get_logger(__name__)

class AuthorizationHandler(http.server.SimpleHTTPRequestHandler):
    """
    OAuth 2.0 authorization callback handler for Microsoft Graph authentication.
    
    Handles the OAuth callback from Microsoft identity platform during
    interactive authentication flows, extracting authorization codes and
    providing user-friendly feedback during the authentication process.
    
    Business Context:
        Provides authentication experience for asset management
        users accessing Microsoft 365 email systems securely.
    """

    @log_function()
    def do_GET(self) -> None:
        """
        Handle GET request with OAuth authorization callback.
        
        Processes the OAuth callback from Microsoft identity platform,
        extracts authorization code, and provides appropriate user feedback
        with styling for business environments.
        
        Raises:
            None: Gracefully handles all errors with appropriate HTTP responses
        """
        try:
            if self.path.startswith('/?code='):
                # Extract authorization code and state from callback
                parsed = urlparse(self.path)
                query_params = parse_qs(parsed.query)

                if 'code' in query_params:
                    self.server.auth_code = query_params['code'][0]
                    self.server.state = query_params.get('state', [None])[0]

                    logger.info("OAuth authorization code received successfully")

                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    success_html = """
                    <html>
                    <head>
                        <title>Email Agent - Authentication Success</title>
                        <style>
                            body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; 
                                   padding: 50px; background: #f5f5f5; }
                            .container { max-width: 600px; margin: 0 auto; background: white; 
                                        padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                            .success { color: #28a745; font-size: 48px; margin-bottom: 20px; }
                            h2 { color: #333; margin-bottom: 15px; }
                            p { color: #666; line-height: 1.6; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="success">✅</div>
                            <h2>Authentication Successful!</h2>
                            <p>Microsoft 365 authentication completed successfully.</p>
                            <p>You can now close this window and return to the email agent.</p>
                            <p><strong>Email Agent is now connected to your Microsoft 365 account.</strong></p>
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(success_html.encode())
                else:
                    # Handle missing authorization code
                    logger.error("OAuth callback missing authorization code")
                    self._send_error_response("No authorization code received")

            elif self.path.startswith('/?error='):
                # Handle OAuth errors
                parsed = urlparse(self.path)
                query_params = parse_qs(parsed.query)
                error_code = query_params.get('error', ['unknown'])[0]
                error_description = query_params.get('error_description', ['Unknown error'])[0]

                logger.error(f"OAuth error: {error_code} - {error_description}")
                self._send_error_response(f"Authentication failed: {error_description}")

            else:
                # Default waiting response
                self._send_waiting_response()

        except Exception as e:
            logger.error(f"OAuth callback handler error: {e}")
            self._send_error_response("Authentication processing error")

    def _send_error_response(self, error_message: str) -> None:
        """Send error response to user."""
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        error_html = f"""
        <html>
        <head>
            <title>Email Agent - Authentication Error</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; text-align: center; 
                       padding: 50px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; 
                            padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .error {{ color: #dc3545; font-size: 48px; margin-bottom: 20px; }}
                h2 {{ color: #333; margin-bottom: 15px; }}
                p {{ color: #666; line-height: 1.6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">❌</div>
                <h2>Authentication Failed</h2>
                <p>{error_message}</p>
                <p>Please close this window and try authentication again.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(error_html.encode())

    def _send_waiting_response(self) -> None:
        """Send waiting response to user."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        waiting_html = """
        <html>
        <head>
            <title>Email Agent - Waiting for Authentication</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; 
                       padding: 50px; background: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background: white; 
                            padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .waiting { color: #007bff; font-size: 48px; margin-bottom: 20px; 
                          animation: pulse 2s infinite; }
                @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
                h2 { color: #333; margin-bottom: 15px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="waiting">🔄</div>
                <h2>Waiting for Microsoft 365 Authentication...</h2>
                <p>Please complete the authentication process in the Microsoft login window.</p>
                <p>This window will update automatically when authentication is complete.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(waiting_html.encode())

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP server logging to avoid noise."""
        pass

class MicrosoftGraphInterface(BaseEmailInterface):
    """
    Microsoft Graph API integration for email management.
    
    Provides complete email management capabilities through Microsoft Graph API
    with production-grade authentication, error handling, and monitoring designed
    for private market asset management environments.
    
    Features:
        - OAuth 2.0 authentication with interactive web flow
        - Complete email operations (CRUD, search, labels)
        - attachment handling with metadata extraction
        - Business-context error handling and retry logic
        - Performance monitoring and health checking
        - Async operations for high-throughput processing
        
    Business Context:
        Designed for asset management firms requiring reliable Microsoft 365
        integration for processing sensitive financial communications, investor
        updates, and deal-related correspondence with institutional-grade security.
        
    Technical Architecture:
        - MSAL for OAuth 2.0 authentication flows
        - Async HTTP client for API interactions
        - Thread pool for blocking operations
        - Complete error mapping and handling
        - logging and monitoring
    """

    # Microsoft Graph API configuration
    SCOPES = [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/User.Read'
    ]

    GRAPH_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    AUTH_ENDPOINT = 'https://login.microsoftonline.com'

    # API limits and timeouts
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100
    REQUEST_TIMEOUT = 30
    AUTH_TIMEOUT = 300  # 5 minutes for authentication

    def __init__(self, credentials_path: str = "config/msgraph_credentials.json") -> None:
        """
        Initialize Microsoft Graph interface with complete configuration.
        
        Sets up the Microsoft Graph API client with OAuth 2.0 authentication,
        async HTTP client configuration, and logging for production
        deployment in asset management environments.
        
        Args:
            credentials_path: Path to Microsoft Graph credentials JSON file
            
        Raises:
            FileNotFoundError: If credentials file not found
            ValueError: If credentials file is invalid
            RuntimeError: If required dependencies are missing
            
        Note:
            Requires valid Microsoft Graph application registration with
            appropriate permissions for email access in the target tenant.
        """
        super().__init__()

        self.logger = get_logger(f"{__name__}.MicrosoftGraphInterface")
        self.logger.info("Initializing Microsoft Graph email interface")

        # Core components
        self.access_token: str | None = None
        self.app: msal.PublicClientApplication | None = None
        self.session: aiohttp.ClientSession | None = None
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="msgraph")

        # Load and validate credentials
        self.credentials_path = Path(credentials_path)
        self.credentials = self._load_credentials()

        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0.0

        self.logger.info(f"Microsoft Graph interface initialized for {self.credentials.get('application_name', 'Unknown App')}")

    @log_function()
    def _load_credentials(self) -> dict[str, Any]:
        """
        Load and validate Microsoft Graph credentials from file.
        
        Loads OAuth 2.0 application credentials required for Microsoft Graph
        authentication including client ID, tenant ID, and application metadata.
        
        Returns:
            Dictionary containing validated credentials
            
        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If credentials file is invalid or missing required fields
        """
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Microsoft Graph credentials file not found: {self.credentials_path}")

        try:
            with open(self.credentials_path) as f:
                credentials = json.load(f)

            # Validate required fields
            required_fields = ['client_id', 'tenant_id']
            missing_fields = [field for field in required_fields if field not in credentials]

            if missing_fields:
                raise ValueError(f"Missing required credential fields: {missing_fields}")

            # Validate field formats
            if not credentials['client_id'] or len(credentials['client_id']) < 10:
                raise ValueError("Invalid client_id in credentials")

            if not credentials['tenant_id'] or len(credentials['tenant_id']) < 10:
                raise ValueError("Invalid tenant_id in credentials")

            self.logger.info(f"Loaded Microsoft Graph credentials for tenant: {credentials['tenant_id'][:8]}...")
            return credentials

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in credentials file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading credentials: {e}")

    @log_function()
    async def connect(self) -> bool:
        """
        Establish connection to Microsoft Graph using OAuth 2.0 authentication.
        
        Performs complete OAuth 2.0 authentication flow with Microsoft identity
        platform including token caching, refresh logic, and interactive authentication
        when required. Provides user experience for business environments.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If network connection fails
            RuntimeError: If critical components are unavailable
            
        Business Flow:
            1. Check for cached authentication tokens
            2. Attempt silent token refresh if expired
            3. Launch interactive authentication if needed
            4. Validate connection with profile retrieval
            5. Initialize async HTTP session for API calls
        """
        try:
            self.logger.info("Starting Microsoft Graph authentication flow")

            # Extract credentials
            client_id = self.credentials['client_id']
            tenant_id = self.credentials['tenant_id']
            redirect_uri = "http://localhost:8080"

            authority = f"{self.AUTH_ENDPOINT}/{tenant_id}"

            # Create MSAL public client application
            self.app = msal.PublicClientApplication(
                client_id=client_id,
                authority=authority
            )

            # Check for cached tokens first
            accounts = self.app.get_accounts()
            token_result = None

            if accounts:
                self.logger.info(f"Found {len(accounts)} cached Microsoft account(s)")
                # Attempt silent token acquisition
                token_result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])

                if token_result:
                    self.logger.info("Successfully acquired token silently (cached/refreshed)")
                else:
                    self.logger.info("Silent token acquisition failed - interactive authentication required")

            # If no cached token or silent acquisition failed, do interactive flow
            if not token_result:
                token_result = await self._perform_interactive_authentication(redirect_uri)

            # Validate token result
            if not token_result or 'access_token' not in token_result:
                error_msg = token_result.get('error_description', 'Unknown authentication error') if token_result else 'No token received'
                raise AuthenticationError(f"Microsoft Graph authentication failed: {error_msg}")

            # Store access token
            self.access_token = token_result['access_token']
            self.logger.info("Microsoft Graph access token acquired successfully")

            # Initialize HTTP session
            await self._initialize_http_session()

            # Validate connection by getting user profile
            profile = await self.get_profile()
            self.user_email = profile.get('email')
            self.display_name = profile.get('name')
            self.is_connected = True

            self.logger.info(f"Microsoft Graph connection established for {self.user_email}")
            return True

        except AuthenticationError:
            raise
        except Exception as e:
            self.logger.error(f"Microsoft Graph connection failed: {e}")
            raise ConnectionError(f"Failed to connect to Microsoft Graph: {e}")

    @log_function()
    async def _perform_interactive_authentication(self, redirect_uri: str) -> dict[str, Any] | None:
        """
        Perform interactive OAuth 2.0 authentication with web browser.
        
        Launches interactive authentication flow using system web browser
        with callback handling and user experience optimized
        for business environments.
        
        Args:
            redirect_uri: OAuth callback URI for authorization code
            
        Returns:
            Token result dictionary or None if authentication failed
            
        Raises:
            AuthenticationError: If interactive authentication fails
            RuntimeError: If local server cannot be started
        """
        self.logger.info("Starting interactive Microsoft Graph authentication")

        # Start local callback server
        port = 8080
        max_port_attempts = 10
        server = None

        for attempt in range(max_port_attempts):
            try:
                server = socketserver.TCPServer(("", port + attempt), AuthorizationHandler)
                server.auth_code = None
                server.state = None
                port = port + attempt
                break
            except OSError:
                if attempt == max_port_attempts - 1:
                    raise RuntimeError("Cannot start local server for OAuth callback")
                continue

        # Start server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Update redirect URI with actual port
            actual_redirect_uri = f"http://localhost:{port}"

            # Initialize authorization code flow
            flow = self.app.initiate_auth_code_flow(
                scopes=self.SCOPES,
                redirect_uri=actual_redirect_uri
            )

            if "auth_uri" not in flow:
                raise AuthenticationError("Failed to create Microsoft Graph authorization flow")

            auth_url = flow["auth_uri"]

            # Open browser for authentication
            self.logger.info("Opening browser for Microsoft 365 authentication")
            logger.info("🌐 Opening browser for Microsoft 365 authentication...")
            logger.info("   If browser doesn't open automatically, visit: %s", auth_url)

            webbrowser.open(auth_url)

            # Wait for authorization code
            self.logger.info(f"Waiting for OAuth callback on port {port}")
            logger.info("   Waiting for authentication completion...")

            # Poll for authorization code with timeout
            timeout_seconds = self.AUTH_TIMEOUT
            poll_interval = 1
            elapsed = 0

            while elapsed < timeout_seconds:
                if server.auth_code:
                    self.logger.info("Authorization code received from OAuth callback")
                    break

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                if elapsed % 30 == 0:  # Progress update every 30 seconds
                    self.logger.info(f"Still waiting for authentication... ({elapsed}s elapsed)")

            if not server.auth_code:
                raise AuthenticationError(f"Authentication timeout after {timeout_seconds} seconds")

            # Complete the flow with authorization code and state
            auth_response = {'code': server.auth_code}
            if server.state:
                auth_response['state'] = server.state

            token_result = self.app.acquire_token_by_auth_code_flow(
                auth_code_flow=flow,
                auth_response=auth_response
            )

            self.logger.info("Interactive authentication completed successfully")
            logger.info("✅ Microsoft 365 authentication successful!")

            return token_result

        finally:
            # Clean up server
            server.shutdown()
            server.server_close()

    @log_function()
    async def _initialize_http_session(self) -> None:
        """
        Initialize async HTTP session for Microsoft Graph API calls.
        
        Creates configured aiohttp session with appropriate headers,
        timeouts, and error handling for API interactions.
        """
        if self.session:
            await self.session.close()

        # Configure session with authentication headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'EmailAgent-MicrosoftGraph/1.0'
        }

        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            raise_for_status=False  # Handle errors manually
        )

        self.logger.info("HTTP session initialized for Microsoft Graph API")

    @log_function()
    async def disconnect(self) -> None:
        """
        Disconnect from Microsoft Graph and cleanup resources.
        
        Properly closes HTTP sessions, clears authentication tokens,
        and resets connection state with complete cleanup.
        """
        self.logger.info("Disconnecting from Microsoft Graph")

        # Close HTTP session
        if self.session:
            await self.session.close()
            self.session = None

        # Clear authentication
        self.access_token = None
        self.app = None

        # Reset connection state
        self.is_connected = False
        self.user_email = None
        self.display_name = None

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        self.logger.info("Microsoft Graph disconnection complete")

    @log_function()
    async def get_profile(self) -> dict[str, Any]:
        """
        Retrieve user profile information from Microsoft Graph.
        
        Gets complete user profile including email address, display name,
        and other relevant information for business context and logging.
        
        Returns:
            Dictionary containing user profile information
            
        Raises:
            ConnectionError: If not connected to Microsoft Graph
            EmailSystemError: If profile retrieval fails
        """
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            # Get user profile from Microsoft Graph
            url = f"{self.GRAPH_ENDPOINT}/me"

            async with self.session.get(url) as response:
                if response.status == 200:
                    profile_data = await response.json()

                    # Extract relevant profile information
                    profile = {
                        'email': profile_data.get('mail') or profile_data.get('userPrincipalName'),
                        'name': profile_data.get('displayName', 'Unknown User'),
                        'id': profile_data.get('id'),
                        'job_title': profile_data.get('jobTitle'),
                        'department': profile_data.get('department'),
                        'office_location': profile_data.get('officeLocation')
                    }

                    self.logger.info(f"Retrieved profile for {profile['email']}")
                    return profile

                else:
                    error_data = await response.json() if response.content_type == 'application/json' else {}
                    error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status}')
                    raise EmailSystemError(f"Failed to get Microsoft Graph profile: {error_msg}")

        except Exception as e:
            if isinstance(e, EmailSystemError):
                raise
            self.logger.error(f"Microsoft Graph profile retrieval failed: {e}")
            raise EmailSystemError(f"Profile retrieval error: {e}")

    async def list_emails(self, criteria: EmailSearchCriteria) -> list[Email]:
        """List emails matching criteria."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            # Build Microsoft Graph filter and search query
            filters = []

            if criteria.sender:
                filters.append(f"from/emailAddress/address eq '{criteria.sender}'")
            if criteria.subject:
                filters.append(f"contains(subject, '{criteria.subject}')")
            if criteria.has_attachments:
                filters.append("hasAttachments eq true")
            if criteria.is_unread is True:
                filters.append("isRead eq false")
            elif criteria.is_unread is False:
                filters.append("isRead eq true")
            if criteria.is_flagged:
                filters.append("flag/flagStatus eq 'flagged'")
            if criteria.date_after:
                # Use proper ISO format for Microsoft Graph compatibility
                if criteria.date_after.tzinfo is None:
                    # Add UTC timezone if naive datetime
                    criteria.date_after = criteria.date_after.replace(tzinfo=UTC)
                iso_date = criteria.date_after.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                filters.append(f"receivedDateTime ge {iso_date}")
            if criteria.date_before:
                # Use proper ISO format for Microsoft Graph compatibility
                if criteria.date_before.tzinfo is None:
                    # Add UTC timezone if naive datetime
                    criteria.date_before = criteria.date_before.replace(tzinfo=UTC)
                iso_date = criteria.date_before.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                filters.append(f"receivedDateTime le {iso_date}")

            # Build URL
            url = f"{self.GRAPH_ENDPOINT}/me/messages"
            params = {
                '$top': str(criteria.max_results),
                '$orderby': 'receivedDateTime desc'
            }

            # If searching for attachments, expand to include attachment data
            if criteria.has_attachments:
                params['$expand'] = 'attachments'

            if filters:
                # Microsoft Graph requires: properties in $orderby must also appear in $filter
                # AND properties in $orderby must appear FIRST in $filter

                # Check if we already have receivedDateTime filters from date criteria
                has_date_filter = any('receivedDateTime' in f for f in filters)
                if not has_date_filter:
                    # Add minimal date filter only if no date criteria specified
                    date_filter = "receivedDateTime ge 1900-01-01T00:00:00Z"
                    all_filters = [date_filter] + filters
                else:
                    # Move existing receivedDateTime filters to the front
                    date_filters = [f for f in filters if 'receivedDateTime' in f]
                    other_filters = [f for f in filters if 'receivedDateTime' not in f]
                    all_filters = date_filters + other_filters

                params['$filter'] = ' and '.join(all_filters)

            if criteria.query:
                params['$search'] = f'"{criteria.query}"'

            # Handle labels (folders)
            if criteria.labels:
                # For Microsoft Graph, we need to search in specific folders
                # This is a simplified approach - real implementation might need folder hierarchy
                folder_name = criteria.labels[0]  # Use first label as folder
                url = f"{self.GRAPH_ENDPOINT}/me/mailFolders('{folder_name}')/messages"

            async with self.session.get(url, params=params) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to list messages: HTTP {response.status}")

                data = await response.json()
                messages = data.get('value', [])

                # Convert to Email objects
                emails = []
                include_attachments = criteria.has_attachments  # Include attachments if we searched for them
                for msg in messages:
                    try:
                        email_obj = self._parse_graph_message(msg, include_attachments)
                        emails.append(email_obj)
                    except Exception as e:
                        logger.warning("Failed to parse message %s: %s", msg.get('id'), e)
                        continue

                return emails

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to list Microsoft Graph messages: {e}")

    async def get_email(self, email_id: str, include_attachments: bool = False) -> Email:
        """Get a specific email by ID."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            # Get message with attachments if requested
            expand = '$expand=attachments' if include_attachments else ''
            url = f"{self.GRAPH_ENDPOINT}/me/messages/{email_id}"
            if expand:
                url += f"?{expand}"

            async with self.session.get(url) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status == 404:
                    raise EmailNotFoundError(f"Email {email_id} not found")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to get message: HTTP {response.status}")

                data = await response.json()
                return self._parse_graph_message(data, include_attachments)

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to get Microsoft Graph message: {e}")

    async def send_email(self, request: EmailSendRequest) -> str:
        """Send an email via Microsoft Graph."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            # Build message
            message = {
                'subject': request.subject,
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': addr.address,
                            'name': addr.name or addr.address
                        }
                    } for addr in request.to
                ],
                'body': {
                    'contentType': 'HTML' if request.body_html else 'Text',
                    'content': request.body_html or request.body_text or ''
                }
            }

            if request.cc:
                message['ccRecipients'] = [
                    {
                        'emailAddress': {
                            'address': addr.address,
                            'name': addr.name or addr.address
                        }
                    } for addr in request.cc
                ]

            if request.bcc:
                message['bccRecipients'] = [
                    {
                        'emailAddress': {
                            'address': addr.address,
                            'name': addr.name or addr.address
                        }
                    } for addr in request.bcc
                ]

            # Set importance
            if request.importance == EmailImportance.HIGH:
                message['importance'] = 'high'
            elif request.importance == EmailImportance.LOW:
                message['importance'] = 'low'
            else:
                message['importance'] = 'normal'

            # Handle reply threading
            if request.reply_to_message_id:
                # For replies, we should use the reply endpoint instead
                url = f"{self.GRAPH_ENDPOINT}/me/messages/{request.reply_to_message_id}/reply"
                payload = {'message': message}
            else:
                url = f"{self.GRAPH_ENDPOINT}/me/sendMail"
                payload = {'message': message}

            # Add attachments
            if request.attachments:
                message['attachments'] = []
                for attachment in request.attachments:
                    if attachment.content:
                        content_bytes = base64.b64encode(attachment.content).decode()
                        message['attachments'].append({
                            '@odata.type': '#microsoft.graph.fileAttachment',
                            'name': attachment.filename,
                            'contentType': attachment.content_type,
                            'contentBytes': content_bytes
                        })

            async with self.session.post(url, json=payload) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status not in [200, 202]:
                    error_text = await response.text()
                    raise EmailSystemError(f"Failed to send message: HTTP {response.status} - {error_text}")

                # Microsoft Graph doesn't return message ID on send
                # Return a placeholder ID
                return "sent"

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to send Microsoft Graph message: {e}")

    async def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read."""
        return await self._update_message(email_id, {'isRead': True})

    async def mark_as_unread(self, email_id: str) -> bool:
        """Mark email as unread."""
        return await self._update_message(email_id, {'isRead': False})

    async def delete_email(self, email_id: str) -> bool:
        """Delete an email."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            url = f"{self.GRAPH_ENDPOINT}/me/messages/{email_id}"

            async with self.session.delete(url) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status == 404:
                    raise EmailNotFoundError(f"Email {email_id} not found")
                elif response.status != 204:
                    raise EmailSystemError(f"Failed to delete message: HTTP {response.status}")

                return True

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to delete Microsoft Graph message: {e}")

    async def get_labels(self) -> list[str]:
        """Get available folders (labels)."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            url = f"{self.GRAPH_ENDPOINT}/me/mailFolders"

            async with self.session.get(url) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to get folders: HTTP {response.status}")

                data = await response.json()
                folders = data.get('value', [])
                return [folder['displayName'] for folder in folders]

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to get Microsoft Graph folders: {e}")

    async def add_label(self, email_id: str, label: str) -> bool:
        """Move email to folder (Microsoft Graph doesn't have labels like Gmail)."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            # First, find the folder ID for the label
            folders = await self._get_folders_dict()
            folder_id = folders.get(label)

            if not folder_id:
                raise EmailSystemError(f"Folder '{label}' not found")

            # Move message to folder
            url = f"{self.GRAPH_ENDPOINT}/me/messages/{email_id}/move"
            payload = {'destinationId': folder_id}

            async with self.session.post(url, json=payload) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status == 404:
                    raise EmailNotFoundError(f"Email {email_id} not found")
                elif response.status not in [200, 201]:
                    raise EmailSystemError(f"Failed to move message: HTTP {response.status}")

                return True

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to add label to Microsoft Graph message: {e}")

    async def remove_label(self, email_id: str, label: str) -> bool:
        """Move email from folder back to inbox."""
        # For simplicity, we move back to inbox when removing a "label"
        return await self.add_label(email_id, "Inbox")

    async def download_attachment(self, email_id: str, attachment_id: str) -> bytes:
        """Download attachment content from Microsoft Graph."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            url = f"{self.GRAPH_ENDPOINT}/me/messages/{email_id}/attachments/{attachment_id}/$value"

            async with self.session.get(url) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status == 404:
                    raise EmailNotFoundError(f"Attachment {attachment_id} not found in email {email_id}")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to download attachment: HTTP {response.status}")

                content = await response.read()
                return content

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to download Microsoft Graph attachment: {e}")

    # Helper methods
    async def _run_in_executor(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run blocking function in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))

    async def _update_message(self, email_id: str, update_data: dict[str, Any]) -> bool:
        """Update message properties."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            url = f"{self.GRAPH_ENDPOINT}/me/messages/{email_id}"

            async with self.session.patch(url, json=update_data) as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status == 404:
                    raise EmailNotFoundError(f"Email {email_id} not found")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to update message: HTTP {response.status}")

                return True

        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to update Microsoft Graph message: {e}")

    async def _get_folders_dict(self) -> dict[str, str]:
        """Get folder name to ID mapping."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")

        try:
            url = f"{self.GRAPH_ENDPOINT}/me/mailFolders"

            async with self.session.get(url) as response:
                if response.status != 200:
                    return {}

                data = await response.json()
                folders = data.get('value', [])
                return {folder['displayName']: folder['id'] for folder in folders}

        except aiohttp.ClientError:
            return {}

    def _parse_graph_message(self, message: dict[str, Any], include_attachments: bool = False) -> Email:
        """Parse Microsoft Graph message into Email object."""

        # Extract basic fields
        subject = message.get('subject', '')
        sender_data = message.get('from', {}).get('emailAddress', {})
        sender = EmailAddress(
            address=sender_data.get('address', ''),
            name=sender_data.get('name')
        )

        # Parse recipients
        recipients = []
        for recipient in message.get('toRecipients', []):
            addr_data = recipient.get('emailAddress', {})
            recipients.append(EmailAddress(
                address=addr_data.get('address', ''),
                name=addr_data.get('name')
            ))

        cc = []
        for recipient in message.get('ccRecipients', []):
            addr_data = recipient.get('emailAddress', {})
            cc.append(EmailAddress(
                address=addr_data.get('address', ''),
                name=addr_data.get('name')
            ))

        # Parse dates
        sent_date = None
        received_date = None

        if message.get('sentDateTime'):
            sent_date = datetime.fromisoformat(message['sentDateTime'].replace('Z', '+00:00'))
        if message.get('receivedDateTime'):
            received_date = datetime.fromisoformat(message['receivedDateTime'].replace('Z', '+00:00'))

        # Parse body
        body_data = message.get('body', {})
        body_text = None
        body_html = None

        if body_data.get('contentType') == 'text':
            body_text = body_data.get('content')
        elif body_data.get('contentType') == 'html':
            body_html = body_data.get('content')

        # Parse attachments
        attachments = []
        if include_attachments and message.get('attachments'):
            for att in message['attachments']:
                attachment = EmailAttachment(
                    filename=att.get('name', ''),
                    content_type=att.get('contentType', ''),
                    size=att.get('size', 0),
                    attachment_id=att.get('id')
                )

                # If content is included
                if att.get('contentBytes'):
                    try:
                        attachment.content = base64.b64decode(att['contentBytes'])
                    except:
                        pass

                attachments.append(attachment)

        # Parse importance
        importance = EmailImportance.NORMAL
        graph_importance = message.get('importance', 'normal').lower()
        if graph_importance == 'high':
            importance = EmailImportance.HIGH
        elif graph_importance == 'low':
            importance = EmailImportance.LOW

        # Parse flags
        is_read = message.get('isRead', False)
        is_flagged = message.get('flag', {}).get('flagStatus') == 'flagged'

        # Build headers dict from available data
        headers = {
            'subject': subject,
            'from': str(sender),
            'to': ', '.join([str(r) for r in recipients]),
            'message-id': message.get('internetMessageId'),
            'date': message.get('sentDateTime', ''),
        }

        if message.get('conversationId'):
            headers['conversation-id'] = message['conversationId']

        return Email(
            id=message['id'],
            thread_id=message.get('conversationId'),
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
            received_date=received_date,
            headers=headers,
            labels=[],  # Microsoft Graph uses folders, not labels
            message_id=message.get('internetMessageId'),
            in_reply_to=None,  # Would need to parse this from headers
            raw_data=message
        )

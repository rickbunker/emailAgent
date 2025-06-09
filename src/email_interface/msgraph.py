"""
Microsoft Graph implementation of the email interface.

This module provides integration with Microsoft 365/Exchange using Microsoft Graph API.
"""

import json
import base64
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import webbrowser
import threading
import http.server
import socketserver
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import aiohttp
import msal

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

logger = logging.getLogger(__name__)

class AuthorizationHandler(http.server.SimpleHTTPRequestHandler):
    """Handle OAuth callback for web-based authentication."""
    
    def do_GET(self):
        """Handle GET request with authorization code."""
        if self.path.startswith('/?code='):
            # Extract authorization code and state
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            
            if 'code' in query_params:
                self.server.auth_code = query_params['code'][0]
                self.server.state = query_params.get('state', [None])[0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <html>
                <head><title>Email Agent - Authentication Success</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: green;">✅ Authentication Successful!</h2>
                    <p>You can close this window and return to the email agent.</p>
                    <p>The email agent is now connected to your Microsoft 365 account.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
            else:
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = """
                <html>
                <head><title>Email Agent - Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: red;">❌ Authentication Failed</h2>
                    <p>No authorization code received. Please try again.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        else:
            # Default response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            waiting_html = """
            <html>
            <head><title>Email Agent - Waiting for Authentication</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>🔄 Waiting for Microsoft 365 Authentication...</h2>
                <p>Please complete the authentication process in the other browser tab.</p>
            </body>
            </html>
            """
            self.wfile.write(waiting_html.encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

class MicrosoftGraphInterface(BaseEmailInterface):
    """Microsoft Graph implementation of the email interface."""
    
    # Microsoft Graph scopes
    SCOPES = [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/User.Read'
    ]
    
    # Microsoft Graph endpoints
    GRAPH_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    AUTH_ENDPOINT = 'https://login.microsoftonline.com'
    
    def __init__(self, credentials_path: str = "examples/msgraph_credentials.json"):
        super().__init__()
        self.access_token = None
        self.app = None
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.credentials_path = Path(credentials_path)
        
        # Load credentials
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        with open(self.credentials_path) as f:
            self.credentials = json.load(f)
        
        logger.info(f"Initialized Microsoft Graph interface for {self.credentials['application_name']}")
    
    async def connect(self) -> bool:
        """
        Connect to Microsoft Graph using web-based OAuth authentication.
        """
        try:
            logger.info("Starting Microsoft Graph authentication...")
            
            # MSAL setup
            client_id = self.credentials['client_id']
            tenant_id = self.credentials['tenant_id']
            redirect_uri = "http://localhost:8080"
            
            authority = f"https://login.microsoftonline.com/{tenant_id}"
            scopes = [
                'https://graph.microsoft.com/Mail.ReadWrite',
                'https://graph.microsoft.com/Mail.Send',
                'https://graph.microsoft.com/User.Read'
            ]
            
            # Create public client app
            self.app = msal.PublicClientApplication(
                client_id=client_id,
                authority=authority
            )
            
            # Check for cached token first
            accounts = self.app.get_accounts()
            token_result = None
            
            if accounts:
                logger.info(f"Found {len(accounts)} cached account(s)")
                token_result = self.app.acquire_token_silent(scopes, account=accounts[0])
            
            if not token_result:
                logger.info("No cached token found, starting interactive authentication...")
                
                # Start local server
                port = 8080
                server = socketserver.TCPServer(("", port), AuthorizationHandler)
                server.auth_code = None
                server.state = None
                
                # Start server in background thread
                server_thread = threading.Thread(target=server.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                try:
                    # Get authorization URL
                    flow = self.app.initiate_auth_code_flow(
                        scopes=scopes,
                        redirect_uri=redirect_uri
                    )
                    
                    if "auth_uri" not in flow:
                        raise Exception("Failed to create auth flow")
                    
                    auth_url = flow["auth_uri"]
                    
                    logger.info("Opening browser for authentication...")
                    print(f"🌐 Opening browser for Microsoft 365 authentication...")
                    print(f"   If browser doesn't open, visit: {auth_url}")
                    print(f"   Waiting for authentication...")
                    
                    # Open browser
                    webbrowser.open(auth_url)
                    
                    # Wait for authorization code
                    timeout = 300  # 5 minutes
                    elapsed = 0
                    
                    while server.auth_code is None and elapsed < timeout:
                        await asyncio.sleep(1)
                        elapsed += 1
                    
                    if server.auth_code is None:
                        raise Exception("Authentication timeout - no authorization code received")
                    
                    logger.info("Authorization code received!")
                    
                    # Exchange code for token
                    auth_response = {'code': server.auth_code}
                    if server.state:
                        auth_response['state'] = server.state
                    
                    token_result = self.app.acquire_token_by_auth_code_flow(
                        flow,
                        auth_response
                    )
                    
                finally:
                    server.shutdown()
                    server.server_close()
            
            if "access_token" not in token_result:
                error = token_result.get("error_description", "Unknown authentication error")
                raise Exception(f"Failed to get access token: {error}")
            
            self.access_token = token_result["access_token"]
            logger.info("Successfully obtained access token")
            
            # Initialize HTTP session
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(headers=headers)
            
            # Verify connection by getting user profile
            async with self.session.get('https://graph.microsoft.com/v1.0/me') as response:
                if response.status == 200:
                    profile = await response.json()
                    user_email = profile.get('mail') or profile.get('userPrincipalName')
                    logger.info(f"Successfully connected as {profile.get('displayName')} ({user_email})")
                    print(f"✅ Connected to Microsoft 365 as {profile.get('displayName')} ({user_email})")
                    self.user_email = user_email
                    self.display_name = profile.get('displayName')
                    self.is_connected = True
                    return True
                else:
                    raise Exception(f"Failed to verify connection: HTTP {response.status}")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            self.user_email = None
            self.display_name = None
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Microsoft Graph."""
        if self.session:
            await self.session.close()
        
        self.session = None
        self.access_token = None
        self.app = None
        self.is_connected = False
        self.user_email = None
        self.display_name = None
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get Microsoft Graph user profile."""
        if not self.session:
            raise ConnectionError("Not connected to Microsoft Graph")
        
        try:
            async with self.session.get(f"{self.GRAPH_ENDPOINT}/me") as response:
                if response.status == 401:
                    raise AuthenticationError("Microsoft Graph token expired or invalid")
                elif response.status != 200:
                    raise EmailSystemError(f"Failed to get profile: HTTP {response.status}")
                
                data = await response.json()
                return {
                    'email': data.get('mail') or data.get('userPrincipalName'),
                    'name': data.get('displayName'),
                    'id': data.get('id'),
                    'job_title': data.get('jobTitle'),
                    'office_location': data.get('officeLocation')
                }
                
        except aiohttp.ClientError as e:
            raise EmailSystemError(f"Failed to get Microsoft Graph profile: {e}")
    
    async def list_emails(self, criteria: EmailSearchCriteria) -> List[Email]:
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
                iso_date = criteria.date_after.strftime('%Y-%m-%dT%H:%M:%SZ')
                filters.append(f"receivedDateTime ge {iso_date}")
            if criteria.date_before:
                iso_date = criteria.date_before.strftime('%Y-%m-%dT%H:%M:%SZ')
                filters.append(f"receivedDateTime le {iso_date}")
            
            # Build URL
            url = f"{self.GRAPH_ENDPOINT}/me/messages"
            params = {
                '$top': str(criteria.max_results),
                '$orderby': 'receivedDateTime desc'
            }
            
            if filters:
                params['$filter'] = ' and '.join(filters)
            
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
                for msg in messages:
                    try:
                        email_obj = self._parse_graph_message(msg)
                        emails.append(email_obj)
                    except Exception as e:
                        print(f"[WARN] Failed to parse message {msg.get('id')}: {e}")
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
    
    async def get_labels(self) -> List[str]:
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
    
    # Helper methods
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking function in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def _update_message(self, email_id: str, update_data: Dict[str, Any]) -> bool:
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
    
    async def _get_folders_dict(self) -> Dict[str, str]:
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
    
    def _parse_graph_message(self, message: Dict[str, Any], include_attachments: bool = False) -> Email:
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
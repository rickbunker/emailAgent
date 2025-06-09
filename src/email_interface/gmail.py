"""
Gmail implementation of the email interface.

This module provides integration with Gmail using the Google Workspace Gmail API.
Supports OAuth 2.0 authentication and full email management capabilities.

See: https://developers.google.com/workspace/gmail/api/guides
"""

import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json
import os
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

class GmailInterface(BaseEmailInterface):
    """Gmail implementation of the email interface."""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/contacts.readonly'  # Added for contacts access
    ]
    
    def __init__(self):
        super().__init__()
        self.service = None
        self.credentials = None
        self.executor = ThreadPoolExecutor(max_workers=4)  # For blocking API calls
    
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to Gmail using OAuth 2.0 credentials.
        
        Args:
            credentials: Dict containing one of:
                - 'credentials_file': Path to credentials.json file (for first-time auth)
                - 'token_file': Path to token.json file (for existing auth)
                - 'token_data': Direct token data dict
                
        Returns:
            bool: True if connection successful
        """
        try:
            creds = None
            
            # Try to load existing token
            if 'token_file' in credentials and os.path.exists(credentials['token_file']):
                creds = Credentials.from_authorized_user_file(credentials['token_file'], self.SCOPES)
            elif 'token_data' in credentials:
                creds = Credentials.from_authorized_user_info(credentials['token_data'], self.SCOPES)
            
            # If no valid credentials, do OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh expired token
                    await self._run_in_executor(creds.refresh, Request())
                else:
                    # Do full OAuth flow
                    if 'credentials_file' not in credentials:
                        raise AuthenticationError("No credentials file provided for initial authentication")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials['credentials_file'], self.SCOPES)
                    creds = await self._run_in_executor(flow.run_local_server, port=0)
                
                # Save token for future use
                if 'token_file' in credentials:
                    with open(credentials['token_file'], 'w') as token:
                        token.write(creds.to_json())
            
            # Build Gmail service
            self.credentials = creds
            self.service = await self._run_in_executor(build, 'gmail', 'v1', credentials=creds)
            
            # Get user profile
            profile = await self.get_profile()
            self.user_email = profile.get('email')
            self.display_name = profile.get('name')
            self.is_connected = True
            
            return True
            
        except Exception as e:
            raise AuthenticationError(f"Gmail authentication failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Gmail."""
        self.service = None
        self.credentials = None
        self.is_connected = False
        self.user_email = None
        self.display_name = None
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get Gmail user profile."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            # Get Gmail profile
            gmail_profile = await self._run_in_executor(
                self.service.users().getProfile(userId='me').execute
            )
            
            # Use email address as name (simple approach to avoid extra API calls)
            email = gmail_profile.get('emailAddress', '')
            name = email.split('@')[0] if email else 'User'
            
            return {
                'email': email,
                'name': name,
                'messages_total': gmail_profile.get('messagesTotal', 0),
                'threads_total': gmail_profile.get('threadsTotal', 0),
                'history_id': gmail_profile.get('historyId')
            }
            
        except HttpError as e:
            raise EmailSystemError(f"Failed to get Gmail profile: {e}")
    
    async def list_emails(self, criteria: EmailSearchCriteria) -> List[Email]:
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
                date_str = criteria.date_after.strftime('%Y/%m/%d')
                query_parts.append(f"after:{date_str}")
            if criteria.date_before:
                date_str = criteria.date_before.strftime('%Y/%m/%d')
                query_parts.append(f"before:{date_str}")
            for label in criteria.labels:
                query_parts.append(f"label:{label}")
            
            query = ' '.join(query_parts) if query_parts else None
            
            # Search for messages
            result = await self._run_in_executor(
                self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=criteria.max_results
                ).execute
            )
            
            messages = result.get('messages', [])
            
            # Get full message details
            emails = []
            for msg in messages:
                try:
                    email_obj = await self.get_email(msg['id'])
                    emails.append(email_obj)
                except Exception as e:
                    print(f"[WARN] Failed to get email {msg['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            raise EmailSystemError(f"Failed to list Gmail messages: {e}")
    
    async def get_email(self, email_id: str, include_attachments: bool = False) -> Email:
        """Get a specific email by ID."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            # Get message
            message = await self._run_in_executor(
                self.service.users().messages().get(
                    userId='me',
                    id=email_id,
                    format='full'
                ).execute
            )
            
            return await self._parse_gmail_message(message, include_attachments)
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found")
            raise EmailSystemError(f"Failed to get Gmail message: {e}")
    
    async def send_email(self, request: EmailSendRequest) -> str:
        """Send an email via Gmail."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            # Create message
            if request.body_html:
                message = MIMEMultipart('alternative')
                if request.body_text:
                    message.attach(MIMEText(request.body_text, 'plain'))
                message.attach(MIMEText(request.body_html, 'html'))
            else:
                message = MIMEText(request.body_text or '', 'plain')
            
            # Set headers
            message['to'] = ', '.join([addr.address for addr in request.to])
            message['subject'] = request.subject
            
            if request.cc:
                message['cc'] = ', '.join([addr.address for addr in request.cc])
            if request.bcc:
                message['bcc'] = ', '.join([addr.address for addr in request.bcc])
            
            # Handle reply threading
            if request.reply_to_message_id:
                message['In-Reply-To'] = request.reply_to_message_id
                message['References'] = request.reply_to_message_id
            
            # Add attachments
            if request.attachments:
                if not isinstance(message, MIMEMultipart):
                    # Convert to multipart
                    text_part = message
                    message = MIMEMultipart()
                    message.attach(text_part)
                    # Copy headers
                    for key, value in text_part.items():
                        if key.lower() not in ['content-type', 'content-transfer-encoding']:
                            message[key] = value
                
                for attachment in request.attachments:
                    if attachment.content:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.content)
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {attachment.filename}'
                        )
                        message.attach(part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            result = await self._run_in_executor(
                self.service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute
            )
            
            return result['id']
            
        except HttpError as e:
            raise EmailSystemError(f"Failed to send Gmail message: {e}")
    
    async def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read."""
        return await self._modify_labels(email_id, remove_labels=['UNREAD'])
    
    async def mark_as_unread(self, email_id: str) -> bool:
        """Mark email as unread."""
        return await self._modify_labels(email_id, add_labels=['UNREAD'])
    
    async def delete_email(self, email_id: str) -> bool:
        """Delete an email (move to trash)."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            await self._run_in_executor(
                self.service.users().messages().trash(
                    userId='me',
                    id=email_id
                ).execute
            )
            return True
        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found")
            raise EmailSystemError(f"Failed to delete Gmail message: {e}")
    
    async def get_labels(self) -> List[str]:
        """Get all Gmail labels."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            result = await self._run_in_executor(
                self.service.users().labels().list(userId='me').execute
            )
            
            labels = result.get('labels', [])
            return [label['name'] for label in labels]
            
        except HttpError as e:
            raise EmailSystemError(f"Failed to get Gmail labels: {e}")
    
    async def add_label(self, email_id: str, label: str) -> bool:
        """Add a label to an email."""
        return await self._modify_labels(email_id, add_labels=[label])
    
    async def remove_label(self, email_id: str, label: str) -> bool:
        """Remove a label from an email."""
        return await self._modify_labels(email_id, remove_labels=[label])
    
    async def get_contacts(self) -> List[Dict[str, Any]]:
        """Get all Gmail contacts."""
        if not self.credentials:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            # Build People API service
            people_service = await self._run_in_executor(
                build, 'people', 'v1', credentials=self.credentials
            )
            
            contacts = []
            next_page_token = None
            page_count = 0
            
            # Fetch all contacts using pagination
            while True:
                page_count += 1
                print(f"      Fetching contacts page {page_count}...")
                
                # Build request parameters
                request_params = {
                    'resourceName': 'people/me',
                    'personFields': 'names,emailAddresses',
                    'pageSize': 1000  # Maximum allowed per page
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                # Get contacts page
                results = await self._run_in_executor(
                    people_service.people().connections().list(**request_params).execute
                )
                
                connections = results.get('connections', [])
                print(f"      Page {page_count}: Found {len(connections)} contacts")
                
                # Process contacts from this page
                for person in connections:
                    contact = {
                        'name': '',
                        'emails': []
                    }
                    
                    # Get name
                    names = person.get('names', [])
                    if names:
                        contact['name'] = names[0].get('displayName', '')
                    
                    # Get email addresses
                    emails = person.get('emailAddresses', [])
                    for email in emails:
                        email_addr = email.get('value', '').lower()
                        if email_addr:
                            contact['emails'].append(email_addr)
                    
                    # Only add contacts that have email addresses
                    if contact['emails']:
                        contacts.append(contact)
                
                # Check if there are more pages
                next_page_token = results.get('nextPageToken')
                if not next_page_token:
                    break
                
                # Safety limit to prevent infinite loops
                if page_count > 10:
                    print(f"      Warning: Stopped at page {page_count} to prevent infinite loop")
                    break
            
            print(f"      ✅ Total contacts with emails: {len(contacts)} (from {page_count} pages)")
            return contacts
            
        except Exception as e:
            print(f"Warning: Could not fetch contacts: {e}")
            return []
    
    # Helper methods
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking function in thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: func(*args, **kwargs))
    
    async def _modify_labels(self, email_id: str, add_labels: List[str] = None, remove_labels: List[str] = None) -> bool:
        """Modify labels on an email."""
        if not self.service:
            raise ConnectionError("Not connected to Gmail")
        
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels
            
            await self._run_in_executor(
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body=body
                ).execute
            )
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                raise EmailNotFoundError(f"Email {email_id} not found")
            raise EmailSystemError(f"Failed to modify Gmail message labels: {e}")
    
    async def _parse_gmail_message(self, message: Dict[str, Any], include_attachments: bool = False) -> Email:
        """Parse Gmail API message into Email object."""
        
        headers = {}
        for header in message['payload'].get('headers', []):
            headers[header['name'].lower()] = header['value']
        
        # Extract basic fields
        subject = headers.get('subject', '')
        sender = self._parse_email_address(headers.get('from', ''))
        message_id = headers.get('message-id')
        in_reply_to = headers.get('in-reply-to')
        
        # Parse recipients
        recipients = []
        if 'to' in headers:
            for addr in headers['to'].split(','):
                recipients.append(self._parse_email_address(addr.strip()))
        
        cc = []
        if 'cc' in headers:
            for addr in headers['cc'].split(','):
                cc.append(self._parse_email_address(addr.strip()))
        
        # Parse dates
        sent_date = None
        if 'date' in headers:
            try:
                sent_date = email.utils.parsedate_to_datetime(headers['date'])
            except:
                pass
        
        # Parse body
        body_text, body_html = await self._extract_body(message['payload'])
        
        # Parse attachments
        attachments = []
        if include_attachments:
            attachments = await self._extract_attachments(message['payload'], message['id'])
        
        # Determine importance
        importance = EmailImportance.NORMAL
        priority = headers.get('x-priority', headers.get('priority', ''))
        if priority in ['1', 'high']:
            importance = EmailImportance.HIGH
        elif priority in ['5', 'low']:
            importance = EmailImportance.LOW
        
        # Parse labels and flags
        labels = []
        is_read = 'UNREAD' not in message.get('labelIds', [])
        is_flagged = 'STARRED' in message.get('labelIds', [])
        
        for label_id in message.get('labelIds', []):
            if label_id not in ['UNREAD', 'STARRED', 'IMPORTANT']:
                labels.append(label_id)
        
        return Email(
            id=message['id'],
            thread_id=message.get('threadId'),
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
            raw_data=message
        )
    
    async def _extract_body(self, payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """Extract text and HTML body from Gmail message payload."""
        body_text = None
        body_html = None
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body_text = await self._decode_body_data(part['body'])
                elif part['mimeType'] == 'text/html':
                    body_html = await self._decode_body_data(part['body'])
                elif part['mimeType'].startswith('multipart/'):
                    # Nested multipart
                    nested_text, nested_html = await self._extract_body(part)
                    if nested_text:
                        body_text = nested_text
                    if nested_html:
                        body_html = nested_html
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                body_text = await self._decode_body_data(payload['body'])
            elif payload['mimeType'] == 'text/html':
                body_html = await self._decode_body_data(payload['body'])
        
        return body_text, body_html
    
    async def _decode_body_data(self, body_data: Dict[str, Any]) -> Optional[str]:
        """Decode Gmail message body data."""
        if 'data' not in body_data:
            return None
        
        try:
            data = body_data['data']
            # Gmail uses URL-safe base64 encoding
            decoded = base64.urlsafe_b64decode(data + '===')  # Add padding
            return decoded.decode('utf-8')
        except Exception as e:
            print(f"[WARN] Failed to decode body data: {e}")
            return None
    
    async def _extract_attachments(self, payload: Dict[str, Any], message_id: str) -> List[EmailAttachment]:
        """Extract attachments from Gmail message."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if 'filename' in part and part['filename']:
                    # This is an attachment
                    attachment = EmailAttachment(
                        filename=part['filename'],
                        content_type=part['mimeType'],
                        size=part['body'].get('size', 0),
                        attachment_id=part['body'].get('attachmentId')
                    )
                    
                    # Optionally load content
                    if part['body'].get('attachmentId'):
                        try:
                            att_data = await self._run_in_executor(
                                self.service.users().messages().attachments().get(
                                    userId='me',
                                    messageId=message_id,
                                    id=part['body']['attachmentId']
                                ).execute
                            )
                            attachment.content = base64.urlsafe_b64decode(att_data['data'])
                        except Exception as e:
                            print(f"[WARN] Failed to load attachment content: {e}")
                    
                    attachments.append(attachment)
        
        return attachments 
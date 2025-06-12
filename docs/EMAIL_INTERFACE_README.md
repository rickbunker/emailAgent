# Email Interface Layer

A unified interface for connecting to multiple email systems in the Email Agent project.

## 🎯 **Overview**

The Email Interface Layer provides a clean, consistent API for working with different email systems:

- **Gmail** - Google's email service via Gmail API
- **Microsoft 365/Exchange** - Microsoft's email services via Microsoft Graph API
- **Extensible** - Easy to add new email systems (IMAP, POP3, etc.)

## 🏗️ **Architecture**

```
📧 Email Interface Layer
├── BaseEmailInterface (Abstract)
│   ├── 📋 Common Operations
│   ├── 🔍 Search & Filter
│   ├── ✉️ Send & Receive
│   └── 🏷️ Labels & Folders
├── GmailInterface
│   ├── 🔐 OAuth 2.0 Auth
│   ├── 📬 Gmail API
│   └── 🏷️ Label Management
├── MicrosoftGraphInterface
│   ├── 🔐 Azure AD Auth
│   ├── 📬 Graph API
│   └── 📁 Folder Management
└── EmailInterfaceFactory
    ├── 🏭 Easy Creation
    ├── ⚙️ Config-based Setup
    └── 📋 Templates
```

## 🚀 **Quick Start**

### 1. **Factory Pattern (Recommended)**

```python
from email_interface import EmailInterfaceFactory, EmailSearchCriteria

# Create interface
gmail = EmailInterfaceFactory.create('gmail')

# Connect with credentials
credentials = {
    'credentials_file': 'path/to/credentials.json',
    'token_file': 'path/to/token.json'
}
await gmail.connect(credentials)

# List recent emails
criteria = EmailSearchCriteria(max_results=10, is_unread=True)
emails = await gmail.list_emails(criteria)

# Get profile
profile = await gmail.get_profile()
print(f"Connected as: {profile['name']} ({profile['email']})")

# Disconnect
await gmail.disconnect()
```

### 2. **Direct Instantiation**

```python
from email_interface import GmailInterface, MicrosoftGraphInterface

# Gmail
gmail = GmailInterface()
await gmail.connect({'credentials_file': 'creds.json'})

# Microsoft Graph
msgraph = MicrosoftGraphInterface()
await msgraph.connect({'client_id': 'your-client-id'})
```

## 📋 **Supported Email Systems**

| System | Type | Authentication | Status |
|--------|------|----------------|--------|
| Gmail | `gmail` | OAuth 2.0 | ✅ Ready |
| Microsoft 365 | `microsoft_graph` | Azure AD | ✅ Ready |
| Outlook | `outlook` | Azure AD (alias) | ✅ Ready |
| Office 365 | `office365` | Azure AD (alias) | ✅ Ready |

## 🔐 **Authentication Setup**

### **Gmail Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Gmail API
3. Create OAuth 2.0 credentials
4. Download `credentials.json`

```python
credentials = {
    'credentials_file': 'path/to/credentials.json',  # Required
    'token_file': 'path/to/token.json'              # Optional
}
```

### **Microsoft Graph Setup**

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register an application in Azure AD
3. Configure API permissions for Microsoft Graph
4. Get client ID (and optionally client secret)

```python
credentials = {
    'client_id': 'your-app-client-id',        # Required
    'client_secret': 'your-client-secret',    # Optional (public clients)
    'tenant_id': 'your-tenant-id',           # Optional (default: 'common')
    'redirect_uri': 'http://localhost:8080'   # Optional
}
```

## 📨 **Core Operations**

### **Email Listing & Search**

```python
from email_interface import EmailSearchCriteria
from datetime import datetime, timedelta

# Basic search
criteria = EmailSearchCriteria(
    max_results=50,
    is_unread=True,
    has_attachments=False
)

# search
criteria = EmailSearchCriteria(
    query="important meeting",
    sender="boss@company.com",
    subject="project update",
    date_after=datetime.now() - timedelta(days=7),
    labels=["Important"]
)

emails = await interface.list_emails(criteria)
```

### **Email Reading**

```python
# Get email by ID
email = await interface.get_email('email-id', include_attachments=True)

print(f"From: {email.sender.name} <{email.sender.address}>")
print(f"Subject: {email.subject}")
print(f"Date: {email.sent_date}")
print(f"Body: {email.body_text or email.body_html}")

# Check attachments
for attachment in email.attachments:
    print(f"Attachment: {attachment.filename} ({attachment.size} bytes)")
```

### **Email Sending**

```python
from email_interface import EmailSendRequest, EmailAddress, EmailImportance

# Compose email
request = EmailSendRequest(
    to=[EmailAddress("user@example.com", "John Doe")],
    cc=[EmailAddress("manager@example.com")],
    subject="Project Update",
    body_html="<h1>Weekly Report</h1><p>Progress summary...</p>",
    body_text="Weekly Report\n\nProgress summary...",
    importance=EmailImportance.HIGH
)

# Send
message_id = await interface.send_email(request)
print(f"Email sent: {message_id}")
```

### **Email Management**

```python
# Mark as read/unread
await interface.mark_as_read('email-id')
await interface.mark_as_unread('email-id')

# Delete email
await interface.delete_email('email-id')

# Label/folder management
labels = await interface.get_labels()
await interface.add_label('email-id', 'Important')
await interface.remove_label('email-id', 'Spam')
```

## 🔍 **Search Capabilities**

The `EmailSearchCriteria` class provides filtering:

```python
criteria = EmailSearchCriteria(
    query="quarterly report",           # Free text search
    sender="finance@company.com",       # Specific sender
    recipient="team@company.com",       # Specific recipient
    subject="Q4 2024",                 # Subject contains
    has_attachments=True,              # Must have attachments
    is_unread=False,                   # Read emails only
    is_flagged=True,                   # Flagged/starred emails
    date_after=datetime(2024, 1, 1),   # After date
    date_before=datetime(2024, 12, 31), # Before date
    labels=["Work", "Important"],       # Specific labels/folders
    max_results=100                     # Limit results
)
```

## 🏷️ **Labels vs Folders**

- **Gmail**: Uses labels (can have multiple per email)
- **Microsoft Graph**: Uses folders (email in one folder)
- **Interface**: Abstracts both as "labels" for consistency

## ⚡ **Async/Await Support**

All operations are async for optimal performance:

```python
import asyncio

async def main():
    interface = EmailInterfaceFactory.create('gmail')
    await interface.connect(credentials)

    # Concurrent operations
    profile_task = interface.get_profile()
    emails_task = interface.list_emails(criteria)
    labels_task = interface.get_labels()

    profile, emails, labels = await asyncio.gather(
        profile_task, emails_task, labels_task
    )

    await interface.disconnect()

asyncio.run(main())
```

## 🛠️ **Error Handling**

```python
from email_interface import (
    EmailSystemError,
    AuthenticationError,
    ConnectionError,
    PermissionError,
    EmailNotFoundError
)

try:
    await interface.connect(credentials)
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except EmailSystemError as e:
    print(f"Email system error: {e}")
```

## 📊 **Email Data Model**

```python
@dataclass
class Email:
    id: str                              # Unique email ID
    thread_id: Optional[str]             # Conversation thread
    subject: str                         # Email subject
    sender: EmailAddress                 # Sender info
    recipients: List[EmailAddress]       # To recipients
    cc: List[EmailAddress]               # CC recipients
    bcc: List[EmailAddress]              # BCC recipients
    body_text: Optional[str]             # Plain text body
    body_html: Optional[str]             # HTML body
    attachments: List[EmailAttachment]   # File attachments
    importance: EmailImportance          # LOW/NORMAL/HIGH
    is_read: bool                        # Read status
    is_flagged: bool                     # Flagged/starred
    sent_date: Optional[datetime]        # When sent
    received_date: Optional[datetime]    # When received
    headers: Dict[str, str]              # Email headers
    labels: List[str]                    # Labels/folders
    message_id: Optional[str]            # RFC message ID
    in_reply_to: Optional[str]           # Reply reference
    raw_data: Optional[Dict[str, Any]]   # Original API data
```

## 🔧 **Configuration Examples**

### **Environment Variables**

```bash
# Gmail
GMAIL_CREDENTIALS_FILE=/path/to/credentials.json
GMAIL_TOKEN_FILE=/path/to/token.json

# Microsoft Graph
MSGRAPH_CLIENT_ID=your-client-id
MSGRAPH_CLIENT_SECRET=your-client-secret
MSGRAPH_TENANT_ID=your-tenant-id
```

### **Config File (JSON)**

```json
{
  "email_systems": {
    "primary": {
      "type": "gmail",
      "credentials": {
        "credentials_file": "config/gmail_credentials.json",
        "token_file": "config/gmail_token.json"
      }
    },
    "secondary": {
      "type": "microsoft_graph",
      "credentials": {
        "client_id": "12345678-1234-1234-1234-123456789012",
        "tenant_id": "common"
      }
    }
  }
}
```

## 🧪 **Testing**

```bash
# Run factory demo
python examples/email_demo.py --system factory

# Test Gmail (requires credentials)
python examples/email_demo.py --system gmail

# Test Microsoft Graph (requires app registration)
python examples/email_demo.py --system microsoft_graph
```

## 🔮 **Future Enhancements**

- **IMAP/POP3 Support** - Generic email server support
- **Exchange Server** - On-premises Exchange integration
- **Email Threading** - conversation management
- **Bulk Operations** - Batch email processing
- **Real-time Updates** - Webhook/push notifications
- **Caching Layer** - Performance optimization
- **Rate Limiting** - API quota management

## 📁 **Project Structure**

```
src/email_interface/
├── __init__.py          # Package exports
├── base.py              # Abstract interface & data models
├── gmail.py             # Gmail implementation
├── msgraph.py           # Microsoft Graph implementation
├── factory.py           # Interface factory
examples/
├── email_demo.py        # Usage demonstrations
requirements.txt         # Dependencies
```

## 🤝 **Integration with Email Agent**

This interface layer plugs seamlessly into the Email Agent's architecture:

- **Spam Detection**: Analyze emails from any system
- **Contact Extraction**: Extract contacts from real emails
- **Memory System**: Store email interactions in Qdrant
- **Agent Workflows**: Process emails with LangGraph

## 💡 **Best Practices**

1. **Always use async/await** for all operations
2. **Handle connection errors** gracefully
3. **Disconnect when done** to free resources
4. **Use search criteria** to limit API calls
5. **Cache credentials** securely
6. **Respect rate limits** of email APIs
7. **Test with small batches** first

---

Ready to connect your Email Agent to real email systems! 🚀

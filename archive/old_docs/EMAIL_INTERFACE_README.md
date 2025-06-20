# Email Interface Layer

A unified interface for connecting to multiple email systems in the **Asset Document Processing Agent** project.

## 🎯 **Overview**

The Email Interface Layer provides a consistent API for processing emails containing private market investment documents from different email systems:

- **Gmail** - Google's email service via Gmail API
- **Microsoft 365/Exchange** - Microsoft's email services via Microsoft Graph API
- **Asset-Focused** - Optimized for document extraction and classification
- **Memory Integration** - Connects with procedural memory for learning
- **Extensible** - Easy to add new email systems (IMAP, Exchange, etc.)

## 🏗️ **System Architecture**

```
📧 Asset Document Email Processing
├── Email Interface Layer
│   ├── BaseEmailInterface (Abstract)
│   │   ├── 📋 Document Extraction
│   │   ├── 🔍 Asset-Related Search
│   │   ├── ✉️ Sender Recognition
│   │   └── 🏷️ Email Organization
│   ├── GmailInterface
│   │   ├── 🔐 OAuth 2.0 Auth
│   │   ├── 📬 Gmail API
│   │   └── 🏷️ Label Management
│   ├── MicrosoftGraphInterface
│   │   ├── 🔐 Azure AD Auth
│   │   ├── 📬 Graph API
│   │   └── 📁 Folder Management
│   └── EmailInterfaceFactory
│       ├── 🏭 Configuration-based Creation
│       ├── ⚙️ Credential Management
│       └── 🔄 Connection Pooling
├── Asset Document Agent
│   ├── 🧠 Memory-Driven Classification
│   ├── 📄 Document Processing
│   ├── 🎯 Asset Matching
│   └── 👥 Human Review Queue
└── Web Interface
    ├── 📊 Processing Dashboard
    ├── 🔍 Document Browser
    ├── ✋ Human Review System
    └── 📈 Learning Analytics
```

## 🚀 **Quick Start**

### 1. **Asset Document Processing (Recommended)**

```python
from src.email_interface import EmailInterfaceFactory
from src.agents.asset_document_agent import AssetDocumentAgent
from src.utils.config import config

# Create email interface
email_interface = EmailInterfaceFactory.create('gmail')

# Connect with credentials
credentials = {
    'credentials_file': config.gmail_credentials_file,
    'token_file': config.gmail_token_file
}
await email_interface.connect(credentials)

# Initialize asset document agent
agent = AssetDocumentAgent()
await agent.initialize_collections()

# Process emails with attachments
criteria = EmailSearchCriteria(
    has_attachments=True,
    is_unread=True,
    max_results=50
)

emails = await email_interface.list_emails(criteria)

for email in emails:
    if email.attachments:
        for attachment in email.attachments:
            # Process each attachment through the agent
            attachment_data = {
                'filename': attachment.filename,
                'content': attachment.content
            }

            email_data = {
                'sender_email': email.sender.address,
                'subject': email.subject,
                'body': email.body_text or email.body_html,
                'sent_date': email.sent_date
            }

            # Enhanced processing with memory-driven classification
            result = await agent.enhanced_process_attachment(
                attachment_data, email_data
            )

            if result.status == ProcessingStatus.SUCCESS:
                print(f"✅ Processed: {attachment.filename}")
                print(f"   Category: {result.document_category}")
                print(f"   Confidence: {result.confidence:.3f}")
                if result.matched_asset_id:
                    print(f"   Asset: {result.matched_asset_id[:8]}")

await email_interface.disconnect()
```

### 2. **Web UI Integration**

```python
# Start the web interface
python -m src.web_ui.app

# Navigate to http://localhost:5000
# - Configure email connections
# - Process mailboxes automatically
# - Review classifications
# - Train the learning system
```

## 📋 **Supported Email Systems**

| System | Type | Authentication | Asset Processing | Status |
|--------|------|----------------|------------------|--------|
| Gmail | `gmail` | OAuth 2.0 | ✅ Full Support | ✅ Ready |
| Microsoft 365 | `microsoft_graph` | Azure AD | ✅ Full Support | ✅ Ready |
| Outlook.com | `outlook` | Azure AD (alias) | ✅ Full Support | ✅ Ready |
| Office 365 | `office365` | Azure AD (alias) | ✅ Full Support | ✅ Ready |

## 🔐 **Authentication Setup**

### **Gmail for Asset Documents**

**Required Scopes for Document Processing:**
- `https://www.googleapis.com/auth/gmail.readonly` - Read emails and attachments
- `https://www.googleapis.com/auth/gmail.modify` - Mark processed emails
- `https://www.googleapis.com/auth/gmail.send` - Send processing notifications

```python
# Setup in Google Cloud Console
# 1. Enable Gmail API
# 2. Create OAuth 2.0 credentials
# 3. Add authorized redirect URI: http://localhost:8080
# 4. Download credentials.json

credentials = {
    'credentials_file': 'config/gmail_credentials.json',
    'token_file': 'config/gmail_token.json',
    'scopes': [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.send'
    ]
}
```

### **Microsoft Graph for Asset Documents**

**Required Permissions for Document Processing:**
- `Mail.ReadWrite` - Read and process emails with attachments
- `Mail.Send` - Send processing notifications
- `User.Read` - Access user profile information
- `Contacts.Read` - Match senders to known contacts

```python
# Setup in Azure Portal
# 1. Register application in Azure AD
# 2. Configure API permissions for Microsoft Graph
# 3. Set redirect URI: http://localhost:8080
# 4. Enable public client flows

credentials = {
    'client_id': 'your-app-client-id',
    'tenant_id': 'your-tenant-id',  # or 'common' for personal accounts
    'redirect_uri': 'http://localhost:8080',
    'scopes': [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/User.Read',
        'https://graph.microsoft.com/Contacts.Read'
    ]
}
```

## 📨 **Asset-Focused Operations**

### **Document-Bearing Email Search**

```python
from src.email_interface import EmailSearchCriteria
from datetime import datetime, timedelta

# Search for emails with attachments (potential asset documents)
criteria = EmailSearchCriteria(
    has_attachments=True,
    date_after=datetime.now() - timedelta(days=30),
    sender_contains=["fundmanager", "servicer", "borrower"],
    subject_contains=["rent roll", "financial", "loan", "report"],
    attachment_types=[".pdf", ".xlsx", ".xls", ".docx"],
    max_results=100
)

emails = await interface.list_emails(criteria)
```

### **Asset Document Processing Pipeline**

```python
# Complete processing pipeline
async def process_asset_emails(interface, agent):
    criteria = EmailSearchCriteria(
        has_attachments=True,
        is_unread=True,
        max_results=20
    )

    emails = await interface.list_emails(criteria)
    processed_count = 0

    for email in emails:
        print(f"Processing email from: {email.sender.address}")
        print(f"Subject: {email.subject}")

        # Process each attachment
        for attachment in email.attachments:
            attachment_data = {
                'filename': attachment.filename,
                'content': await interface.get_attachment_content(
                    email.id, attachment.id
                )
            }

            email_data = {
                'sender_email': email.sender.address,
                'subject': email.subject,
                'body': email.body_text or email.body_html,
                'sent_date': email.sent_date
            }

            # Memory-driven processing
            result = await agent.enhanced_process_attachment(
                attachment_data, email_data
            )

            # Handle results based on confidence
            if result.confidence_level == ConfidenceLevel.HIGH:
                # Auto-processed successfully
                await interface.add_label(email.id, "Processed")
                processed_count += 1

            elif result.confidence_level == ConfidenceLevel.VERY_LOW:
                # Needs human review
                await interface.add_label(email.id, "Needs Review")

            # Save processed attachment
            if result.matched_asset_id:
                await agent.save_attachment_to_asset_folder(
                    attachment_data['content'],
                    attachment.filename,
                    result,
                    result.matched_asset_id
                )

        # Mark email as processed
        await interface.mark_as_read(email.id)

    return processed_count
```

### **Sender-Asset Mapping**

```python
# Learn sender-asset relationships
async def analyze_sender_patterns(agent, sender_email):
    # Get historical data for this sender
    sender_assets = await agent.get_sender_assets(sender_email)

    if sender_assets:
        print(f"Known sender: {sender_email}")
        for asset_info in sender_assets:
            print(f"  - Asset: {asset_info['asset_id']}")
            print(f"    Confidence: {asset_info['confidence']:.3f}")
    else:
        print(f"New sender: {sender_email}")
        # This sender will be learned from successful classifications
```

## 🔍 **Asset-Focused Search Capabilities**

```python
# Advanced search for asset-related emails
criteria = EmailSearchCriteria(
    # Document-specific filters
    has_attachments=True,
    attachment_types=[".pdf", ".xlsx", ".xls", ".docx", ".pptx"],
    attachment_size_min=1024,  # Skip tiny files
    attachment_size_max=25*1024*1024,  # 25MB limit

    # Asset-related content
    subject_contains=["rent roll", "financial", "loan", "property"],
    body_contains=["quarterly", "monthly", "report", "statement"],

    # Sender patterns
    sender_domains=["fundmanager.com", "servicer.com", "bank.com"],
    sender_contains=["finance", "accounting", "investor"],

    # Time-based filtering
    date_after=datetime.now() - timedelta(days=90),
    is_unread=False,  # Include processed emails for training

    # Efficiency
    max_results=200,
    sort_by="date_desc"
)

emails = await interface.list_emails(criteria)
```

## 🏷️ **Email Organization for Asset Management**

```python
# Standard labels for asset document processing
ASSET_LABELS = {
    'PROCESSED': 'Asset-Processed',
    'HIGH_CONFIDENCE': 'Asset-Auto-Processed',
    'NEEDS_REVIEW': 'Asset-Needs-Review',
    'QUARANTINED': 'Asset-Quarantined',
    'DUPLICATE': 'Asset-Duplicate',
    'NON_ASSET': 'Non-Asset-Email'
}

# Apply labels after processing
async def apply_processing_labels(interface, email_id, result):
    if result.status == ProcessingStatus.SUCCESS:
        if result.confidence_level == ConfidenceLevel.HIGH:
            await interface.add_label(email_id, ASSET_LABELS['HIGH_CONFIDENCE'])
        elif result.confidence_level == ConfidenceLevel.VERY_LOW:
            await interface.add_label(email_id, ASSET_LABELS['NEEDS_REVIEW'])

        await interface.add_label(email_id, ASSET_LABELS['PROCESSED'])

    elif result.status == ProcessingStatus.QUARANTINED:
        await interface.add_label(email_id, ASSET_LABELS['QUARANTINED'])

    elif result.status == ProcessingStatus.DUPLICATE:
        await interface.add_label(email_id, ASSET_LABELS['DUPLICATE'])
```

## ⚡ **Parallel Processing for Large Mailboxes**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_mailbox_parallel(interface, agent, max_concurrent=5):
    """Process emails in parallel for better performance."""

    criteria = EmailSearchCriteria(
        has_attachments=True,
        max_results=100
    )

    emails = await interface.list_emails(criteria)

    # Create semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_single_email(email):
        async with semaphore:
            return await process_email_attachments(email, agent)

    # Process emails concurrently
    tasks = [process_single_email(email) for email in emails]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Summarize results
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful

    print(f"Processed {successful} emails successfully, {failed} failed")
    return results
```

## 🛠️ **Error Handling for Asset Processing**

```python
from src.email_interface import (
    EmailSystemError,
    AuthenticationError,
    ConnectionError,
    PermissionError,
    EmailNotFoundError
)

async def robust_email_processing(interface, agent):
    try:
        await interface.connect(credentials)

        # Process emails with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                results = await process_asset_emails(interface, agent)
                break
            except EmailSystemError as e:
                if attempt < max_retries - 1:
                    print(f"Retry {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Please check your credentials and permissions")

    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print("Please check your internet connection")

    except PermissionError as e:
        print(f"Permission denied: {e}")
        print("Please check your API permissions and scopes")

    finally:
        await interface.disconnect()
```

## 📊 **Asset Email Data Model**

```python
@dataclass
class AssetEmail:
    # Standard email fields
    id: str
    subject: str
    sender: EmailAddress
    body_text: Optional[str]
    body_html: Optional[str]
    sent_date: Optional[datetime]

    # Asset-specific fields
    attachments: List[AssetAttachment]
    potential_assets: List[str]  # Asset IDs that might match
    processing_status: ProcessingStatus
    confidence_scores: Dict[str, float]
    classification_results: Dict[str, Any]

    # Learning data
    sender_history: Optional[Dict[str, Any]]
    learned_patterns: List[str]
    human_feedback: Optional[Dict[str, Any]]

@dataclass
class AssetAttachment:
    id: str
    filename: str
    size: int
    content_type: str

    # Asset processing results
    document_category: Optional[DocumentCategory]
    matched_asset_id: Optional[str]
    confidence_level: Optional[ConfidenceLevel]
    file_path: Optional[Path]
    processing_metadata: Dict[str, Any]
```

## 🔧 **Configuration for Asset Processing**

### **Environment Variables**

```bash
# Email interface configuration
GMAIL_CREDENTIALS_FILE=/path/to/gmail_credentials.json
GMAIL_TOKEN_FILE=/path/to/gmail_token.json

MSGRAPH_CLIENT_ID=your-client-id
MSGRAPH_TENANT_ID=your-tenant-id
MSGRAPH_REDIRECT_URI=http://localhost:8080

# Asset processing configuration
BASE_ASSETS_PATH=./assets
MAX_ATTACHMENT_SIZE_MB=25
LOW_CONFIDENCE_THRESHOLD=0.4

# Qdrant vector database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Security
CLAMAV_ENABLED=true
```

### **YAML Configuration**

```yaml
email_interface:
  gmail:
    credentials_file: "config/gmail_credentials.json"
    token_file: "config/gmail_token.json"
    scopes:
      - "https://www.googleapis.com/auth/gmail.readonly"
      - "https://www.googleapis.com/auth/gmail.modify"

  msgraph:
    client_id: "${MSGRAPH_CLIENT_ID}"
    tenant_id: "${MSGRAPH_TENANT_ID}"
    redirect_uri: "http://localhost:8080"

asset_processing:
  base_assets_path: "./assets"
  max_attachment_size_mb: 25
  allowed_extensions: [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".pptx"]
  low_confidence_threshold: 0.4

  # Parallel processing
  max_concurrent_emails: 5
  max_concurrent_attachments: 10
  batch_size: 20

memory:
  auto_learning_threshold: 0.75
  similarity_threshold: 0.8
  pattern_retention_days: 365

security:
  clamav_enabled: true
  quarantine_path: "./quarantine"
```

## 🧪 **Testing Asset Processing**

```bash
# Test email interface connections
python -m src.email_interface.test_connections

# Test document processing pipeline
python -m src.agents.test_asset_processing

# Run web interface for interactive testing
python -m src.web_ui.app

# Process specific mailbox
python -m scripts.process_mailbox --interface gmail --max-emails 10
```

## 🔮 **Advanced Features**

### **Memory-Driven Learning**

```python
# Learn from successful classifications
async def learn_from_processing(agent, email, attachment, result):
    if result.confidence_level == ConfidenceLevel.HIGH:
        # Auto-learn from high-confidence results
        await agent.procedural_memory.learn_classification_pattern(
            attachment.filename,
            email.subject,
            email.body_text or email.body_html,
            result.document_category.value,
            "unknown",  # Asset type inferred separately
            result.confidence,
            "auto_learning"
        )

# Learn from human corrections
async def learn_from_human_feedback(agent, review_item, human_correction):
    await agent.learn_from_human_feedback(
        review_item.filename,
        review_item.email_subject,
        review_item.email_body,
        review_item.system_prediction,
        human_correction,
        review_item.asset_type
    )
```

### **Asset Relationship Discovery**

```python
# Discover new asset relationships from email patterns
async def discover_asset_patterns(agent, emails):
    patterns = {}

    for email in emails:
        sender = email.sender.address

        # Analyze email content for asset indicators
        combined_text = f"{email.subject} {email.body_text or ''}"

        # Use existing asset matching logic
        known_assets = await agent.list_assets()
        matches = await agent.identify_asset_from_content(
            email.subject,
            email.body_text or email.body_html or "",
            "",  # No filename for email content
            known_assets
        )

        if matches:
            asset_id, confidence = matches[0]
            if confidence > 0.7:  # High confidence threshold
                if sender not in patterns:
                    patterns[sender] = []
                patterns[sender].append({
                    'asset_id': asset_id,
                    'confidence': confidence,
                    'email_subject': email.subject,
                    'date': email.sent_date
                })

    return patterns
```

## 💡 **Best Practices for Asset Processing**

1. **Batch Processing**: Process emails in batches for efficiency
2. **Parallel Processing**: Use async/await for concurrent operations
3. **Error Recovery**: Implement retry logic for transient failures
4. **Memory Management**: Clean up large attachments after processing
5. **Learning Feedback**: Regularly review and correct classifications
6. **Security First**: Always scan attachments for malware
7. **Audit Trail**: Maintain logs of all processing decisions
8. **Performance Monitoring**: Track processing times and success rates

## 📁 **Project Integration**

```
src/
├── email_interface/          # This module
│   ├── __init__.py
│   ├── base.py              # Abstract interfaces
│   ├── gmail.py             # Gmail implementation
│   ├── msgraph.py           # Microsoft Graph implementation
│   └── factory.py           # Interface factory
├── agents/
│   ├── asset_document_agent.py    # Main processing agent
│   └── supervisor.py             # Agent coordination
├── memory/
│   ├── procedural.py            # Learning memory
│   └── episodic.py              # Historical data
├── web_ui/
│   ├── app.py                   # Web interface
│   └── human_review.py          # Review system
└── utils/
    ├── config.py                # Configuration management
    └── logging_system.py        # Structured logging
```

## 🤝 **Integration Examples**

### **Web UI Integration**

The email interface integrates seamlessly with the web UI:

```python
# In web_ui/app.py
@app.route('/api/process-emails', methods=['POST'])
async def api_process_emails():
    interface_type = request.json.get('interface_type', 'gmail')
    max_emails = request.json.get('max_emails', 20)

    # Create interface
    interface = EmailInterfaceFactory.create(interface_type)
    await interface.connect(get_credentials(interface_type))

    # Process with the asset agent
    results = await process_mailbox_emails(interface, max_emails)

    await interface.disconnect()
    return jsonify(results)
```

### **Human Review Integration**

```python
# Queue items for human review
async def queue_for_human_review(processing_result, email_data):
    if processing_result.confidence_level == ConfidenceLevel.VERY_LOW:
        review_item = {
            'id': str(uuid.uuid4()),
            'filename': processing_result.metadata.get('filename'),
            'email_subject': email_data.subject,
            'email_sender': email_data.sender.address,
            'system_prediction': processing_result.document_category.value,
            'confidence': processing_result.confidence,
            'created_date': datetime.now(UTC).isoformat(),
            'status': 'pending'
        }

        # Store in human review queue
        await store_human_review_item(review_item)
        return review_item['id']
```

---

**The Email Interface Layer powers sophisticated asset document processing with memory-driven learning and human-in-the-loop refinement.** 🚀

Ready to process your private market investment documents intelligently!

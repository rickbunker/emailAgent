# Gmail API Setup Guide - Email Agent Integration

> **Complete Gmail integration for the AI-powered asset document management system with memory-driven learning and parallel processing.**

## 🎯 **Overview**

This guide configures Gmail API access for Email Agent's sophisticated document processing capabilities:
- **Memory-driven classification** of email attachments
- **Asset matching** with 1.0 confidence scores
- **Parallel processing** of multiple emails and attachments
- **Human-in-the-loop learning** from user feedback
- **Enterprise security** with ClamAV and SpamAssassin integration

---

## 📋 **Step-by-Step Setup**

### **1. Google Cloud Console Project**

1. **Access Google Cloud Console**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create or Select Project**
   ```
   Project Name: "Email Agent Production" (or "Email Agent Dev")
   Project ID: email-agent-prod-[random] (auto-generated)
   Organization: Your organization (if applicable)
   ```

3. **Enable Billing** (if not already done)
   - Gmail API is free for moderate usage
   - Billing account required for project creation

### **2. Enable Required APIs**

1. **Navigate to APIs & Services** → **Library**

2. **Enable Gmail API**
   - Search: "Gmail API"
   - Click **Gmail API** → **Enable**
   - Quota: 1 billion quota units/day (more than sufficient)

3. **Optional: Enable other Google APIs** (for future expansion)
   - Google Drive API (for document storage integration)
   - Cloud Logging API (for enhanced monitoring)

### **3. Configure OAuth Consent Screen**

1. **Go to APIs & Services** → **OAuth consent screen**

2. **Choose User Type**
   - **Internal**: If you have Google Workspace (recommended for corporate use)
   - **External**: For personal/development use

3. **App Information**
   ```
   App name: Email Agent - Asset Document Management
   User support email: [your-email@company.com]
   App logo: [optional - upload your company logo]
   App domain: [your-domain.com] (if applicable)
   ```

4. **Developer Contact Information**
   ```
   Email addresses: [your-dev-team@company.com]
   ```

5. **Scopes Configuration**
   ```
   Required Scopes:
   - https://www.googleapis.com/auth/gmail.readonly
   - https://www.googleapis.com/auth/gmail.modify
   - https://www.googleapis.com/auth/gmail.labels

   Optional (for enhanced features):
   - https://www.googleapis.com/auth/gmail.compose
   - https://www.googleapis.com/auth/gmail.send
   ```

6. **Test Users** (for External apps)
   - Add email addresses that will test the system
   - Maximum 100 test users during development

### **4. Create OAuth 2.0 Credentials**

1. **Navigate to APIs & Services** → **Credentials**

2. **Create Credentials** → **OAuth 2.0 Client IDs**

3. **Application Type Selection**
   ```
   Application type: Desktop application
   Name: Email Agent Gmail Interface
   ```

4. **Download Credentials**
   - Click **Download JSON**
   - Save as `gmail_credentials.json`

### **5. Install and Configure in Email Agent**

1. **Place Credentials File**
   ```bash
   # Copy to config directory
   cp ~/Downloads/client_secret_*.json config/gmail_credentials.json

   # Verify file structure
   cat config/gmail_credentials.json | jq '.installed.client_id'
   ```

2. **Test Connection**
   ```bash
   # Activate Email Agent environment
   source .emailagent/bin/activate

   # Quick connection test
   python -c "
   import asyncio
   from src.email_interface import create_email_interface

   async def test_gmail():
       gmail = create_email_interface('gmail')
       success = await gmail.connect({'credentials_file': 'config/gmail_credentials.json'})
       print(f'Gmail connection: {\"✅ Success\" if success else \"❌ Failed\"}')
       if success:
           profile = await gmail.get_profile()
           print(f'Connected as: {profile[\"name\"]} ({profile[\"email\"]})')
           await gmail.disconnect()

   asyncio.run(test_gmail())
   "
   ```

---

## 🚀 **Email Agent Integration**

### **Web Interface Setup**

1. **Start Email Agent**
   ```bash
   python app.py
   # Open http://localhost:5001
   ```

2. **Configure Gmail Mailbox**
   - Navigate to **"Email Processing"**
   - Select **"Gmail"** as email system
   - **Credentials**: Should auto-detect `config/gmail_credentials.json`
   - **Mailbox ID**: Set to `gmail_primary` (or custom name)

3. **First-Time Authentication**
   - Click **"Process Emails"**
   - Browser will open for OAuth consent
   - Grant permissions to Email Agent
   - Token saved automatically to `config/gmail_token.json`

### **Processing Configuration**

```bash
# Environment variables (optional)
export GMAIL_CREDENTIALS_PATH="config/gmail_credentials.json"
export GMAIL_TOKEN_PATH="config/gmail_token.json"
export MAX_CONCURRENT_EMAILS=5          # Parallel email processing
export MAX_CONCURRENT_ATTACHMENTS=10    # Parallel attachment processing
export DEFAULT_HOURS_BACK=24            # Email lookback period
```

### **Multi-Mailbox Support**

**`config/mailbox_config.json`** (example)
```json
{
  "mailboxes": [
    {
      "id": "gmail_primary",
      "type": "gmail",
      "credentials_file": "config/gmail_credentials.json",
      "enabled": true,
      "description": "Primary Gmail account"
    },
    {
      "id": "gmail_deals",
      "type": "gmail",
      "credentials_file": "config/gmail_deals_credentials.json",
      "enabled": true,
      "description": "Deals team Gmail account"
    }
  ]
}
```

---

## 🔐 **Authentication Flow**

### **Initial Setup (One-time)**
1. **User clicks "Process Emails"** in web interface
2. **Browser opens** Google OAuth consent screen
3. **User grants permissions**:
   - Read email messages and settings
   - Modify email messages and settings
   - Manage email labels
4. **Token stored** securely in `config/gmail_token.json`
5. **Future access** uses stored token (auto-refresh)

### **Token Management**
```bash
# Check token status
python -c "
import json
from pathlib import Path
from datetime import datetime

if Path('config/gmail_token.json').exists():
    with open('config/gmail_token.json') as f:
        token = json.load(f)
        expires = datetime.fromtimestamp(token.get('expiry', 0))
        print(f'Token expires: {expires}')
        print(f'Valid: {expires > datetime.now()}')
else:
    print('No token file found - authentication required')
"

# Force re-authentication (if needed)
rm config/gmail_token.json
# Next processing run will trigger new OAuth flow
```

---

## 🎛️ **Email Agent Processing Features**

### **Intelligent Email Processing**
```python
# What happens when you click "Process Emails":

# 1. Parallel email fetching (5 concurrent emails)
emails = await gmail.list_emails(criteria=EmailSearchCriteria(
    max_results=50,
    hours_back=24,
    has_attachments=True
))

# 2. Memory-driven attachment classification
for email in emails:
    for attachment in email.attachments:
        result = await agent.enhanced_process_attachment(
            attachment_data={'filename': attachment.filename, 'content': attachment.content},
            email_data={'subject': email.subject, 'sender': email.sender.address}
        )

        # 3. Asset matching with 1.0 confidence scores
        if result.matched_asset_id:
            # 4. Automatic file organization
            saved_path = await agent.save_attachment_to_asset_folder(
                attachment.content,
                attachment.filename,
                result,
                result.matched_asset_id
            )
```

### **Human Learning Integration**
- **Low-confidence items** → Human Review Queue
- **User corrections** → Episodic Memory (automatic learning)
- **Pattern evolution** → Procedural Memory updates
- **No code changes** required for system improvement

### **Security Processing**
- **ClamAV virus scanning** on all attachments
- **SpamAssassin filtering** for email content
- **File type validation** and size limits
- **SHA256 duplicate detection**

---

## 🛠️ **Troubleshooting**

### **Common Authentication Issues**

**"credentials.json not found"**
```bash
# Verify file location and format
ls -la config/gmail_credentials.json
cat config/gmail_credentials.json | jq '.installed.client_id' 2>/dev/null || echo "Invalid JSON format"
```

**"Access blocked: This app's request is invalid"**
```bash
# Check OAuth consent screen configuration
echo "1. Verify Gmail API is enabled in Google Cloud Console"
echo "2. Confirm OAuth consent screen is properly configured"
echo "3. Check that test users are added (for External apps)"
```

**"insufficient authentication scopes"**
```bash
# Clear token to force re-authentication with correct scopes
rm config/gmail_token.json
echo "Next processing run will request proper scopes"
```

**"This app isn't verified"**
```bash
echo "For development: Click 'Advanced' → 'Go to Email Agent (unsafe)'"
echo "For production: Submit app for Google verification"
echo "For corporate: Use Internal user type with Google Workspace"
```

### **Performance Issues**

**Slow email processing**
```bash
# Check parallel processing configuration
python -c "
from src.utils.config import config
print(f'Max concurrent emails: {config.max_concurrent_emails}')
print(f'Max concurrent attachments: {config.max_concurrent_attachments}')
"

# Monitor processing in real-time
tail -f logs/email_agent.log | grep "Gmail\|process"
```

**Rate limiting errors**
```bash
# Gmail API quotas (unlikely to hit):
# - 1 billion quota units/day
# - 250 quota units/user/second

# If rate limited, implement exponential backoff
echo "Rate limiting is handled automatically by the Email Agent"
```

### **Memory System Integration Issues**

**Qdrant connection problems**
```bash
# Verify Qdrant is running
curl -s http://localhost:6333/collections | jq .

# Check memory system status
python -c "
import asyncio
from src.memory.procedural import ProceduralMemory
from qdrant_client import QdrantClient

async def check_memory():
    client = QdrantClient('localhost', 6333)
    memory = ProceduralMemory(client)
    stats = await memory.get_pattern_stats()
    print(f'Memory system: {stats}')

asyncio.run(check_memory())
"
```

---

## 🔒 **Security & Production Considerations**

### **Credential Security**
```bash
# Set proper file permissions
chmod 600 config/gmail_credentials.json
chmod 600 config/gmail_token.json

# Never commit credentials to version control
echo "config/*credentials*.json" >> .gitignore
echo "config/*token*.json" >> .gitignore
```

### **Production Deployment**
```bash
# Environment variables for production
export GMAIL_CREDENTIALS_PATH="/secure/path/gmail_credentials.json"
export GMAIL_TOKEN_PATH="/secure/path/gmail_token.json"
export FLASK_ENV=production
export FLASK_SECRET_KEY="your-secure-secret-key"

# Use secure credential storage (e.g., AWS Secrets Manager, Azure Key Vault)
```

### **Monitoring & Logging**
```bash
# Monitor Gmail API usage
tail -f logs/email_agent.log | grep "Gmail API"

# Check processing statistics
curl -s http://localhost:5001/api/processing-history | jq '.summary'
```

---

## 📊 **Testing & Validation**

### **Basic Connectivity Test**
```bash
python -c "
import asyncio
from src.email_interface import create_email_interface

async def test():
    gmail = create_email_interface('gmail')
    connected = await gmail.connect({'credentials_file': 'config/gmail_credentials.json'})

    if connected:
        profile = await gmail.get_profile()
        print(f'✅ Connected: {profile[\"email\"]}')

        # Test email listing
        from src.email_interface.base import EmailSearchCriteria
        emails = await gmail.list_emails(EmailSearchCriteria(max_results=5))
        print(f'✅ Found {len(emails)} recent emails')

        await gmail.disconnect()
    else:
        print('❌ Connection failed')

asyncio.run(test())
"
```

### **End-to-End Processing Test**
```bash
# Process last 24 hours of emails through full Email Agent pipeline
python -c "
import asyncio
from src.web_ui.app import process_mailbox_emails

async def test_processing():
    mailbox_config = {
        'id': 'gmail_primary',
        'type': 'gmail',
        'credentials_file': 'config/gmail_credentials.json'
    }

    results = await process_mailbox_emails(mailbox_config, hours_back=24)

    print(f'✅ Processed {results[\"processed_emails\"]} emails')
    print(f'✅ Found {sum(len(d.get(\"processing_info\", {}).get(\"assets_matched\", [])) for d in results[\"processing_details\"])} asset matches')
    print(f'✅ Classified {sum(d.get(\"processing_info\", {}).get(\"attachments_classified\", 0) for d in results[\"processing_details\"])} attachments')

asyncio.run(test_processing())
"
```

---

## 📁 **File Structure After Setup**

```
config/
├── gmail_credentials.json    # OAuth 2.0 credentials (keep secure)
├── gmail_token.json         # Authentication token (auto-generated)
└── mailbox_config.json      # Multi-mailbox configuration (optional)

logs/
└── email_agent.log          # Processing logs with Gmail activity

assets/
└── [asset_folders]/         # Processed documents organized by asset
    └── [document_categories]/ # loan_documents, financial_statements, etc.
```

---

## 🎯 **Success Metrics**

After successful Gmail integration, you should see:

✅ **Authentication**: OAuth flow completes without errors
✅ **Email Access**: Can list and fetch emails with attachments
✅ **Parallel Processing**: 5 emails processed concurrently
✅ **Asset Matching**: 1.0 confidence scores on known assets
✅ **Document Classification**: 25+ categories with memory-driven learning
✅ **File Organization**: Automatic saving to correct asset folders
✅ **Human Learning**: Low-confidence items routed to review queue

---

**Gmail is now fully integrated with Email Agent's memory-driven document processing system! 🚀**

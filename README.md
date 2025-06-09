# Email Management Agent

An intelligent email management system built using LangGraph's agent framework. This agent helps manage email history and incoming emails using a combination of procedural, semantic, and episodic memory.

## Features

- **🧠 Intelligent email management** using GPT-4.1-mini via Core42 Compass
- **📧 Multi-email system support** via unified Email Interface Layer
  - Gmail integration via Gmail API
  - Microsoft 365/Exchange via Microsoft Graph API
  - Extensible architecture for additional email systems
- **🧬 Advanced memory systems**:
  - Procedural memory for rules and procedures
  - Semantic memory for sender and email type knowledge  
  - Episodic memory for conversation history and feedback
  - Contact extraction and relationship tracking
- **🛡️ Comprehensive spam detection** with SpamAssassin integration
- **🔍 Smart email analysis** with DNS blacklist checking and content analysis
- **🤖 Learning from user feedback** and interactions

## Project Structure

```
emailAgent/
├── src/
│   ├── email_interface/        # 📧 Email system integrations
│   │   ├── base.py            # Abstract interface & data models
│   │   ├── gmail.py           # Gmail API implementation
│   │   ├── msgraph.py         # Microsoft Graph implementation
│   │   └── factory.py         # Interface factory
│   ├── memory/                # 🧠 Memory systems
│   │   ├── contact.py         # Contact extraction & management
│   │   ├── procedural.py      # Rules and procedures memory
│   │   ├── semantic.py        # Sender and email type knowledge
│   │   └── episodic.py        # Conversation history and feedback
│   ├── agents/                # 🤖 AI agents
│   │   ├── contact_extractor.py  # Contact extraction agent
│   │   ├── spam_detector.py      # Spam detection agent
│   │   ├── supervisor.py         # Main supervisor agent
│   │   └── workers.py           # Worker agents for specific tasks
│   └── tools/                 # 🛠️ Utility tools
│       └── spamassassin_integration.py  # SpamAssassin integration
├── examples/
│   └── email_demo.py          # Email interface demonstrations
├── requirements.txt
├── README.md
└── EMAIL_INTERFACE_README.md  # 📧 Detailed email interface docs
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Email Interface Demo
```bash
# See available email systems and configuration
python examples/email_demo.py --system factory

# Test Gmail integration (requires OAuth setup)
python examples/email_demo.py --system gmail

# Test Microsoft Graph (requires Azure app registration)  
python examples/email_demo.py --system microsoft_graph
```

### 3. Email System Setup

#### Gmail Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project and enable Gmail API
3. Create OAuth 2.0 credentials
4. Download `credentials.json`

#### Microsoft Graph Setup  
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register application in Azure AD
3. Configure Microsoft Graph API permissions
4. Get client ID and tenant ID

See [EMAIL_INTERFACE_README.md](EMAIL_INTERFACE_README.md) for detailed setup instructions.

## Core Components

### 📧 Email Interface Layer
Unified interface for connecting to multiple email systems:
- **Gmail**: OAuth 2.0 authentication, full API access
- **Microsoft Graph**: Azure AD authentication, Office 365 integration
- **Extensible**: Easy to add IMAP, POP3, Exchange Server

### 🛡️ Spam Detection System
Multi-layered spam detection combining:
- **SpamAssassin**: Industry-standard rule-based detection
- **DNS Blacklists**: Real-time IP reputation checking
- **Content Analysis**: ML-powered content classification
- **Memory-based Learning**: Adaptive filtering based on user feedback

### 🧠 Memory Architecture
- **Contact Memory**: Extract and track email contacts with relationship mapping
- **Procedural Memory**: Store email processing rules and procedures
- **Semantic Memory**: Build knowledge about senders and email types
- **Episodic Memory**: Track conversation history and user feedback

### 🤖 Agent Framework
LangGraph-powered agents for intelligent email processing:
- **Supervisor Agent**: Orchestrates email processing workflow
- **Contact Extractor**: Identifies and extracts contact information
- **Spam Detector**: Analyzes emails for spam characteristics
- **Worker Agents**: Handle specific email processing tasks

## Usage Examples

### Basic Email Interface Usage
```python
from email_interface import EmailInterfaceFactory, EmailSearchCriteria

# Create and connect to Gmail
gmail = EmailInterfaceFactory.create('gmail')
await gmail.connect({'credentials_file': 'credentials.json'})

# Search for recent emails
criteria = EmailSearchCriteria(max_results=10, is_unread=True)
emails = await gmail.list_emails(criteria)

# Process emails
for email in emails:
    print(f"From: {email.sender.name} <{email.sender.address}>")
    print(f"Subject: {email.subject}")
```

### Spam Detection
```python
from src.agents.spam_detector import SpamDetector

detector = SpamDetector()
result = await detector.analyze_email(email_content)

if result.is_spam:
    print(f"Spam detected! Score: {result.score}")
    print(f"Triggered rules: {result.triggered_rules}")
```

### Contact Extraction
```python
from src.agents.contact_extractor import ContactExtractor

extractor = ContactExtractor()
contacts = await extractor.extract_from_email(email_content)

for contact in contacts:
    print(f"Contact: {contact.name} <{contact.email}>")
    print(f"Confidence: {contact.confidence}")
```

## Development Status

✅ **Completed**:
- Email Interface Layer with Gmail and Microsoft Graph support
- SpamAssassin integration with DNS blacklist checking
- Contact extraction agent with deduplication
- Qdrant-based memory system with 5 collections
- Factory pattern for easy email system instantiation

🚧 **In Progress**:
- Email classification and categorization
- Response automation and templates
- Advanced email threading and conversation management

🔮 **Planned**:
- IMAP/POP3 support for generic email servers
- Real-time email monitoring and processing
- Smart email composition assistance
- Integration with calendar and task management
- Advanced analytics and reporting

## Contributing

This project uses modern Python async/await patterns and follows clean architecture principles. All email operations are non-blocking for optimal performance.

## License

[License information to be added]

---

Ready to revolutionize your email management with AI! 🚀 
# Email Agent - Asset Document Management

An email processing system that monitors incoming emails, identifies attachments related to investment deals, and saves them to appropriate locations with proper classification.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-organized-green.svg)](#testing)

## Project Overview

**emailAgent** processes incoming emails from Gmail and Microsoft 365 accounts, identifies attachments that relate to specific investment deals, and saves those attachments to designated folders with proper organization and metadata.

### Core Features

- **Email Integration** - Gmail and Microsoft Graph APIs for email monitoring
- **Document Classification** - AI-powered classification of attachments by document type
- **Security Scanning** - ClamAV virus scanning and spam detection
- **Asset Matching** - Links documents to specific deals/assets based on email content
- **Memory Systems** - Tracks processing history and learns from user feedback
- **Web Interface** - Management dashboard for monitoring and manual review

## Features

### Email System Support
- **Gmail** - Google Workspace integration with OAuth 2.0 and token caching
- **Microsoft Graph** - Office 365/Microsoft 365 integration with web-based OAuth
- **Unified Interface** - Abstract base class providing consistent API across both systems

### Document Processing
```python
# Automatic document classification with confidence scoring
category, confidence = agent.classify_document(
    filename="Q4_Rent_Roll.xlsx",
    subject="December rent roll for 123 Main Street", 
    body="Monthly tenant payment summary attached",
    asset_type=AssetType.COMMERCIAL_REAL_ESTATE
)
# Result: DocumentCategory.RENT_ROLL, confidence: 0.89
```

**Document Categories Supported:**
- **Commercial Real Estate**: Rent rolls, operating statements, lease agreements, property reports
- **Private Credit**: Loan documents, borrower financials, credit memos, portfolio reports  
- **Private Equity**: Portfolio reports, investment memos, due diligence, exit strategies
- **Infrastructure**: Asset reports, regulatory filings, maintenance logs, environmental reports

### Security & Threat Detection
- **ClamAV Virus Scanning** - Command-line integration with virus detection
- **SpamAssassin Integration** - Rule-based spam detection with scoring
- **Attachment Validation** - File type verification and content analysis
- **Processing History** - Learning from past processing decisions

### Memory Systems
```python
# 5 Specialized Collections:
collections = [
    "contacts",           # Contact extraction and relationship mapping
    "assets",            # Asset information and document association  
    "processing_history", # Email processing results and patterns
    "sender_patterns",   # Sender behavior and classification
    "document_types"     # Document classification training data
]
```

### Confidence-Based Routing
```python
confidence_level = agent.determine_confidence_level(
    document_confidence=0.90,
    asset_confidence=0.85, 
    sender_known=True
)
# Routes to: ConfidenceLevel.HIGH -> Automatic processing
# Routes to: ConfidenceLevel.LOW -> Human review required
```

## Project Structure

```
emailAgent/
├── app.py                          # Main application launcher
├── requirements.txt                # Python dependencies
├── src/                            # Core application code
│   ├── email_interface/            # Email system integrations  
│   │   ├── base.py                 # Abstract interface & data models
│   │   ├── gmail.py                # Gmail API interface
│   │   ├── msgraph.py              # Microsoft Graph interface
│   │   └── factory.py              # Email system factory
│   ├── agents/                     # LangGraph AI agents
│   │   ├── asset_document_agent.py # Main document processing agent
│   │   ├── contact_extractor.py    # Contact extraction agent
│   │   ├── spam_detector.py        # Spam detection agent
│   │   └── supervisor.py           # Multi-agent supervisor
│   ├── memory/                     # Qdrant memory systems
│   │   ├── contact.py              # Contact relationship mapping
│   │   ├── semantic.py             # Document and sender knowledge
│   │   ├── episodic.py             # Processing history and feedback
│   │   └── procedural.py           # Rules and procedures
│   ├── web_ui/                     # Web interface for asset management
│   │   ├── app.py                  # Flask web application
│   │   └── templates/              # HTML templates
│   ├── tools/                      # Security and utility tools
│   │   └── spamassassin_integration.py
│   └── utils/                      # Logging and utility functions
│       └── logging_system.py       # Logging framework
├── tests/                          # Test suite
│   ├── test_msgraph_web_auth.py    # Microsoft Graph auth tests
│   ├── test_phase3_classification.py # AI document classification tests  
│   ├── test_100_real_emails.py     # Performance testing
│   ├── test_logging_system.py      # Logging framework tests
│   ├── test_memory.py              # Memory system tests
│   ├── simple_phase3_test.py       # Basic functionality test
│   └── README.md                   # Test documentation
├── scripts/                        # Development and debug scripts
│   ├── debug_msgraph.py            # Microsoft Graph debugging
│   ├── test_msgraph_simple.py      # Simple testing script
│   └── test_parallel_processing.py # Performance testing
├── data/                           # Temporary data files (gitignored)
├── config/                         # Configuration and credentials
├── docs/                           # Documentation
├── logs/                           # Application logs
└── assets/                         # Asset storage and test documents
```

## Quick Start

### 1. Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install and start ClamAV (macOS with Homebrew)
brew install clamav
freshclam  # Update virus definitions

# Install and start Qdrant vector database
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Microsoft Graph Setup

1. **Azure Portal Setup**: Go to [Azure Portal](https://portal.azure.com/)
2. **Register Application**: Create app registration with appropriate permissions
3. **Configure Authentication**: Add `http://localhost:8080` as redirect URI
4. **Enable Public Client Flows**: Required for device/web authentication

Create `examples/msgraph_credentials.json`:
```json
{
  "application_name": "Your Email Agent",
  "client_id": "your-azure-client-id",
  "tenant_id": "your-azure-tenant-id"
}
```

See [MSGRAPH_SETUP.md](MSGRAPH_SETUP.md) for detailed setup instructions.

### 3. Run the Application

```bash
# Start the web interface for asset management
python app.py
# Access at: http://localhost:5001

# Test basic Phase 3 functionality
python tests/simple_phase3_test.py

# Test Microsoft Graph authentication  
python tests/test_msgraph_web_auth.py

# Test complete document classification
python tests/test_phase3_classification.py
```

## 💡 Usage Examples

### Document Processing Pipeline
```python
from src.agents.asset_document_agent import AssetDocumentAgent

agent = AssetDocumentAgent()

# Process email attachment with full pipeline
result = await agent.enhanced_process_attachment(
    attachment={'filename': 'Q4_Rent_Roll.xlsx', 'content': file_bytes},
    email_context={
        'sender_email': 'manager@property.com',
        'subject': 'December rent roll - 123 Main Street',
        'body': 'Monthly tenant payment summary attached'
    }
)

print(f"Status: {result.status}")
print(f"Document Type: {result.document_category}")  
print(f"Confidence: {result.confidence_level}")
print(f"Asset Matched: {result.asset_id}")
```

### Microsoft Graph Email Processing
```python
from src.email_interface.msgraph import MicrosoftGraphInterface
from src.email_interface.base import EmailSearchCriteria

# Connect to Microsoft 365
msgraph = MicrosoftGraphInterface()
await msgraph.connect()

# Search for emails with attachments
criteria = EmailSearchCriteria(
    has_attachments=True,
    max_results=10,
    is_unread=True
)

emails = await msgraph.list_emails(criteria)

# Process each email through the agent
for email in emails:
    if email.attachments:
        for attachment in email.attachments:
            result = await agent.enhanced_process_attachment(
                attachment, email
            )
```

### Asset and Contact Memory
```python
from src.memory.semantic import SemanticMemory

memory = SemanticMemory()

# Store asset information
await memory.store_asset_info(
    asset_id="123-main-street",
    asset_type="commercial_real_estate", 
    properties={"address": "123 Main Street", "city": "Boston"}
)

# Query for related documents
related = await memory.query_related_assets("rent roll main street")
```

## Testing

The project includes a test suite organized in the `tests/` directory:

### Authentication Tests
- `test_gmail_integration.py` - Gmail API integration and authentication
- `test_msgraph_web_auth.py` - Microsoft Graph web authentication
- `test_msgraph_connection.py` - Connection testing
- `test_msgraph_integration.py` - Integration testing

### Feature Tests  
- `simple_phase3_test.py` - Basic document classification
- `test_phase3_classification.py` - AI processing testing

### Performance Tests
- `test_100_real_emails.py` - Large-scale email processing
- `test_emails_with_attachments.py` - Attachment processing performance

```bash
# Run individual tests
python tests/test_gmail_integration.py      # Test Gmail integration
python tests/test_msgraph_web_auth.py       # Test Microsoft Graph integration
python tests/simple_phase3_test.py          # Test document classification

# See tests/README.md for full testing documentation
```

## Development Status

### Phase 1: Core Infrastructure
- Email interface abstraction layer
- Basic spam detection with SpamAssassin  
- File validation and virus scanning
- Qdrant vector database integration

### Phase 2: Asset Management
- Asset document categorization
- Sender-asset relationship mapping
- Memory systems with 5 collections
- Contact extraction and deduplication

### Phase 3: Document Intelligence
- AI-powered document classification
- Confidence-based routing and decision making
- Asset fuzzy matching from email content
- Processing pipeline with intelligence

### Phase 4: Performance & Scale
- Issue: Slow processing due to sequential ClamAV scanning
- Solution: Parallel processing and optimized virus scanning
- Real-time email monitoring via webhooks
- Batch processing for high-volume scenarios


### **LangGraph Agent Framework**
- **Supervisor Agent**: Orchestrates multi-agent email processing
- **Specialized Agents**: Document classification, contact extraction, spam detection
- **State Management**: Persistent state across agent interactions
- **Error Handling**: Graceful degradation and recovery

### **Async/Await Throughout**
- Non-blocking email operations for optimal performance
- Concurrent processing of multiple emails and attachments  
- Scalable architecture ready for high-volume processing

### **Memory-Driven Intelligence**
- **Procedural Memory**: Email processing rules and procedures
- **Semantic Memory**: Asset knowledge and document classification training
- **Episodic Memory**: Processing history and user feedback for continuous learning
- **Contact Memory**: Relationship mapping and sender intelligence

### **Security-First Design**
- Credential protection with complete `.gitignore`
- Multi-layer threat detection (virus scanning + spam detection)
- Attachment validation and safe processing
- Audit trails and processing history

## 🤝 Contributing

This project follows coding standards:

### 📋 **Development Standards**
- **Type hints** throughout the codebase for better IDE support and error prevention
- **Google-style docstrings** for all functions and classes  
- **Async/await** patterns for optimal performance
- **Configuration system** integration for all settings
- **Structured logging** with project logging framework
- **Abstract base classes** for extensibility
- **Pre-commit hooks** for automated code quality

### 🛠️ **Getting Started with Development**
```bash
# Install development tools
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Review coding standards
see docs/CODING_STANDARDS.md
see docs/DEVELOPMENT_SETUP.md
```

### 📚 **Documentation**
- **[Coding Standards](docs/CODING_STANDARDS.md)** - Comprehensive guidelines for code quality
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** - IDE setup and development workflow  
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions

## Copyright and License

Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker  
License -- for Inveniam use only

---

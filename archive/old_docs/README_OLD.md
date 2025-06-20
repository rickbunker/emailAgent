# Email Agent – AI-Powered Asset Document Management System

> **An intelligent email processing system designed for private market asset management, featuring memory-driven learning, parallel processing, and human-in-the-loop feedback.**

## 🎯 **Overview**

Email Agent is a sophisticated document management system built specifically for private market investments (commercial real estate, private equity, private credit, and infrastructure). It automatically processes corporate mailboxes, classifies attachments using AI, matches documents to assets, and organizes files—all while learning from human feedback to continuously improve accuracy.

### **Key Innovation: Memory-Driven Learning**
Unlike traditional rule-based systems, Email Agent uses a **memory-driven architecture** that:
- **Learns from successful classifications** and adapts patterns
- **Incorporates human feedback** without requiring code changes
- **Replaces 2,788 lines of hardcoded patterns** with adaptive intelligence
- **Achieves 1.0 confidence scores** on asset matching through fuzzy logic and learning

---

## 🏗️ **System Architecture**

```
📧 Email Agent Architecture
├── 🤖 AI Agents Layer
│   ├── Asset Document Agent (Memory-Driven Classification)
│   ├── Spam Detection Agent (Multi-layered Security)
│   ├── Contact Extraction Agent (Relationship Building)
│   └── Supervisor Agent (Workflow Orchestration)
├── 📬 Email Interface Layer
│   ├── Gmail API Integration (OAuth 2.0)
│   ├── Microsoft Graph Integration (Azure AD)
│   └── Unified Email Operations
├── 🧠 Memory System (Qdrant Vector Database)
│   ├── Procedural Memory (Classification Patterns)
│   ├── Episodic Memory (Human Feedback)
│   ├── Semantic Memory (Document Embeddings)
│   └── Contact Memory (Relationship Tracking)
├── 🛡️ Security Layer
│   ├── ClamAV Virus Scanning
│   ├── SpamAssassin Spam Detection
│   ├── File Type Validation
│   └── SHA256 Duplicate Detection
├── 🌐 Web Interface (Flask)
│   ├── Asset Management Dashboard
│   ├── Email Processing Interface
│   ├── Human Review Queue
│   ├── Memory System Dashboards
│   └── File Browser & Organization
└── 📚 Knowledge Base (Version-Controlled)
    ├── 129 Domain Knowledge Items
    ├── Classification Patterns (112 regex patterns)
    ├── Asset Keywords (4 asset types)
    └── Business Rules (Confidence & Routing)
```

---

## 🚀 **Core Features**

### **📧 Intelligent Email Processing**
- **Parallel Processing**: 5 concurrent emails, 10 concurrent attachments
- **Multi-source Support**: Gmail and Microsoft 365/Exchange
- **30-Day Lookback**: Configurable email processing timeframes
- **Duplicate Detection**: SHA256-based with complete audit trails

### **🤖 AI-Powered Document Classification**
- **25+ Document Categories**: Across commercial real estate, private credit, private equity, and infrastructure
- **Memory-Driven Learning**: Adapts from successful classifications
- **Human Feedback Integration**: Learns from corrections without code changes
- **Confidence Scoring**: High/Medium/Low classification with automatic routing

### **🎯 Advanced Asset Matching**
- **Fuzzy Logic Matching**: SequenceMatcher-based similarity scoring
- **Perfect Confidence**: Achieves 1.0 confidence scores on known assets
- **Multi-layer Scoring**: Exact matches, fuzzy matching, keyword boosts
- **Asset Type Intelligence**: Specialized matching per investment type

### **👥 Human-in-the-Loop Learning**
- **Review Queue**: Low-confidence items routed for human input
- **Feedback Integration**: System learns from human corrections
- **Pattern Evolution**: Successful patterns automatically incorporated
- **No Code Changes**: Business users can improve the system directly

### **🛡️ Enterprise Security**
- **Multi-layer Protection**: ClamAV + SpamAssassin + content analysis
- **Quarantine System**: Automatic threat isolation
- **File Validation**: Type whitelisting and size limits
- **Audit Trails**: Complete processing history for compliance

### **🧠 Intelligent Memory System**
- **Vector Database**: Qdrant-powered semantic search and storage
- **Four Memory Types**: Procedural, episodic, semantic, and contact
- **Smart Reset**: Disaster recovery from version-controlled knowledge base
- **Real-time Learning**: Patterns update automatically from successful processing

---

## 📊 **Performance & Scale**

### **Processing Capabilities**
- **Parallel Architecture**: Concurrent email and attachment processing
- **Performance**: Processes 5 emails simultaneously with 10 attachments each
- **Efficiency**: Memory-driven approach reduces processing overhead
- **Scalability**: Async/await architecture designed for high throughput

### **Accuracy Metrics**
- **Asset Matching**: Achieves 1.0 confidence scores on known assets
- **Classification**: 25+ document categories with confidence scoring
- **Learning Rate**: Adapts from successful classifications automatically
- **Human Feedback**: Incorporates corrections for continuous improvement

---

## 🛠️ **Quick Start Guide**

### **1. Prerequisites**
```bash
# System Requirements
Python 3.11+
Docker (for Qdrant)
ClamAV (optional, for virus scanning)
```

### **2. Installation**
```bash
# Clone and setup environment
git clone <repository-url>
cd emailAgent
python -m venv .emailagent
source .emailagent/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### **3. Start Services**
```bash
# Start Qdrant vector database
docker run -p 6333:6333 qdrant/qdrant

# Optional: Install ClamAV for virus scanning
brew install clamav && freshclam  # macOS
# or
apt-get install clamav && freshclam  # Ubuntu
```

### **4. Configure Email Access**
```bash
# Gmail Setup (see docs/GMAIL_SETUP.md)
cp config/gmail_credentials_template.json config/gmail_credentials.json
# Edit with your OAuth 2.0 credentials

# Microsoft Graph Setup (see docs/MSGRAPH_SETUP.md)
cp config/msgraph_credentials_template.json config/msgraph_credentials.json
# Edit with your Azure app registration details
```

### **5. Launch Application**
```bash
# Start the web interface
python app.py

# Access at http://localhost:5001
```

---

## 💡 **Usage Examples**

### **Basic Email Processing**
```python
from src.agents.asset_document_agent import AssetDocumentAgent
from src.email_interface import create_email_interface
from qdrant_client import QdrantClient

# Initialize components
qdrant_client = QdrantClient(host="localhost", port=6333)
agent = AssetDocumentAgent(qdrant_client=qdrant_client)
await agent.initialize_collections()

# Process an attachment
attachment_data = {
    "filename": "Q4_Financial_Report.pdf",
    "content": pdf_content_bytes
}

email_data = {
    "sender_email": "manager@property.com",
    "subject": "Q4 Financials - Main Street Property",
    "body": "Please find attached the quarterly financial report."
}

# Enhanced processing with memory-driven classification
result = await agent.enhanced_process_attachment(attachment_data, email_data)

print(f"Status: {result.status}")
print(f"Document Category: {result.document_category}")
print(f"Matched Asset: {result.matched_asset_id}")
print(f"Confidence: {result.asset_confidence}")
print(f"File Saved: {result.file_path}")
```

### **Human Feedback Learning**
```python
# System learns from human corrections
await agent.learn_from_human_feedback(
    filename="investment_memo.pdf",
    email_subject="Gray IV Investment Opportunity",
    email_body="Please review the attached investment memo.",
    system_prediction="financial_statements",
    human_correction="deal_documents",
    asset_type="private_equity"
)

# The system now knows that investment memos from Gray IV
# should be classified as deal_documents, not financial_statements
```

### **Asset Management**
```python
# Create a new asset
asset_id = await agent.create_asset(
    deal_name="Gray IV",
    asset_name="Gray Industrial Partners IV",
    asset_type=AssetType.PRIVATE_EQUITY,
    identifiers=["Gray", "Gray IV", "GIP IV"]
)

# Files mentioning "Gray IV" will now automatically
# route to this asset's folder structure
```

---

## 📁 **Project Structure**

```
emailAgent/
├── 📄 app.py                          # Flask application entry point
├── ⚙️ pyproject.toml                   # Project configuration & dependencies
├── 📋 requirements.txt                 # Production dependencies
├── 🔧 requirements-dev.txt             # Development dependencies
├── 📚 docs/                           # Comprehensive documentation
│   ├── 📖 CODING_STANDARDS.md        # Development guidelines
│   ├── 🚀 DEPLOYMENT_GUIDE.md        # Production deployment
│   ├── 📧 EMAIL_INTERFACE_README.md  # Email integration guide
│   ├── 📝 LOGGING_GUIDE.md           # Logging system documentation
│   └── 🧪 TESTING_GUIDE.md           # Testing procedures
├── 🧠 knowledge/                     # Version-controlled domain knowledge
│   ├── 📋 classification_patterns.json # 112 regex patterns
│   ├── 🏷️ asset_keywords.json        # Asset type keywords
│   ├── ⚖️ business_rules.json         # Confidence & routing rules
│   └── ⚙️ asset_configs.json         # Validation configurations
├── 🤖 src/                           # Source code
│   ├── 🕵️ agents/                    # AI processing agents
│   │   ├── asset_document_agent.py   # Core document processing (1,583 lines)
│   │   ├── spam_detector.py          # Multi-layer spam detection
│   │   ├── contact_extractor.py      # Relationship management
│   │   └── supervisor.py             # Workflow orchestration
│   ├── 📬 email_interface/           # Email system integrations
│   │   ├── base.py                   # Abstract interface & models
│   │   ├── gmail.py                  # Gmail API implementation
│   │   ├── msgraph.py                # Microsoft Graph implementation
│   │   └── factory.py                # Interface factory pattern
│   ├── 🧠 memory/                    # Qdrant vector database system
│   │   ├── base.py                   # Memory system foundation
│   │   ├── procedural.py             # Classification patterns
│   │   ├── episodic.py               # Human feedback history
│   │   ├── semantic.py               # Document embeddings
│   │   └── contact.py                # Relationship tracking
│   ├── 🛡️ tools/                     # Security & utility tools
│   │   └── spamassassin_integration.py # Spam detection integration
│   ├── ⚙️ utils/                     # Core utilities
│   │   ├── config.py                 # Configuration management
│   │   └── logging_system.py         # Comprehensive logging
│   └── 🌐 web_ui/                    # Flask web interface
│       ├── app.py                    # Main application (4,308 lines)
│       ├── human_review.py           # Review queue management
│       ├── static/                   # CSS, JS, images
│       └── templates/                # HTML templates
├── 🧪 tests/                         # Test suite
├── 📊 scripts/                       # Utility scripts
└── 💾 assets/                        # Processed document storage
    └── [asset_folders]/              # Organized by asset and category
```

---

## 🎛️ **Web Interface Features**

### **📊 Dashboard Overview**
- **Processing Statistics**: Real-time metrics and performance data
- **Asset Overview**: Portfolio summary with document counts
- **Memory Status**: Learning system health and pattern counts
- **Recent Activity**: Latest processing runs and results

### **📬 Email Processing**
- **Multi-mailbox Support**: Process Gmail and Microsoft 365 simultaneously
- **Flexible Timeframes**: 1 hour to 30 days of email history
- **Parallel Processing**: Real-time progress indicators
- **Detailed Results**: Per-email breakdown with attachment analysis

### **👥 Human Review Queue**
- **Low-confidence Items**: Automatic routing for human input
- **Asset Assignment**: Drag-and-drop asset association
- **Category Correction**: Document type refinement
- **Learning Integration**: Feedback automatically improves system

### **📁 File Browser**
- **Asset Organization**: Hierarchical folder structure
- **Category Subfolders**: Automatic document type organization
- **Reclassification**: Easy file movement and correction
- **Download & Preview**: Direct file access

### **🧠 Memory Dashboards**
- **Procedural Memory**: View and manage classification patterns
- **Episodic Memory**: Human feedback history and learning insights
- **Contact Memory**: Relationship tracking and sender analysis
- **Knowledge Base**: Version-controlled domain knowledge viewer

### **🔧 System Management**
- **Asset Management**: Create, edit, and organize investment assets
- **Sender Mappings**: Email-to-asset relationship management
- **Processing History**: Complete audit trails and run logs
- **Testing & Cleanup**: Development and maintenance tools

---

## 🧠 **Memory System Deep Dive**

### **🔄 Procedural Memory**
**Purpose**: Stores learned classification patterns and business rules
- **Classification Patterns**: 112+ regex patterns for document categorization
- **Asset Keywords**: Fuzzy matching terms for asset identification
- **Business Rules**: Confidence thresholds and routing logic
- **Learning Integration**: Automatically incorporates successful patterns

### **📖 Episodic Memory**
**Purpose**: Records human feedback and system learning events
- **Feedback History**: User corrections and suggestions
- **Pattern Evolution**: How the system learned from specific inputs
- **Context Preservation**: Email content and classification context
- **Learning Analytics**: Insights into system improvement over time

### **🔍 Semantic Memory**
**Purpose**: Vector embeddings for document similarity and search
- **Document Embeddings**: Sentence transformer representations
- **Similarity Search**: Find related documents across assets
- **Content Analysis**: Semantic understanding beyond keyword matching
- **Retrieval Augmentation**: Context for classification decisions

### **👥 Contact Memory**
**Purpose**: Relationship tracking and sender intelligence
- **Sender Profiles**: Email address analysis and categorization
- **Trust Levels**: Automatic sender reputation scoring
- **Relationship Mapping**: Asset-to-contact associations
- **Communication Patterns**: Frequency and document type analysis

### **🎯 Smart Memory Reset**
**Purpose**: Disaster recovery and system restoration
- **Knowledge Base Seeding**: Restore from version-controlled patterns
- **Clean Slate Setup**: Fresh installation with proven patterns
- **Environment Migration**: Move patterns between dev/test/prod
- **Backup & Recovery**: Complete system state restoration

---

## 🛡️ **Security Architecture**

### **📧 Email Security**
- **OAuth 2.0 Authentication**: Secure email access without password storage
- **Token Management**: Automatic refresh and secure credential handling
- **Rate Limiting**: API quota management and throttling
- **Connection Encryption**: TLS/SSL for all email communications

### **📎 Attachment Security**
- **ClamAV Integration**: Real-time virus scanning of all attachments
- **Quarantine System**: Automatic isolation of detected threats
- **File Type Validation**: Whitelist-based file type filtering
- **Size Limits**: Configurable maximum attachment sizes

### **🔍 Content Security**
- **SpamAssassin Integration**: Multi-layer spam detection
- **Blacklist Checking**: Real-time DNS blacklist validation
- **Content Analysis**: Pattern-based phishing detection
- **Authentication Validation**: SPF, DKIM, DMARC checking

### **💾 Data Security**
- **SHA256 Hashing**: Duplicate detection and content integrity
- **Audit Trails**: Complete processing history for compliance
- **Secure Storage**: Encrypted credential files
- **Access Controls**: Role-based permissions for sensitive operations

---

## 🔧 **Development & Testing**

### **🛠️ Development Environment**
```bash
# Setup development environment
source .emailagent/bin/activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run development server
python app.py
```

### **🧪 Testing Framework**
```bash
# Run all tests
make test

# Run specific test categories
pytest tests/ -m unit          # Unit tests only
pytest tests/ -m integration   # Integration tests
pytest tests/ -m slow          # Slower tests

# Generate coverage report
pytest --cov=src --cov-report=html
```

### **📋 Code Quality**
- **Black**: Automatic code formatting
- **Ruff**: Fast linting and error detection
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanning
- **Pre-commit**: Automatic quality checks on commits

### **📖 Documentation Standards**
- **Google-style Docstrings**: Comprehensive function documentation
- **Type Hints**: Full type annotation coverage
- **Comprehensive Logging**: `@log_function()` decorators on key methods
- **Architecture Decision Records**: Major design decisions documented

---

## 🚀 **Deployment Guide**

### **🐳 Production Deployment**
```bash
# Production environment setup
export FLASK_ENV=production
export FLASK_SECRET_KEY=your-production-secret
export QDRANT_HOST=your-qdrant-server
export QDRANT_PORT=6333

# Start application
gunicorn --bind 0.0.0.0:5000 app:app
```

### **☁️ Cloud Deployment Options**
- **AWS**: ECS/Fargate with RDS and ElastiCache
- **Azure**: Container Instances with Cosmos DB
- **GCP**: Cloud Run with Cloud SQL
- **Docker**: Complete containerization support

### **📊 Monitoring & Observability**
- **Health Checks**: `/api/health` endpoint for monitoring
- **Metrics Collection**: Processing statistics and performance data
- **Log Aggregation**: Structured logging for centralized monitoring
- **Error Tracking**: Comprehensive error reporting and alerting

---

## 📚 **Documentation Library**

### **🏁 Getting Started**
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)**: Complete development environment
- **[Gmail Setup](docs/GMAIL_SETUP.md)**: OAuth 2.0 configuration for Gmail
- **[Microsoft Graph Setup](docs/MSGRAPH_SETUP.md)**: Azure AD app registration

### **🏗️ Architecture & Design**
- **[Email Interface Guide](docs/EMAIL_INTERFACE_README.md)**: Multi-provider email integration
- **[Asset Management Guide](docs/ASSET_DOCUMENT_MANAGEMENT_README.md)**: Document processing workflows
- **[Logging System](docs/LOGGING_GUIDE.md)**: Comprehensive logging framework

### **🚀 Operations & Deployment**
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment procedures
- **[Testing Guide](docs/TESTING_GUIDE.md)**: Test execution and development
- **[Coding Standards](docs/CODING_STANDARDS.md)**: Development guidelines and best practices

### **🔍 Technical Deep Dives**
- **Knowledge Base**: Version-controlled domain expertise (129 items)
- **Memory Systems**: Four-layer intelligent memory architecture
- **Security Framework**: Multi-layer protection and compliance
- **Performance Optimization**: Parallel processing and async architecture

---

## 🤝 **Contributing**

### **🔄 Development Workflow**
1. **Fork & Clone**: Create your development branch
2. **Environment Setup**: Install dependencies and pre-commit hooks
3. **Feature Development**: Follow coding standards and type annotations
4. **Testing**: Ensure all tests pass and add new test coverage
5. **Documentation**: Update relevant documentation and docstrings
6. **Quality Checks**: Run `make test` to verify all quality gates
7. **Pull Request**: Submit with detailed description and test results

### **📋 Contribution Guidelines**
- **Type Hints**: All functions must have complete type annotations
- **Docstrings**: Google-style documentation for all public methods
- **Testing**: Unit tests required for new functionality
- **Logging**: Use `@log_function()` decorator for important operations
- **Security**: Follow secure coding practices and avoid hardcoded secrets

---

## 📄 **License & Copyright**

**Copyright 2025 Inveniam Capital Partners, LLC and Rick Bunker**
**License**: Internal use only
**Version**: 1.0.0
**Author**: Rick Bunker (rbunker@inveniam.io)

---

## 🎯 **Project Status**

**Current State**: ✅ **Production Ready**
- **Memory System**: Fully operational with learning capabilities
- **Parallel Processing**: 5x performance improvement over sequential processing
- **Asset Matching**: Achieving 1.0 confidence scores on known assets
- **Human Feedback**: Complete learning loop with user interface
- **Security**: Multi-layer protection with ClamAV and SpamAssassin
- **Documentation**: Comprehensive guides and API documentation

**Recent Achievements**:
- ✅ Replaced 2,788 lines of hardcoded patterns with memory-driven learning
- ✅ Implemented parallel processing for 5x performance improvement
- ✅ Achieved perfect 1.0 confidence asset matching scores
- ✅ Built complete human-in-the-loop learning system
- ✅ Created comprehensive knowledge base with 129 domain items
- ✅ Established full test coverage with 11/11 quality checks passing

---

**Ready to transform your email processing workflow with intelligent automation and continuous learning!** 🚀

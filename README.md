# 🤖 Email Agent - Intelligent Asset Document Management

A sophisticated email agent system built with LangGraph that specializes in intelligent document management for private market investments. Features AI-powered document classification, virus scanning, asset intelligence, and comprehensive memory systems.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-organized-green.svg)](#testing)

## 🎯 Project Overview

**emailAgent** is an enterprise-grade intelligent email processing system designed for **asset management firms**, **private equity**, **commercial real estate**, and **infrastructure investments**. It automatically processes incoming emails, classifies documents, detects threats, and maintains comprehensive memory about assets, contacts, and processing history.

### 🏆 Key Achievements (Production Ready: ~75%)

- ✅ **Dual Email Integration** - Both Gmail and Microsoft Graph working with unified interface
- ✅ **AI Document Classification** - 25+ categories across 4 asset types with confidence scoring
- ✅ **ClamAV Virus Scanning** - Reliable command-line integration with temp file handling
- ✅ **Qdrant Memory Systems** - 5 specialized collections for contacts, assets, and processing history
- ✅ **Comprehensive Test Suite** - Organized test structure with performance and integration tests
- ✅ **Professional Architecture** - Clean separation of concerns with async/await patterns

## 🚀 Features

### 📧 **Multi-Email System Support**
- **Gmail** - ✅ Full Google Workspace integration with OAuth 2.0 and token caching
- **Microsoft Graph** - ✅ Full Office 365/Microsoft 365 integration with web-based OAuth
- **Unified Interface** - Abstract base class enabling consistent API across both systems

### 🧠 **Phase 3: AI-Powered Document Intelligence**
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

### 🔒 **Advanced Security & Threat Detection**
- **ClamAV Virus Scanning** - Command-line integration with EICAR test virus detection
- **SpamAssassin Integration** - Rule-based spam detection with scoring
- **Attachment Validation** - File type verification and content analysis
- **Memory-based Threat Intelligence** - Learning from processing history

### 🧬 **Qdrant-Powered Memory Systems**
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

### 🎯 **Confidence-Based Routing**
```python
confidence_level = agent.determine_confidence_level(
    document_confidence=0.90,
    asset_confidence=0.85, 
    sender_known=True
)
# Routes to: ConfidenceLevel.HIGH -> Automatic processing
# Routes to: ConfidenceLevel.LOW -> Human review required
```

## 📁 Project Structure

```
emailAgent/
├── 📂 src/                           # Core application code
│   ├── 📧 email_interface/           # Email system integrations  
│   │   ├── base.py                   # Abstract interface & data models
│   │   ├── gmail.py                 # ✅ Gmail API (working)
│   │   ├── msgraph.py               # ✅ Microsoft Graph (working)
│   │   └── factory.py               # Email system factory
│   ├── 🤖 agents/                   # LangGraph AI agents
│   │   ├── asset_document_agent.py  # ✅ Main document processing agent
│   │   ├── contact_extractor.py     # Contact extraction agent
│   │   ├── spam_detector.py         # Spam detection agent
│   │   └── supervisor.py            # Multi-agent supervisor
│   ├── 🧠 memory/                   # Qdrant memory systems
│   │   ├── contact.py               # Contact relationship mapping
│   │   ├── semantic.py              # Document and sender knowledge
│   │   ├── episodic.py              # Processing history and feedback
│   │   └── procedural.py            # Rules and procedures
│   └── 🛠️ tools/                    # Security and utility tools
│       └── spamassassin_integration.py
├── 📂 tests/                        # ✅ Organized test suite
│   ├── test_msgraph_web_auth.py     # ✅ Working Microsoft Graph auth
│   ├── test_phase3_classification.py # ✅ AI document classification  
│   ├── test_100_real_emails.py      # Performance testing
│   ├── simple_phase3_test.py        # ✅ Basic functionality test
│   └── README.md                    # Test documentation
├── 📂 examples/                     # Integration examples and demos
├── 📂 assets/                       # Test assets and sample documents
├── 📋 requirements.txt              # Python dependencies
└── 📖 Documentation files           # Setup guides and README files
```

## 🚀 Quick Start

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

### 3. Test the System

```bash
# Test basic Phase 3 functionality
python tests/simple_phase3_test.py

# Test Microsoft Graph authentication  
python tests/test_msgraph_web_auth.py

# Test comprehensive document classification
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

## 🧪 Testing

The project includes a comprehensive test suite organized in the `tests/` directory:

### Authentication Tests
- ✅ `test_gmail_integration.py` - Gmail API integration and authentication
- ✅ `test_msgraph_web_auth.py` - Microsoft Graph web authentication
- 🔄 `test_msgraph_connection.py` - Legacy connection testing
- ✅ `test_msgraph_integration.py` - Full integration testing

### Feature Tests  
- ✅ `simple_phase3_test.py` - Basic document classification
- ✅ `test_phase3_classification.py` - Comprehensive AI testing

### Performance Tests
- ⚠️ `test_100_real_emails.py` - Large-scale email processing (slow performance identified)
- ⚠️ `test_emails_with_attachments.py` - Attachment processing performance

```bash
# Run individual tests
python tests/test_gmail_integration.py      # Test Gmail integration
python tests/test_msgraph_web_auth.py       # Test Microsoft Graph integration
python tests/simple_phase3_test.py          # Test document classification

# See tests/README.md for full testing documentation
```

## 🔧 Development Status

### ✅ **Phase 1: Core Infrastructure** (Complete)
- Email interface abstraction layer
- Basic spam detection with SpamAssassin  
- File validation and virus scanning
- Qdrant vector database integration

### ✅ **Phase 2: Asset Management** (Complete)
- Asset document categorization
- Sender-asset relationship mapping
- Enhanced memory systems with 5 collections
- Contact extraction and deduplication

### ✅ **Phase 3: Document Intelligence** (Complete)
- AI-powered document classification (25+ categories)
- Confidence-based routing and decision making
- Asset fuzzy matching from email content
- Enhanced processing pipeline with intelligence

### 🚧 **Phase 4: Performance & Scale** (In Progress)
- **Issue Identified**: Slow processing due to sequential ClamAV scanning
- **Solution Planned**: Parallel processing and optimized virus scanning
- Real-time email monitoring via webhooks
- Batch processing for high-volume scenarios

### 🔮 **Phase 5: Production Features** (Planned)
- Web dashboard for monitoring and management
- RESTful API for integration with other systems
- Advanced analytics and reporting
- Multi-tenant support for enterprise deployment

## 🚀 Future Development Roadmap

### 🧠 **Natural Language Understanding**
Enhanced document classification through deep semantic understanding:

```python
# Advanced content extraction and entity recognition
extracted_entities = await agent.extract_entities(document_content)
# Result: {
#   "property_address": "123 Main Street, Boston MA",
#   "loan_number": "CRE-2024-001", 
#   "counterparty": "Alpha Property Management",
#   "metrics": {"NOI": 2.5e6, "occupancy": 0.94}
# }
```

**Capabilities:**
- **OCR Integration** - Extract text from PDFs, images, and scanned documents
- **Entity Recognition** - Identify property addresses, loan numbers, counterparties, and financial metrics
- **Intent Classification** - Understand document purpose beyond just filename patterns
- **Semantic Comparison** - Compare content with known document examples for better classification
- **Concept Mapping** - Build relationships between related concepts across documents

### 📊 **Multi-Document Relationship Analysis**
Building connections between related documents across time:

```python
# Track document sequences and identify patterns
timeline = await agent.build_asset_timeline(
    asset_id="main-street-plaza",
    document_types=["rent_roll", "operating_statement", "capex_report"]
)
# Result: Time-series analysis of rent rolls showing occupancy trends
```

**Features:**
- **Temporal Analysis** - Track document sequences over time periods
- **Metric Extraction** - Identify and track key metrics across document series
- **Trend Detection** - Recognize patterns in document submissions and content
- **Anomaly Identification** - Flag unusual breaks in document patterns
- **Relationship Visualization** - Create visual maps of document relationships

### 🔮 **Predictive Document Expectation**
Anticipate expected documents based on asset type and timing patterns:

```python
# System anticipates missing documents
expected_docs = await agent.get_missing_documents(
    asset_id="main-street-plaza",
    date_range="Q4-2024"
)
# Result: ["Monthly rent roll (overdue 3 days)", "CapEx invoice (due next week)"]
```

**Capabilities:**
- **Calendar Integration** - Track document due dates based on lease agreements and loan terms
- **Pattern Recognition** - Identify typical document submission schedules from historical data
- **Proactive Notifications** - Alert when expected documents are approaching due dates
- **Confidence Scoring** - Assign probability to expected document arrivals
- **Gap Analysis** - Identify missing documents in expected sequences

### 🌐 **Cross-Asset Intelligence**
Portfolio-level insights and pattern recognition across multiple assets:

```python
# Portfolio-wide analysis and benchmarking
portfolio_insights = await agent.analyze_portfolio_patterns(
    asset_types=["commercial_real_estate"],
    metrics=["occupancy", "noi_growth", "capex_ratio"]
)
# Result: Benchmark analysis showing this asset vs. portfolio averages
```

**Advanced Features:**
- **Portfolio Benchmarking** - Compare document patterns across similar assets
- **Risk Indicators** - Use document patterns to identify potential issues across assets
- **Correlation Analysis** - Find relationships between document patterns and asset performance
- **Outlier Detection** - Identify assets with unusual document submission patterns
- **Performance Prediction** - Use document patterns to predict asset performance trends

### 🤖 **Intelligent Document Workflows**
Automated workflow orchestration based on document classification and confidence:

```python
# Automatic workflow triggering based on document type and confidence
workflow = await agent.trigger_workflow(
    document_type="borrower_financials",
    confidence_level="high",
    asset_id="alpha-credit-001"
)
# Result: Automatically updates covenant testing dashboard, alerts investment team
```

**Workflow Capabilities:**
- **Covenant Monitoring** - Automatic covenant testing when borrower financials arrive
- **Performance Tracking** - Update asset performance dashboards when operating statements received
- **Exception Handling** - Route low-confidence documents to human review queues
- **Stakeholder Notifications** - Alert relevant team members when critical documents arrive
- **Integration Triggers** - Automatically update external systems based on document processing

### 📈 **Advanced Analytics and Reporting**
Business intelligence and operational insights:

- **Processing Metrics** - Track document volume, processing times, and accuracy rates
- **Asset Performance** - Correlate document patterns with asset performance metrics
- **Operational Efficiency** - Measure time savings and error reduction from automation
- **Predictive Analytics** - Forecast document volumes and identify potential bottlenecks
- **Custom Dashboards** - Configurable views for different stakeholder groups

## 🏗️ Architecture Highlights

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
- Credential protection with comprehensive `.gitignore`
- Multi-layer threat detection (virus scanning + spam detection)
- Attachment validation and safe processing
- Audit trails and processing history

## 🤝 Contributing

This project follows clean architecture principles with:
- **Type hints** throughout the codebase
- **Async/await** patterns for performance
- **Abstract base classes** for extensibility
- **Comprehensive error handling** and logging
- **Professional documentation** and testing

## 📄 License

MIT License - see LICENSE file for details.

---

## 🎯 Ready for Production Use

**Perfect for:**
- 🏢 **Asset Management Firms** - Automate document processing workflows
- 🏗️ **Private Equity** - Intelligent portfolio company document handling  
- 🏙️ **Commercial Real Estate** - Automated rent roll and lease processing
- 🔌 **Infrastructure Investments** - Regulatory and compliance document management

**Contact**: Built with ❤️ for intelligent email automation

🚀 **Transform your email management with AI-powered document intelligence!** 
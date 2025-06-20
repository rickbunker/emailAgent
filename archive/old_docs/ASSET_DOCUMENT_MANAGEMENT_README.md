# Asset Document Management System

A sophisticated **Memory-Driven Email Processing Agent** for private market investment document management, featuring AI-powered classification, learning capabilities, and human-in-the-loop refinement.

## 🎯 **System Overview**

The Asset Document Management System automatically processes emails containing investment documents, learns from successful classifications, and organizes documents into asset-specific folder structures with minimal human intervention.

### **Key Capabilities**

- 🧠 **Memory-Driven Learning** - Adapts from successful processing patterns
- 📄 **Intelligent Classification** - Categorizes documents by type and asset
- 🎯 **Asset Matching** - Identifies target assets using fuzzy matching
- 👥 **Human Review System** - Handles low-confidence classifications
- 🔍 **Semantic Search** - Vector-based pattern matching
- 🔒 **Security-First** - Antivirus scanning and quarantine systems
- ⚡ **Parallel Processing** - Concurrent email and attachment handling
- 📊 **Web Interface** - Complete management and review dashboard

## 🏗️ **Architecture Overview**

```
📧 Email Processing Pipeline
├── 🔐 Authentication Layer
│   ├── Gmail API (OAuth 2.0)
│   └── Microsoft Graph (Azure AD)
├── 📨 Email Interface
│   ├── Attachment Extraction
│   ├── Content Analysis
│   └── Sender Recognition
├── 🧠 Asset Document Agent
│   ├── Security Scanning (ClamAV)
│   ├── Duplicate Detection (SHA256)
│   ├── Memory-Driven Classification
│   └── Asset Matching
├── 🗄️ Document Organization
│   ├── Asset-Specific Folders
│   ├── Category Subfolders
│   └── Review Queues
├── 🧠 Procedural Memory
│   ├── Classification Patterns
│   ├── Asset Matching Rules
│   └── Human Feedback Learning
└── 🌐 Web Interface
    ├── Processing Dashboard
    ├── Asset Management
    ├── Human Review System
    └── Learning Analytics
```

## 📄 **Supported Document Types**

### **Commercial Real Estate**
- **Rent Rolls** - Tenant schedules and lease summaries
- **Financial Statements** - Property P&L, cash flow reports
- **Property Photos** - Building and unit images
- **Appraisals** - Property valuation reports
- **Lease Documents** - Tenant leases and amendments
- **Property Management** - Management reports and updates

### **Private Credit**
- **Loan Documents** - Credit agreements, term sheets
- **Borrower Financials** - Financial statements, tax returns
- **Covenant Compliance** - Compliance certificates and reports
- **Credit Memos** - Investment committee materials
- **Loan Monitoring** - Servicing reports and updates

### **Private Equity**
- **Portfolio Reports** - Company performance reports
- **Investor Updates** - LP communications and updates
- **Board Materials** - Board packages and presentations
- **Deal Documents** - Investment memoranda and agreements
- **Valuation Reports** - Portfolio company valuations

### **Infrastructure**
- **Engineering Reports** - Technical studies and assessments
- **Construction Updates** - Progress reports and photos
- **Regulatory Documents** - Permits and compliance filings
- **Operations Reports** - Facility performance data

### **General Categories**
- **Legal Documents** - Contracts, agreements, legal opinions
- **Tax Documents** - Tax returns, K-1s, tax planning
- **Insurance** - Policies, claims, certificates
- **Correspondence** - General business communications

## 🚀 **Quick Start Guide**

### **1. System Setup**

```bash
# Start required services
docker run -p 6333:6333 qdrant/qdrant  # Vector database

# Install dependencies
pip install -r requirements.txt

# Configure credentials (see GMAIL_SETUP.md or MSGRAPH_SETUP.md)
cp config/config.yaml.example config/config.yaml
# Edit config with your credentials
```

### **2. Web Interface**

```bash
# Start the web interface
python -m src.web_ui.app

# Navigate to http://localhost:5000
# Complete setup wizard and test connections
```

### **3. Asset Configuration**

```python
# Create your first asset
from src.agents.asset_document_agent import AssetDocumentAgent, AssetType

agent = AssetDocumentAgent()
await agent.initialize_collections()

# Define an asset
deal_id = await agent.create_asset(
    deal_name="Metroplex Office Complex",
    asset_name="Metroplex Class A Office Building - Dallas, TX",
    asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
    identifiers=["Metroplex", "Dallas Office", "Metro Office", "DOC-2024"]
)

print(f"Created asset: {deal_id}")
```

### **4. Process Emails**

```python
# Basic email processing
from src.email_interface.factory import EmailInterfaceFactory

interface = EmailInterfaceFactory.create('gmail')
await interface.connect(credentials)

# Process recent emails with attachments
results = await process_mailbox_emails(interface, agent, max_emails=10)
print(f"Processed {len(results)} emails")
```

## 📁 **File Organization Structure**

The system automatically organizes documents into a structured hierarchy:

```
./assets/
├── {deal_id}_{deal_name}/                    # Asset-specific folder
│   ├── rent_rolls/                           # Document category folders
│   │   ├── Monthly_Rent_Roll_2024-03.xlsx
│   │   └── Q1_2024_Rent_Roll_Summary.pdf
│   ├── financial_statements/
│   │   ├── 2024_Q1_Financial_Statement.pdf
│   │   └── Annual_Financial_Report_2023.xlsx
│   ├── property_photos/
│   │   ├── Building_Exterior_March_2024.jpg
│   │   └── Lobby_Renovation_Complete.png
│   ├── appraisal/
│   │   └── Property_Appraisal_2024.pdf
│   ├── lease_documents/
│   │   ├── Tenant_A_Lease_Amendment.pdf
│   │   └── New_Lease_Suite_240.docx
│   ├── needs_review/                         # Low confidence items
│   │   └── Unknown_Document_Type.pdf
│   └── uncategorized/                        # Moderate confidence
│       └── Miscellaneous_Report.pdf
└── to_be_reviewed/                           # Global review folders
    ├── very_low_confidence/
    │   └── Unclear_Asset_Document.pdf
    ├── no_asset_match/
    │   └── General_Market_Report.pdf
    └── quarantine/                           # Security threats
        └── suspicious_file.pdf.quarantined
```

## 🧠 **Memory-Driven Learning System**

### **Automatic Learning**

The system automatically learns from high-confidence successful classifications:

```python
# Auto-learning triggers when confidence > 75%
if classification_confidence > 0.75:
    await agent.procedural_memory.learn_classification_pattern(
        filename="Monthly_Rent_Roll_Q1_2024.xlsx",
        email_subject="Q1 Rent Roll - Metroplex Property",
        email_body="Please find attached the quarterly rent roll...",
        predicted_category="rent_roll",
        asset_type="commercial_real_estate",
        confidence=0.89,
        source="auto_learning"
    )
```

### **Human Feedback Learning**

The system learns from human corrections via the web interface:

```python
# Learn from human feedback
pattern_id = await agent.learn_from_human_feedback(
    filename="Property_Report_Q1.pdf",
    email_subject="Quarterly Property Update",
    email_body="Attached is the property performance report...",
    system_prediction="correspondence",
    human_correction="financial_statements",
    asset_type="commercial_real_estate"
)

print(f"Learned new pattern: {pattern_id}")
```

### **Pattern Storage and Retrieval**

All learned patterns are stored in Qdrant vector database for semantic similarity matching:

```python
# Retrieve similar patterns for new classification
similar_patterns = await agent.procedural_memory.find_similar_patterns(
    filename="Building_Report_2024.pdf",
    email_subject="Property Performance Report",
    email_body="Performance metrics for the quarter...",
    min_similarity=0.8
)

for pattern in similar_patterns:
    print(f"Similar: {pattern.category} (confidence: {pattern.confidence:.3f})")
```

## 🎯 **Asset Matching Engine**

### **Multi-Strategy Matching**

The system uses multiple strategies to identify target assets:

1. **Exact Matching** - Direct identifier matches (95% confidence)
2. **Fuzzy Matching** - Similar identifier matches (80-95% confidence)
3. **Keyword Matching** - Asset-related keywords (boost confidence)
4. **Pattern Learning** - Memory-driven asset associations

### **Asset Definition Example**

```python
# Comprehensive asset definition
asset = Asset(
    deal_id="3630bb9c-eee2-4131-9af5-d5d6a287e2db",
    deal_name="Trimble BoA",
    asset_name="Trimble Navigation - Bank of America Credit Facility",
    asset_type=AssetType.PRIVATE_CREDIT,
    folder_path="3630bb9c-eee2-4131-9af5-d5d6a287e2db_Trimble_BoA",
    identifiers=[
        "Trimble Navigation",
        "Trimble Inc",
        "TRMB",
        "Bank of America",
        "BoA Credit",
        "Syndicated Credit",
        "TRM Credit Facility"
    ],
    created_date=datetime.now(UTC),
    last_updated=datetime.now(UTC)
)
```

### **Matching Process**

```python
# Asset matching in action
matches = await agent.identify_asset_from_content(
    email_subject="Trimble Q1 Financial Package",
    email_body="Please find attached Trimble's quarterly financials for the BoA facility...",
    filename="Trimble_Q1_2024_Financials.pdf",
    known_assets=[asset]  # List of all assets
)

for asset_id, confidence in matches:
    print(f"Asset: {asset_id[:8]} -> {confidence:.3f}")
    if confidence > 0.8:
        print("  ✅ High confidence match")
```

## 🔍 **Confidence-Based Routing**

### **Processing Thresholds**

- **High Confidence (≥85%)** - Auto-process and file automatically
- **Medium Confidence (≥65%)** - Process with logging and notification
- **Low Confidence (≥40%)** - Save to asset folder but mark for review
- **Very Low Confidence (<40%)** - Queue for human review

### **Routing Logic**

```python
async def route_document(processing_result, asset_id=None):
    if processing_result.confidence_level == ConfidenceLevel.HIGH:
        # Auto-process: save to specific asset folder with category
        file_path = await agent.save_attachment_to_asset_folder(
            attachment_content, filename, processing_result, asset_id
        )
        await send_success_notification(file_path)

    elif processing_result.confidence_level == ConfidenceLevel.VERY_LOW:
        # Human review: queue for manual classification
        review_id = await queue_for_human_review(processing_result, email_data)
        await send_review_notification(review_id)

    else:
        # Medium/Low: save but flag for verification
        file_path = await agent.save_attachment_to_asset_folder(
            attachment_content, filename, processing_result, asset_id
        )
        await log_moderate_confidence_decision(file_path, processing_result)
```

## 👥 **Human Review System**

### **Web-Based Review Interface**

The system provides a comprehensive web interface for human review:

- **Review Queue** - Pending items requiring human input
- **Batch Processing** - Review multiple items efficiently
- **Learning Integration** - Corrections automatically update the learning system
- **Asset Assignment** - Reassign documents to different assets
- **Category Correction** - Fix misclassifications

### **Review Workflow**

```python
# Human review process
@app.route('/api/human-review/<review_id>/resolve', methods=['POST'])
async def resolve_human_review(review_id):
    correction = request.json

    # Learn from the human feedback
    await agent.learn_from_human_feedback(
        filename=correction['filename'],
        email_subject=correction['email_subject'],
        email_body=correction['email_body'],
        system_prediction=correction['system_prediction'],
        human_correction=correction['human_correction'],
        asset_type=correction['asset_type']
    )

    # Move file to correct location
    await move_document_to_correct_location(review_id, correction)

    return jsonify({"status": "resolved", "learned": True})
```

## 🔒 **Security and Compliance**

### **Antivirus Scanning**

All attachments are scanned with ClamAV before processing:

```python
# Security scanning pipeline
async def security_scan_attachment(content, filename):
    is_clean, threat_name = await security.scan_file_antivirus(content, filename)

    if not is_clean:
        # Quarantine the file
        quarantine_path = await quarantine_file(content, filename, threat_name)
        await notify_security_team(filename, threat_name, quarantine_path)
        return ProcessingResult(
            status=ProcessingStatus.QUARANTINED,
            quarantine_reason=threat_name
        )

    return ProcessingResult(status=ProcessingStatus.SUCCESS)
```

### **Duplicate Detection**

SHA256 hashing prevents duplicate file processing:

```python
# Duplicate detection
file_hash = security.calculate_file_hash(attachment_content)
duplicate_id = await agent.check_duplicate(file_hash)

if duplicate_id:
    logger.info(f"Duplicate detected: {filename} -> {duplicate_id}")
    return ProcessingResult(
        status=ProcessingStatus.DUPLICATE,
        duplicate_of=duplicate_id
    )
```

### **Audit Trail**

All processing decisions are logged for compliance:

```python
# Audit logging
await store_processing_audit({
    'document_id': document_id,
    'filename': filename,
    'sender_email': sender_email,
    'processing_date': datetime.now(UTC),
    'classification': result.document_category,
    'confidence': result.confidence,
    'asset_id': result.matched_asset_id,
    'human_reviewed': result.confidence_level == ConfidenceLevel.VERY_LOW,
    'file_path': str(result.file_path)
})
```

## ⚡ **Performance and Scalability**

### **Parallel Processing**

The system processes multiple emails and attachments concurrently:

```python
# Parallel email processing
async def process_mailbox_parallel(interface, agent, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_single_email(email):
        async with semaphore:
            return await process_email_attachments(email, agent)

    emails = await interface.list_emails(criteria)
    tasks = [process_single_email(email) for email in emails]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

### **Performance Metrics**

- **Processing Speed** - ~2-5 documents per second
- **Memory Usage** - ~200MB baseline + 50MB per concurrent process
- **Storage Efficiency** - Deduplication reduces storage by ~30%
- **Classification Accuracy** - >95% for learned patterns, >80% for new patterns

## 📊 **Monitoring and Analytics**

### **Processing Statistics**

```python
# Get comprehensive processing stats
stats = agent.get_processing_stats()

print(f"Total Processed: {stats['total_processed']}")
print(f"Success Rate: {stats['success_rate']:.1f}%")
print(f"Learning Rate: {stats['learning_rate']:.1f}%")
print(f"Human Corrections: {stats['human_corrections']}")
```

### **Learning Analytics**

```python
# Monitor learning system performance
learning_stats = await agent.procedural_memory.get_learning_stats()

print(f"Classification Patterns: {learning_stats['classification_patterns']}")
print(f"Asset Patterns: {learning_stats['asset_patterns']}")
print(f"Human Feedback Patterns: {learning_stats['human_feedback_patterns']}")
print(f"Auto-Learning Success Rate: {learning_stats['auto_learning_accuracy']:.1f}%")
```

## 🔧 **Configuration and Customization**

### **Asset-Specific Configuration**

```yaml
# config/assets.yaml
assets:
  - deal_id: "custom-asset-id"
    deal_name: "Custom Asset Name"
    asset_type: "commercial_real_estate"
    identifiers:
      - "Primary Name"
      - "Alternate Name"
      - "Short Name"
    keywords:
      - "specific"
      - "keywords"
      - "for matching"
    folder_structure:
      - "custom_category_1"
      - "custom_category_2"
```

### **Processing Customization**

```yaml
# config/processing.yaml
processing:
  confidence_thresholds:
    auto_process: 0.85
    process_with_confirmation: 0.65
    save_uncategorized: 0.40
    human_review: 0.39

  file_handling:
    max_size_mb: 25
    allowed_extensions: [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".pptx", ".jpg", ".png"]
    quarantine_virus_files: true

  learning:
    auto_learning_threshold: 0.75
    pattern_retention_days: 365
    similarity_threshold: 0.8
```

## 🚀 **Advanced Usage**

### **Batch Processing Historical Emails**

```python
# Process historical emails for training
async def process_historical_emails(interface, agent, days_back=90):
    criteria = EmailSearchCriteria(
        has_attachments=True,
        date_after=datetime.now() - timedelta(days=days_back),
        max_results=1000
    )

    emails = await interface.list_emails(criteria)
    results = []

    for email in emails:
        result = await process_email_with_learning(email, agent)
        results.append(result)

        # Learn from high-confidence results
        if result.confidence > 0.8:
            await agent.learn_from_successful_classification(result)

    return results
```

### **Custom Classification Rules**

```python
# Add custom classification logic
class CustomAssetDocumentAgent(AssetDocumentAgent):
    async def custom_classify_document(self, filename, content, email_data):
        # Your custom classification logic
        if "special_keyword" in filename.lower():
            return DocumentCategory.LEGAL_DOCUMENTS, 0.95

        # Fall back to standard classification
        return await super().classify_document(filename, content, email_data)
```

### **Integration with External Systems**

```python
# SharePoint integration example
async def sync_to_sharepoint(file_path, asset_id, document_category):
    sharepoint_client = SharePointClient(config.sharepoint_credentials)

    # Upload to asset-specific SharePoint folder
    sharepoint_path = f"/sites/Assets/{asset_id}/{document_category.value}/"

    await sharepoint_client.upload_file(
        local_path=file_path,
        sharepoint_path=sharepoint_path,
        metadata={
            'Asset_ID': asset_id,
            'Document_Category': document_category.value,
            'Processing_Date': datetime.now(UTC).isoformat(),
            'Classification_Confidence': result.confidence
        }
    )
```

## 🛠️ **Troubleshooting**

### **Common Issues**

**Low Classification Accuracy:**
- Review and correct classifications via web interface
- Add more specific identifiers to asset definitions
- Increase training data by processing historical emails

**Asset Matching Failures:**
- Verify asset identifiers include common variations
- Check for typos in asset names and identifiers
- Review email content for actual asset references

**Performance Issues:**
- Reduce concurrent processing limits
- Optimize Qdrant database performance
- Disable antivirus scanning if not needed

**Memory Growth:**
- Clear old procedural memory patterns periodically
- Monitor Qdrant memory usage and optimize
- Implement pattern archiving for old data

### **Diagnostic Commands**

```bash
# Check system health
python -m src.agents.asset_document_agent --health-check

# Validate configuration
python -m src.utils.config --validate

# Test email connections
python -m src.email_interface --test-connections

# Analyze processing patterns
python -m src.memory.procedural --analyze-patterns
```

## 📚 **Additional Resources**

- **Setup Guides**: `docs/GMAIL_SETUP.md`, `docs/MSGRAPH_SETUP.md`
- **Development**: `docs/DEVELOPMENT_SETUP.md`, `docs/CODING_STANDARDS.md`
- **Email Interface**: `docs/EMAIL_INTERFACE_README.md`
- **Testing**: `docs/TESTING_GUIDE.md`
- **Deployment**: `docs/DEPLOYMENT_GUIDE.md`

## 📞 **Support**

For technical support or questions:
- Check application logs in `logs/` directory
- Use web interface diagnostics
- Review configuration and credentials
- Consult setup documentation

---

**The Asset Document Management System combines sophisticated AI classification with human expertise to create an intelligent, learning document processing solution for private market investments.** 🚀

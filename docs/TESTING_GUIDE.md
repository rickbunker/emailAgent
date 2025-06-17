# Asset Document Management System Testing Guide

Comprehensive testing and quality assurance for the **Memory-Driven Asset Document Processing Agent**.

## 🚀 **Quick Start Testing**

The Asset Document Management System includes a sophisticated testing framework covering all components from email processing to memory-driven learning.

### **1. One-Command Testing**
```bash
# Run all tests and quality checks
make test

# Quick testing (skip slower checks)
make test-quick

# Asset-specific testing
make test-assets

# Run with detailed output and coverage
python scripts/test_harness.py --verbose --coverage
```

### **2. Component-Specific Testing**
```bash
# Test email interfaces
pytest tests/test_email_interface.py -v

# Test asset document agent
pytest tests/test_asset_document_agent.py -v

# Test memory systems
pytest tests/test_memory_systems.py -v

# Test web UI
pytest tests/test_web_ui.py -v

# Test security scanning
pytest tests/test_security.py -v
```

### **3. Individual Quality Tools**
```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# Security scan
make security

# Pre-commit hooks
make pre-commit
```

## 🛠️ **Testing Tools and Framework**

### **Code Quality Tools**
- **Black** - Code formatting (88 character lines)
- **isort** - Import sorting (Black-compatible)
- **Ruff** - Fast Python linter with modern rules
- **Pylint** - Comprehensive code analysis
- **MyPy** - Strict type checking
- **Bandit** - Security vulnerability scanning
- **Pre-commit** - Automated quality control hooks

### **Testing Framework**
- **Pytest** - Test runner with async support
- **Coverage.py** - Test coverage reporting and analysis
- **Pytest-mock** - Advanced mocking utilities
- **Pytest-asyncio** - Async test support
- **Pytest-cov** - Coverage integration
- **Factory Boy** - Test data generation
- **Faker** - Realistic test data creation

### **Asset Processing Test Tools**
- **Qdrant Test Client** - Vector database testing
- **Email Mock Server** - Email interface testing
- **File System Mocks** - Document storage testing
- **Memory Fixtures** - Procedural memory testing

## 📁 **Test Structure**

```
tests/
├── conftest.py                     # Shared fixtures and configuration
├── fixtures/                       # Test data and fixtures
│   ├── email_samples/             # Sample emails with attachments
│   ├── document_samples/          # Sample documents for classification
│   ├── asset_definitions/         # Test asset configurations
│   └── memory_patterns/           # Pre-built learning patterns
├── unit/                          # Unit tests
│   ├── test_asset_document_agent.py
│   ├── test_email_interface.py
│   ├── test_memory_systems.py
│   ├── test_security_scanning.py
│   └── test_classification.py
├── integration/                   # Integration tests
│   ├── test_email_processing_pipeline.py
│   ├── test_memory_learning_flow.py
│   ├── test_asset_matching.py
│   └── test_human_review_workflow.py
├── e2e/                          # End-to-end tests
│   ├── test_complete_processing.py
│   ├── test_web_ui_workflows.py
│   └── test_parallel_processing.py
├── performance/                   # Performance tests
│   ├── test_concurrent_processing.py
│   ├── test_memory_performance.py
│   └── test_large_attachments.py
├── security/                     # Security tests
│   ├── test_malware_detection.py
│   ├── test_input_validation.py
│   └── test_data_sanitization.py
└── web_ui/                       # Web interface tests
    ├── test_asset_management.py
    ├── test_human_review.py
    ├── test_processing_dashboard.py
    └── test_api_endpoints.py
```

## 🧪 **Test Categories and Markers**

### **Pytest Markers**
```python
# Asset processing tests
@pytest.mark.asset_processing
def test_document_classification():
    pass

# Memory system tests
@pytest.mark.memory
def test_procedural_learning():
    pass

# Email interface tests
@pytest.mark.email
def test_gmail_connection():
    pass

# Performance tests
@pytest.mark.performance
def test_concurrent_processing():
    pass

# Security tests
@pytest.mark.security
def test_malware_scanning():
    pass

# Slow tests
@pytest.mark.slow
def test_large_file_processing():
    pass

# Integration tests
@pytest.mark.integration
def test_end_to_end_workflow():
    pass

# Web UI tests
@pytest.mark.web
def test_human_review_interface():
    pass
```

### **Running Specific Test Categories**
```bash
# Asset processing tests only
pytest -m asset_processing

# Memory system tests
pytest -m memory

# Email interface tests
pytest -m email

# Quick tests (exclude slow ones)
pytest -m "not slow"

# Integration tests
pytest -m integration

# Security tests
pytest -m security
```

## 🎯 **Asset-Specific Test Scenarios**

### **Document Classification Testing**

```python
# tests/unit/test_asset_document_agent.py
@pytest.mark.asset_processing
@pytest.mark.asyncio
async def test_document_classification_rent_roll():
    """Test rent roll classification with high confidence."""
    agent = AssetDocumentAgent()

    # Test data
    attachment_data = {
        'filename': 'Monthly_Rent_Roll_March_2024.xlsx',
        'content': load_test_file('rent_roll_sample.xlsx')
    }

    email_data = {
        'sender_email': 'property.manager@realty.com',
        'subject': 'March 2024 Rent Roll - Downtown Property',
        'body': 'Please find attached the monthly rent roll for March 2024.'
    }

    # Process document
    result = await agent.enhanced_process_attachment(attachment_data, email_data)

    # Assertions
    assert result.status == ProcessingStatus.SUCCESS
    assert result.document_category == DocumentCategory.RENT_ROLL
    assert result.confidence_level == ConfidenceLevel.HIGH
    assert result.confidence > 0.85
```

### **Asset Matching Testing**

```python
@pytest.mark.asset_processing
@pytest.mark.asyncio
async def test_asset_matching_fuzzy_logic():
    """Test fuzzy asset matching with variations."""
    agent = AssetDocumentAgent()

    # Create test asset
    asset = Asset(
        deal_id="test-asset-123",
        deal_name="Metroplex Office Complex",
        asset_name="Metroplex Class A Office Building",
        asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
        identifiers=["Metroplex", "Metro Office", "Dallas Office Complex"]
    )

    # Test fuzzy matching
    matches = await agent.identify_asset_from_content(
        email_subject="Metro Office Q1 Report",
        email_body="Quarterly report for the Dallas office complex",
        filename="Metroplex_Q1_2024.pdf",
        known_assets=[asset]
    )

    # Assertions
    assert len(matches) > 0
    assert matches[0][0] == "test-asset-123"  # Asset ID
    assert matches[0][1] > 0.8  # High confidence
```

### **Memory Learning Testing**

```python
@pytest.mark.memory
@pytest.mark.asyncio
async def test_procedural_memory_learning():
    """Test automatic learning from successful classifications."""
    agent = AssetDocumentAgent()

    # Simulate high-confidence classification
    pattern_id = await agent.procedural_memory.learn_classification_pattern(
        filename="Financial_Statement_Q1.pdf",
        email_subject="Q1 Financial Statement",
        email_body="Please find the quarterly financial statement attached.",
        predicted_category="financial_statements",
        asset_type="commercial_real_estate",
        confidence=0.92,
        source="test_learning"
    )

    # Verify pattern was stored
    assert pattern_id is not None

    # Test pattern retrieval
    similar_patterns = await agent.procedural_memory.find_similar_patterns(
        filename="Financial_Report_Q2.pdf",
        email_subject="Q2 Financial Report",
        email_body="Attached is the second quarter financial report.",
        min_similarity=0.8
    )

    assert len(similar_patterns) > 0
    assert similar_patterns[0].category == "financial_statements"
```

## 🔗 **Email Interface Testing**

### **Gmail Interface Testing**

```python
@pytest.mark.email
@pytest.mark.asyncio
async def test_gmail_interface_connection():
    """Test Gmail API connection and basic operations."""

    # Mock credentials for testing
    mock_credentials = {
        'credentials_file': 'tests/fixtures/mock_credentials.json',
        'token_file': 'tests/fixtures/mock_token.json'
    }

    with patch('src.email_interface.gmail.GmailInterface.connect') as mock_connect:
        mock_connect.return_value = True

        interface = GmailInterface()
        result = await interface.connect(mock_credentials)

        assert result is True
        mock_connect.assert_called_once_with(mock_credentials)

@pytest.mark.email
@pytest.mark.asyncio
async def test_email_attachment_extraction():
    """Test attachment extraction from emails."""
    interface = MockEmailInterface()

    # Mock email with attachment
    mock_email = create_mock_email_with_attachment(
        filename="test_document.pdf",
        content=b"mock PDF content",
        sender="test@example.com"
    )

    attachments = await interface.get_email_attachments(mock_email.id)

    assert len(attachments) == 1
    assert attachments[0].filename == "test_document.pdf"
    assert len(attachments[0].content) > 0
```

### **Microsoft Graph Interface Testing**

```python
@pytest.mark.email
@pytest.mark.asyncio
async def test_msgraph_interface_authentication():
    """Test Microsoft Graph authentication flow."""

    mock_credentials = {
        'client_id': 'test-client-id',
        'tenant_id': 'test-tenant-id',
        'redirect_uri': 'http://localhost:8080'
    }

    with patch('src.email_interface.msgraph.MicrosoftGraphInterface._authenticate') as mock_auth:
        mock_auth.return_value = {"access_token": "mock-token"}

        interface = MicrosoftGraphInterface()
        result = await interface.connect(mock_credentials)

        assert result is True
        mock_auth.assert_called_once()
```

## 🔒 **Security Testing**

### **Antivirus Scanning Testing**

```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_malware_detection():
    """Test malware detection with ClamAV."""
    security_service = SecurityService()

    # Create EICAR test file (harmless test virus)
    eicar_content = b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'

    is_clean, threat_name = await security_service.scan_file_antivirus(
        eicar_content, "eicar_test.txt"
    )

    # Should detect the test virus
    assert is_clean is False
    assert "EICAR" in threat_name or "Test" in threat_name

@pytest.mark.security
def test_file_type_validation():
    """Test file type validation."""
    security_service = SecurityService()

    # Valid file types
    assert security_service.validate_file_type("document.pdf") is True
    assert security_service.validate_file_type("spreadsheet.xlsx") is True

    # Invalid file types
    assert security_service.validate_file_type("executable.exe") is False
    assert security_service.validate_file_type("script.py") is False

@pytest.mark.security
def test_file_size_validation():
    """Test file size limits."""
    security_service = SecurityService()

    # Within limits
    assert security_service.validate_file_size(1024 * 1024) is True  # 1MB

    # Exceeds limits (assuming 25MB limit)
    assert security_service.validate_file_size(30 * 1024 * 1024) is False  # 30MB
```

### **Input Validation Testing**

```python
@pytest.mark.security
def test_filename_sanitization():
    """Test filename sanitization for security."""

    # Dangerous filenames
    dangerous_names = [
        "../../../etc/passwd",
        "file\\with\\backslashes",
        "file:with:colons",
        "file<with>brackets",
        "file|with|pipes"
    ]

    for filename in dangerous_names:
        sanitized = sanitize_filename(filename)
        assert "../" not in sanitized
        assert "\\" not in sanitized
        assert ":" not in sanitized
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "|" not in sanitized
```

## 🌐 **Web UI Testing**

### **Human Review Interface Testing**

```python
@pytest.mark.web
@pytest.mark.asyncio
async def test_human_review_queue():
    """Test human review queue functionality."""

    with TestClient(app) as client:
        # Create test review item
        review_item = {
            'filename': 'test_document.pdf',
            'email_subject': 'Test Email',
            'email_sender': 'test@example.com',
            'system_prediction': 'correspondence',
            'confidence': 0.35,
            'status': 'pending'
        }

        # Submit for review
        response = client.post('/api/human-review', json=review_item)
        assert response.status_code == 201

        review_id = response.json()['review_id']

        # Retrieve review item
        response = client.get(f'/api/human-review/{review_id}')
        assert response.status_code == 200
        assert response.json()['filename'] == 'test_document.pdf'

@pytest.mark.web
def test_asset_management_api():
    """Test asset management API endpoints."""

    with TestClient(app) as client:
        # Create asset
        asset_data = {
            'deal_name': 'Test Asset',
            'asset_name': 'Test Asset Full Name',
            'asset_type': 'commercial_real_estate',
            'identifiers': ['Test Asset', 'TA-001']
        }

        response = client.post('/api/assets', json=asset_data)
        assert response.status_code == 201

        asset_id = response.json()['deal_id']

        # Retrieve asset
        response = client.get(f'/api/assets/{asset_id}')
        assert response.status_code == 200
        assert response.json()['deal_name'] == 'Test Asset'
```

### **Processing Dashboard Testing**

```python
@pytest.mark.web
def test_processing_dashboard():
    """Test processing dashboard functionality."""

    with TestClient(app) as client:
        # Test dashboard endpoint
        response = client.get('/dashboard')
        assert response.status_code == 200

        # Test processing stats API
        response = client.get('/api/processing-stats')
        assert response.status_code == 200

        stats = response.json()
        assert 'total_processed' in stats
        assert 'success_rate' in stats
        assert 'learning_rate' in stats
```

## ⚡ **Performance Testing**

### **Concurrent Processing Testing**

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_email_processing():
    """Test concurrent email processing performance."""

    agent = AssetDocumentAgent()

    # Create multiple test emails
    test_emails = [
        create_test_email_with_attachment(i) for i in range(10)
    ]

    # Process concurrently
    start_time = time.time()

    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent

    async def process_single_email(email):
        async with semaphore:
            return await agent.process_email(email)

    tasks = [process_single_email(email) for email in test_emails]
    results = await asyncio.gather(*tasks)

    end_time = time.time()
    processing_time = end_time - start_time

    # Performance assertions
    assert len(results) == 10
    assert processing_time < 30  # Should complete in under 30 seconds
    assert all(result.status == ProcessingStatus.SUCCESS for result in results)

@pytest.mark.performance
@pytest.mark.slow
async def test_large_attachment_processing():
    """Test processing of large attachments."""

    # Create large test file (10MB)
    large_content = b'0' * (10 * 1024 * 1024)

    attachment_data = {
        'filename': 'large_document.pdf',
        'content': large_content
    }

    email_data = {
        'sender_email': 'test@example.com',
        'subject': 'Large Document',
        'body': 'Large document for testing.'
    }

    agent = AssetDocumentAgent()

    start_time = time.time()
    result = await agent.enhanced_process_attachment(attachment_data, email_data)
    end_time = time.time()

    # Performance and functionality assertions
    assert result.status == ProcessingStatus.SUCCESS
    assert (end_time - start_time) < 60  # Should complete in under 1 minute
```

### **Memory Performance Testing**

```python
@pytest.mark.performance
@pytest.mark.memory
async def test_memory_system_performance():
    """Test procedural memory performance with large datasets."""

    procedural_memory = ProceduralMemory()

    # Create many test patterns
    patterns = []
    for i in range(1000):
        pattern_id = await procedural_memory.learn_classification_pattern(
            filename=f"test_document_{i}.pdf",
            email_subject=f"Test Subject {i}",
            email_body=f"Test body content {i}",
            predicted_category="test_category",
            asset_type="test_type",
            confidence=0.8 + (i % 20) / 100,  # Varying confidence
            source="performance_test"
        )
        patterns.append(pattern_id)

    # Test retrieval performance
    start_time = time.time()

    similar_patterns = await procedural_memory.find_similar_patterns(
        filename="test_document_query.pdf",
        email_subject="Test Query Subject",
        email_body="Test query body content",
        min_similarity=0.7
    )

    end_time = time.time()
    query_time = end_time - start_time

    # Performance assertions
    assert len(similar_patterns) > 0
    assert query_time < 5  # Should complete query in under 5 seconds
```

## 🔧 **Test Configuration and Setup**

### **pytest.ini Configuration**

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --asyncio-mode=auto
markers =
    asset_processing: Asset document processing tests
    memory: Memory system tests
    email: Email interface tests
    security: Security and validation tests
    performance: Performance and load tests
    web: Web interface tests
    integration: Integration tests
    slow: Slow tests (excluded from quick runs)
    unit: Unit tests
    e2e: End-to-end tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### **Test Environment Setup**

```python
# conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from src.agents.asset_document_agent import AssetDocumentAgent
from src.memory.procedural import ProceduralMemory
from src.email_interface.factory import EmailInterfaceFactory

@pytest.fixture
async def agent():
    """Create test asset document agent."""
    agent = AssetDocumentAgent(base_assets_path="./test_assets")
    await agent.initialize_collections()
    yield agent
    # Cleanup
    shutil.rmtree("./test_assets", ignore_errors=True)

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    mock_client = MagicMock()
    mock_client.create_collection.return_value = True
    mock_client.upsert.return_value = True
    mock_client.search.return_value = []
    return mock_client

@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        'sender_email': 'test@example.com',
        'subject': 'Test Email Subject',
        'body': 'Test email body content',
        'sent_date': '2024-03-15T10:00:00Z'
    }

@pytest.fixture
def sample_attachment_data():
    """Sample attachment data for testing."""
    return {
        'filename': 'test_document.pdf',
        'content': b'PDF test content'
    }

@pytest.fixture
def test_asset():
    """Create test asset for testing."""
    from src.agents.asset_document_agent import Asset, AssetType
    from datetime import datetime, UTC

    return Asset(
        deal_id="test-asset-123",
        deal_name="Test Asset",
        asset_name="Test Asset Full Name",
        asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
        folder_path="test-asset-folder",
        identifiers=["Test Asset", "TA-001", "Test Property"],
        created_date=datetime.now(UTC),
        last_updated=datetime.now(UTC)
    )
```

## 📊 **Coverage and Quality Metrics**

### **Coverage Goals**
- **Overall Coverage**: >80%
- **Critical Modules**: >90%
  - Asset Document Agent
  - Security Service
  - Memory Systems
- **Web Interface**: >75%
- **Email Interfaces**: >85%

### **Quality Metrics**
```bash
# Generate comprehensive coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Check coverage by module
coverage report --show-missing

# Generate badge-friendly coverage
coverage-badge -o coverage.svg
```

## 🚨 **Common Issues & Solutions**

### **Async Test Issues**
```python
# Problem: Async test not running properly
def test_async_function():  # Wrong
    result = async_function()
    assert result

# Solution: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():  # Correct
    result = await async_function()
    assert result
```

### **Qdrant Connection Issues**
```python
# Problem: Real Qdrant connection in tests
@pytest.fixture
def agent():
    return AssetDocumentAgent()  # Uses real Qdrant

# Solution: Mock Qdrant client
@pytest.fixture
def agent(mock_qdrant_client):
    return AssetDocumentAgent(qdrant_client=mock_qdrant_client)
```

### **File System Cleanup**
```python
# Problem: Test files left behind
def test_file_processing():
    agent.save_file("test.pdf", content)
    # No cleanup

# Solution: Use fixtures with cleanup
@pytest.fixture
def temp_assets_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
```

## 🎯 **Development Workflow**

### **Pre-Development Testing**
```bash
# Setup development environment
make setup

# Run quick tests before starting work
make test-quick
```

### **During Development**
```bash
# Test specific functionality
pytest tests/unit/test_asset_document_agent.py::test_specific_function -v

# Watch mode for continuous testing
pytest-watch tests/unit/test_asset_document_agent.py
```

### **Pre-Commit Testing**
```bash
# Full test suite
make test

# Fix any formatting issues
make format

# Check all quality metrics
python scripts/test_harness.py --verbose
```

## 🔗 **CI/CD Integration**

### **GitHub Actions Workflow**
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      qdrant:
        image: qdrant/qdrant
        ports:
          - 6333:6333

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        make test

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 📚 **Additional Testing Resources**

### **Essential Commands**
```bash
# Core testing commands
make test              # Full test suite
make test-quick        # Quick tests only
make test-assets       # Asset processing tests
make test-memory       # Memory system tests
make test-security     # Security tests
make test-performance  # Performance tests

# Quality assurance
make format           # Format all code
make lint            # Run all linters
make type-check      # Type checking
make security        # Security scanning
make coverage        # Generate coverage report
```

### **Debugging Tests**
```bash
# Run with debugger
pytest --pdb tests/unit/test_asset_document_agent.py

# Verbose output
pytest -v -s tests/unit/test_asset_document_agent.py

# Run single test
pytest tests/unit/test_asset_document_agent.py::test_specific_function -v

# Show print statements
pytest -s tests/unit/test_asset_document_agent.py
```

### **Files to Know**
- `pyproject.toml` - All tool configuration
- `pytest.ini` - Pytest-specific configuration
- `conftest.py` - Shared test fixtures
- `Makefile` - Development shortcuts
- `requirements-dev.txt` - Development dependencies
- `scripts/test_harness.py` - Comprehensive testing script

---

**Comprehensive Testing Ensures Reliable Asset Document Processing! 🧪**

The testing framework provides confidence in the memory-driven learning system, asset classification accuracy, and overall system reliability.

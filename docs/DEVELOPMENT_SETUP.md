# Email Agent - Development Setup Guide

> **Complete development environment setup for the AI-powered asset document management system with memory-driven learning and parallel processing capabilities.**

## 🎯 **Overview**

This guide sets up your development environment for Email Agent, a sophisticated document processing system featuring:
- **Memory-driven learning** that adapts from human feedback
- **Parallel email processing** (5 concurrent emails, 10 attachments)
- **Multi-provider email integration** (Gmail + Microsoft Graph)
- **Four-layer memory system** (Procedural, Episodic, Semantic, Contact)
- **Enterprise security** (ClamAV + SpamAssassin + content analysis)

---

## 🚀 **Quick Setup**

### **1. Environment Prerequisites**
```bash
# System Requirements
Python 3.11+              # Core language requirement
Docker 20.10+             # For Qdrant vector database
Git 2.30+                 # Version control

# Optional but recommended
ClamAV 0.103+             # Virus scanning (brew install clamav)
SpamAssassin 3.4+         # Spam detection
```

### **2. Project Setup**
```bash
# Clone the repository
git clone <your-repository-url>
cd emailAgent

# Create and activate virtual environment
python -m venv .emailagent
source .emailagent/bin/activate  # macOS/Linux
# or
.emailagent\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### **3. Core Services**
```bash
# Start Qdrant vector database
docker run -d --name qdrant \
  -p 6333:6333 \
  -v ./qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Optional: Start ClamAV daemon
sudo freshclam              # Update virus definitions
sudo clamd                  # Start daemon (varies by OS)

# Verify services
curl http://localhost:6333/collections  # Should return empty array
```

### **4. Configuration Setup**
```bash
# Email credentials (see specific setup guides)
cp config/gmail_credentials_template.json config/gmail_credentials.json
cp config/msgraph_credentials_template.json config/msgraph_credentials.json

# Environment configuration (optional)
cp .env.example .env
# Edit .env with your specific settings
```

### **5. Initial System Setup**
```bash
# Start the application
python app.py

# Open browser to http://localhost:5001
# Navigate to "Memory" > "Testing & Cleanup" > "Smart Memory Reset"
# This seeds the system with 129 knowledge base items
```

---

## 🛠️ **IDE Configuration**

### **VS Code Setup (Recommended)**

**`.vscode/settings.json`**
```json
{
    "python.defaultInterpreterPath": "./.emailagent/bin/python",
    "python.analysis.typeCheckingMode": "strict",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=120"],
    "python.sortImports.args": ["--profile=black"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true,
        "source.fixAll.ruff": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".mypy_cache": true,
        ".pytest_cache": true,
        ".coverage": true,
        ".emailagent": false,
        "qdrant_storage": true,
        "logs/*.log": true
    },
    "python.analysis.autoImportCompletions": true,
    "python.analysis.include": ["src/"],
    "ruff.args": ["--config=pyproject.toml"]
}
```

**`.vscode/launch.json`** (Debugging)
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Email Agent Web UI",
            "type": "python",
            "request": "launch",
            "program": "app.py",
            "console": "integratedTerminal",
            "env": {
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            }
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

### **PyCharm Setup**
- **Interpreter**: Point to `.emailagent/bin/python`
- **Plugins**: Install Python, Docker, TOML, Markdown
- **Code Style**: Import scheme from `pyproject.toml`
- **Run Configurations**: Create config for `app.py` with Flask environment

---

## 📊 **Development Commands**

### **Code Quality & Formatting**
```bash
# Complete code quality check (matches CI)
make test                           # Runs all 11 quality checks

# Individual formatting
black src/ tests/ scripts/         # Code formatting
isort src/ tests/ scripts/         # Import sorting
ruff check --fix src/              # Fast linting with auto-fix

# Type checking
mypy src/                          # Static type analysis

# Security & advanced linting
bandit -r src/                     # Security vulnerability scan
pylint src/                        # Comprehensive code analysis
```

### **Testing Framework**
```bash
# Run all tests
pytest                             # Basic test run
pytest -v                         # Verbose output
pytest --tb=short                 # Shorter traceback format

# Test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests
pytest -m email                   # Email interface tests
pytest -m slow                    # Slower tests

# Coverage analysis
pytest --cov=src                  # Coverage report
pytest --cov=src --cov-report=html # HTML coverage report
pytest --cov=src --cov-report=term-missing # Missing lines
```

### **Memory System Development**
```bash
# Test memory systems
python -c "
import asyncio
from src.memory.procedural import ProceduralMemory
from qdrant_client import QdrantClient

async def test_memory():
    client = QdrantClient('localhost', 6333)
    memory = ProceduralMemory(client)
    await memory.initialize_collections()
    stats = await memory.get_pattern_stats()
    print(f'Patterns loaded: {stats}')

asyncio.run(test_memory())
"

# Knowledge base validation
python -c "
import json
from pathlib import Path

for file in Path('knowledge').glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        print(f'{file.name}: {len(data)} items')
"
```

### **Email Interface Testing**
```bash
# Test email connections (requires credentials)
python -c "
import asyncio
from src.email_interface import create_email_interface

async def test_email():
    # Test Gmail
    gmail = create_email_interface('gmail')
    print(f'Gmail available: {gmail is not None}')

    # Test Microsoft Graph
    msgraph = create_email_interface('msgraph')
    print(f'Microsoft Graph available: {msgraph is not None}')

asyncio.run(test_email())
"
```

---

## 🧠 **Architecture Development**

### **Understanding the System**
```python
# Key architectural components to understand:

# 1. Memory-Driven Learning
from src.memory.procedural import ProceduralMemory
from src.memory.episodic import EpisodicMemory

# 2. Parallel Processing
from src.web_ui.app import process_mailbox_emails

# 3. Asset Document Agent (core intelligence)
from src.agents.asset_document_agent import AssetDocumentAgent

# 4. Email Interface Layer
from src.email_interface import GmailInterface, MicrosoftGraphInterface

# 5. Security & Tools
from src.tools.spamassassin_integration import SpamAssassinDetector
```

### **Development Patterns**
```python
# Standard Email Agent function template
from typing import Dict, List, Optional, Any
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)

@log_function()
async def process_document(
    document_data: Dict[str, Any],
    context: Dict[str, Any]
) -> ProcessingResult:
    """
    Process a document using memory-driven classification.

    Args:
        document_data: Document content and metadata
        context: Email and processing context

    Returns:
        ProcessingResult with classification and confidence

    Raises:
        ProcessingError: When document processing fails
        ValidationError: When input data is invalid
    """
    logger.info(f"Processing document: {document_data.get('filename')}")

    try:
        # Validate inputs
        if not document_data.get('content'):
            raise ValidationError("Document content is required")

        # Use configuration
        max_size = config.max_attachment_size_mb * 1024 * 1024
        if len(document_data['content']) > max_size:
            raise ValidationError(f"Document too large: {len(document_data['content'])} bytes")

        # Memory-driven processing
        result = await agent.enhanced_process_attachment(document_data, context)

        # Learning integration
        if result.confidence_level == ConfidenceLevel.HIGH:
            await memory.learn_from_success(document_data, result)

        logger.info(f"Processing completed: {result.status}")
        return result

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        # Preserve stack trace for debugging
        raise ProcessingError(f"Document processing failed: {e}") from e
```

---

## 🔧 **Daily Development Workflow**

### **Starting Work**
```bash
# 1. Environment check
source .emailagent/bin/activate
python --version                   # Should be 3.11+
docker ps | grep qdrant           # Verify Qdrant running

# 2. Update dependencies (weekly)
pip install -r requirements.txt -r requirements-dev.txt
pre-commit autoupdate

# 3. Quick system check
curl -s http://localhost:6333/collections | jq .  # Qdrant health
curl -s http://localhost:5001/api/health | jq .   # App health (if running)
```

### **Development Loop**
```bash
# 1. Code with standards
# - Type hints on all functions
# - Google-style docstrings
# - @log_function() on important methods
# - Use config system for settings
# - Follow import organization

# 2. Quick validation
ruff check src/                    # Fast linting
mypy src/ --no-error-summary      # Type checking

# 3. Test changes
pytest tests/ -x                   # Stop on first failure
pytest tests/test_your_module.py   # Test specific module
```

### **Before Committing**
```bash
# 1. Full quality check
make test                          # All 11 quality checks

# 2. Test coverage
pytest --cov=src --cov-fail-under=80

# 3. Documentation update
# Update relevant docstrings and docs/ files

# 4. Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat: add memory-driven document classification"
```

---

## 🐛 **Debugging & Troubleshooting**

### **Common Development Issues**

**Memory System Errors**
```bash
# Check Qdrant connection
curl http://localhost:6333/collections

# Reset memory system (nuclear option)
# Via web UI: Memory > Testing & Cleanup > Smart Memory Reset

# Check knowledge base integrity
python -c "
import json
from pathlib import Path
total = 0
for file in Path('knowledge').glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        count = len(data.get(list(data.keys())[0], {}))
        print(f'{file.name}: {count} items')
        total += count
print(f'Total knowledge items: {total}')
"
```

**Email Interface Issues**
```bash
# Test OAuth credentials
python -c "
import json
from pathlib import Path

# Check Gmail credentials
if Path('config/gmail_credentials.json').exists():
    with open('config/gmail_credentials.json') as f:
        creds = json.load(f)
        print(f'Gmail client_id: {creds.get(\"client_id\", \"Missing\")[:20]}...')

# Check Microsoft Graph credentials
if Path('config/msgraph_credentials.json').exists():
    with open('config/msgraph_credentials.json') as f:
        creds = json.load(f)
        print(f'Graph client_id: {creds.get(\"client_id\", \"Missing\")[:20]}...')
"
```

**Performance Issues**
```bash
# Check parallel processing configuration
python -c "
from src.utils.config import config
print(f'Max concurrent emails: {config.max_concurrent_emails}')
print(f'Max concurrent attachments: {config.max_concurrent_attachments}')
print(f'Email batch size: {config.email_batch_size}')
"

# Monitor processing performance
tail -f logs/email_agent.log | grep "EXIT.*process"
```

**Import and Path Issues**
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package structure
find src/ -name "__init__.py" | sort

# Test imports
python -c "
try:
    from src.agents.asset_document_agent import AssetDocumentAgent
    print('✅ Core agent import successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
"
```

### **IDE-Specific Debugging**

**VS Code Debug Configuration**
- Set breakpoints in `src/` files
- Use "Email Agent Web UI" launch configuration
- Check DEBUG CONSOLE for detailed logs
- Use integrated terminal for commands

**PyCharm Debug Setup**
- Configure remote debugging for containerized services
- Use scientific mode for data exploration
- Set up database connection to Qdrant (port 6333)

---

## 📚 **Learning Resources**

### **Project-Specific**
- **[Main README](../README.md)**: Complete system overview
- **[Coding Standards](CODING_STANDARDS.md)**: Detailed development guidelines
- **[Knowledge Base](../knowledge/README.md)**: Domain expertise documentation
- **[Email Interface Guide](EMAIL_INTERFACE_README.md)**: Multi-provider email integration

### **Technology Stack**
- **[Qdrant Documentation](https://qdrant.tech/documentation/)**: Vector database
- **[Flask Documentation](https://flask.palletsprojects.com/)**: Web framework
- **[AsyncIO Guide](https://docs.python.org/3/library/asyncio.html)**: Async programming
- **[Sentence Transformers](https://www.sbert.net/)**: Text embeddings

### **Development Tools**
- **[Ruff Documentation](https://docs.astral.sh/ruff/)**: Fast Python linter
- **[MyPy Documentation](https://mypy.readthedocs.io/)**: Static type checking
- **[Pytest Documentation](https://docs.pytest.org/)**: Testing framework
- **[Pre-commit Documentation](https://pre-commit.com/)**: Git hooks

---

## 🎯 **Development Success Metrics**

### **Code Quality Checkpoints**
- ✅ **All 11 quality checks pass** (`make test`)
- ✅ **90%+ test coverage** on new code
- ✅ **Complete type annotations** for public APIs
- ✅ **Google-style docstrings** for all functions
- ✅ **No security vulnerabilities** (Bandit scan)

### **System Integration Validation**
- ✅ **Memory system operational** (129 knowledge items loaded)
- ✅ **Email interfaces functional** (Gmail + Microsoft Graph)
- ✅ **Parallel processing working** (5 emails, 10 attachments concurrent)
- ✅ **Learning system active** (human feedback integration)
- ✅ **Asset matching accurate** (1.0 confidence scores achieved)

### **Performance Benchmarks**
- ✅ **Processing speed**: 5x improvement over sequential processing
- ✅ **Memory efficiency**: Vector operations under 100ms
- ✅ **Classification accuracy**: 90%+ on known document types
- ✅ **System uptime**: 99.9% availability target

---

**Your development environment is now configured for building the next generation of intelligent document processing! 🚀**

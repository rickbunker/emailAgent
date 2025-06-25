# Email Agent Coding Standards

This document establishes the coding standards and best practices for the Email Agent project. These guidelines ensure consistency, maintainability, and quality across the codebase.

## 🎯 Core Principles

### 1. Type Safety First
- **ALWAYS use type hints** for all function parameters, return values, and class attributes
- Use `from typing import` for complex types (`Optional`, `List`, `Dict`, `Union`, etc.)
- Prefer specific types over generic ones (`List[str]` vs `List`)
- Use `Optional[T]` instead of `Union[T, None]`

```python
# ✅ Good
def process_email(email_id: str, config: Dict[str, Any]) -> Optional[ProcessingResult]:
    pass

# ❌ Bad
def process_email(email_id, config):
    pass
```

### 2. Documentation Standards
- **ALWAYS include docstrings** for modules, classes, and functions
- Use Google-style docstrings for consistency
- Document parameters, return values, and raised exceptions
- Include usage examples for complex functions

```python
# ✅ Good
def enhanced_process_attachment(
    self,
    attachment_data: Dict[str, Any],
    email_data: Dict[str, Any]
) -> AttachmentProcessingResult:
    """
    Process an email attachment with AI classification.

    Args:
        attachment_data: Dictionary containing 'filename' and 'content'
        email_data: Dictionary with sender, subject, date, and body info

    Returns:
        AttachmentProcessingResult with classification and confidence scores

    Raises:
        ProcessingError: If attachment cannot be processed

    Example:
        >>> result = agent.enhanced_process_attachment(
        ...     {"filename": "report.pdf", "content": pdf_bytes},
        ...     {"sender_email": "user@example.com", "subject": "Q4 Report"}
        ... )
        >>> print(result.document_category)
    """
```

### 3. Configuration & Logging Integration
- **ALWAYS use the project's configuration system** (`src.utils.config`) when available
- **ALWAYS use the project's logging system** (`src.utils.logging_system`) when available
- Import and use the global `config` object for settings
- Use `get_logger(__name__)` for module-specific logging
- Use `@log_function()` decorator for important functions

```python
# ✅ Good
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)

@log_function()
def process_mailbox(mailbox_id: str) -> ProcessingStats:
    """Process emails from specified mailbox."""
    logger.info(f"Processing mailbox: {mailbox_id}")

    # Use configuration
    hours_back = config.default_hours_back
    max_emails = config.max_emails_per_batch

    # ... processing logic
```

### 4. Import Organization (PEP 8)
- **ALWAYS organize imports at the top** of the file unless circular references exist
- Group imports: standard library, third-party, local imports
- Use absolute imports when possible
- Handle circular imports with local imports and document why

```python
# ✅ Good - Standard library first
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party libraries
import asyncio
from flask import Flask, request
from qdrant_client import QdrantClient

# Local imports
from src.utils.config import config
from src.utils.logging_system import get_logger
from src.agents.asset_document_agent import AssetDocumentAgent
```

## 🔧 Technical Standards

### Error Handling
- Use specific exception types, not bare `except:`
- Always log errors with context
- Use the configuration system for error thresholds

```python
# ✅ Good
try:
    result = await process_attachment(attachment)
except FileNotFoundError as e:
    logger.error(f"Attachment file not found: {attachment.filename}: {e}")
    raise ProcessingError(f"Cannot process {attachment.filename}") from e
except Exception as e:
    logger.error(f"Unexpected error processing {attachment.filename}: {e}")
    if config.development_mode:
        raise  # Re-raise in development
    return ProcessingResult.error(str(e))
```

### Async/Await Patterns
- Use `async def` for I/O operations (file, network, database)
- Properly await all async calls
- Use `asyncio.gather()` for parallel operations
- Handle async exceptions properly

```python
# ✅ Good
async def process_multiple_attachments(
    attachments: List[AttachmentData]
) -> List[ProcessingResult]:
    """Process multiple attachments in parallel."""
    tasks = [
        process_single_attachment(attachment)
        for attachment in attachments
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Data Classes and Models
- Use `@dataclass` for simple data containers
- Use Pydantic models for validation when needed
- Define clear interfaces with proper typing

```python
# ✅ Good
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessingResult:
    """Result of email attachment processing."""
    success: bool
    attachment_name: str
    file_path: Optional[Path]
    confidence_score: float
    error_message: Optional[str] = None

    @classmethod
    def success_result(cls, name: str, path: Path, confidence: float) -> 'ProcessingResult':
        return cls(True, name, path, confidence)

    @classmethod
    def error_result(cls, name: str, error: str) -> 'ProcessingResult':
        return cls(False, name, None, 0.0, error)
```

## 🏗️ Architecture Standards

### Separation of Concerns
- Keep business logic separate from web routes
- Use service classes for complex operations
- Abstract external dependencies (email APIs, databases)

### Configuration Management
- Use environment variables for deployment settings
- Use the config system for all configurable values
- Validate configuration on startup

### Testing Standards
- Write tests for all public functions
- Use descriptive test names that explain the scenario
- Mock external dependencies
- Test both success and failure cases

```python
# ✅ Good
async def test_process_attachment_with_valid_pdf_returns_success():
    """Test that processing a valid PDF attachment returns success result."""
    # Arrange
    attachment_data = {"filename": "test.pdf", "content": valid_pdf_bytes}
    email_data = {"sender_email": "test@example.com"}

    # Act
    result = await agent.process_attachment(attachment_data, email_data)

    # Assert
    assert result.success is True
    assert result.confidence_score > 0.5
    assert result.file_path is not None
```

## 📁 File Organization

### Directory Structure
```
src/
├── agents/          # AI processing agents
├── email_interface/ # Email system integrations
├── memory/          # Memory and storage systems
├── tools/           # Utility tools and scripts
├── utils/           # Shared utilities (config, logging)
└── web_ui/          # Web interface components

tests/               # Test files mirroring src/ structure
docs/                # Documentation
config/              # Configuration files and credentials
```

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`

## 🚀 Performance Standards

### Parallel Processing
- Use `asyncio.gather()` for I/O-bound parallel operations
- Use `concurrent.futures` for CPU-bound parallel operations
- Consider memory usage when processing large batches
- Use configuration for batch sizes and concurrency limits

### Resource Management
- Use context managers (`with` statements) for file operations
- Close database connections and HTTP clients properly
- Monitor memory usage for large file processing
- Implement proper cleanup in finally blocks

## 🔒 Security Standards

### Input Validation
- Validate all external inputs (email data, file uploads, API parameters)
- Use the configuration system for security limits (file sizes, etc.)
- Sanitize file paths and names
- Check file types against allowed extensions

### Credential Management
- Never hardcode credentials or secrets
- Use the `config/` directory for credential files
- Reference credentials through the configuration system
- Log security events but never log credentials

## 📋 Code Review Checklist

Before committing code, verify:

- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Imports are organized per PEP 8
- [ ] Configuration system used for settings
- [ ] Logging system used for important events
- [ ] Error handling includes proper logging
- [ ] No hardcoded values (use config instead)
- [ ] Async functions properly await all calls
- [ ] Tests written for new functionality
- [ ] Security considerations addressed

## 🧪 Testing Workflow

### **Required Testing During Development**

**After Modest Changes** (bug fixes, small feature additions, refactoring):
```bash
make test-quick
```
- Runs fast linting (ruff), type checking (mypy quick), and tests
- Skips slower tools (bandit, full pylint)
- **Use this frequently during development**

**After Significant Changes** (new features, major refactoring, before commits):
```bash
make test
```
- Runs full test suite with all quality checks
- Includes security scanning, comprehensive linting, and full type checking
- **Required before committing to main branch**

### **Integration with Code Review Checklist**

Add to your development workflow:
- [ ] `make test-quick` passes after each coding session
- [ ] `make test` passes before creating pull requests
- [ ] All tests pass locally before pushing changes
- [ ] New functionality includes corresponding tests

### **Quick Reference Commands**
```bash
make test-quick    # Fast checks during development
make test          # Full validation before commit
make format        # Auto-fix formatting issues
make lint          # Run linting checks only
make type-check    # Run type checking only
```

### **When Tests Fail**
1. **Formatting issues**: Run `make format` to auto-fix
2. **Type errors**: Add missing type hints, fix syntax issues
3. **Linting warnings**: Use `--fix` flag or fix manually
4. **Test failures**: Fix the underlying issue, don't ignore tests

> 📖 **For complete testing documentation, see the Testing Strategy section in the main README.md**

## 🛠️ Development Tools

### Recommended VS Code Extensions
- Python (Microsoft)
- Pylance (Microsoft)
- autoDocstring (Python Docstring Generator)
- GitLens

### Code Formatting
- Use `black` for code formatting
- Use `isort` for import sorting
- Use `mypy` for type checking
- Use `pylint` for code quality

---

**These standards ensure the Email Agent codebase remains maintainable and scalable. When in doubt, follow these guidelines.**

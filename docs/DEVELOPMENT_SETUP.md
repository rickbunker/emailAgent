# Development Setup Guide

This guide helps you set up your development environment to follow the Email Agent coding standards.

## 🚀 Quick Setup

### 1. Install Development Tools
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks (recommended)
pre-commit install
```

### 2. Configure Your IDE

#### VS Code Settings (`.vscode/settings.json`)
```json
{
    "python.defaultInterpreterPath": "./.emailagent/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.sortImports.args": ["--profile=black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".mypy_cache": true,
        ".pytest_cache": true,
        ".coverage": true
    }
}
```

## 🛠️ Development Commands

### Code Formatting
```bash
# Format all Python files
black src/ tests/

# Sort imports
isort src/ tests/

# Run both formatting and import sorting
black src/ tests/ && isort src/ tests/
```

### Code Quality Checks
```bash
# Type checking
mypy src/

# Linting
pylint src/

# Security scanning
bandit -r src/

# Fast linting with ruff
ruff check src/

# Run all checks
ruff check src/ && mypy src/ && pylint src/
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m email         # Email interface tests
```

### Pre-commit Hooks
```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run mypy

# Update hook versions
pre-commit autoupdate
```

## 📋 Daily Development Workflow

### Before Starting Work
```bash
# Make sure you're using the project environment
source .emailagent/bin/activate  # or activate your venv

# Update pre-commit hooks (weekly)
pre-commit autoupdate

# Check code quality baseline
pytest --co -q  # Check if tests are discoverable
mypy src/ --no-error-summary  # Quick type check
```

### While Coding
- **Write type hints** for all function parameters and return values
- **Add docstrings** for all public functions and classes
- **Use the logging system** (`get_logger(__name__)`) instead of print
- **Use the config system** for any configurable values
- **Follow import organization** (stdlib, third-party, local)

### Before Committing
```bash
# Quick quality check
ruff check src/ && mypy src/

# Run tests
pytest tests/

# Pre-commit will automatically run when you commit
git add .
git commit -m "Your commit message"
```

## 🎯 Coding Standards Quick Reference

### Always Include These Imports
```python
# At the top of most files
from typing import Dict, List, Optional, Any
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)
```

### Function Template
```python
@log_function()
async def process_attachment(
    attachment_data: Dict[str, Any],
    email_data: Dict[str, Any]
) -> ProcessingResult:
    """
    Process an email attachment with AI classification.

    Args:
        attachment_data: Dictionary containing 'filename' and 'content'
        email_data: Dictionary with sender, subject, date, and body info

    Returns:
        ProcessingResult with classification and confidence scores

    Raises:
        ProcessingError: If attachment cannot be processed
    """
    logger.info(f"Processing attachment: {attachment_data.get('filename')}")

    try:
        # Use configuration
        max_size = config.max_attachment_size_mb

        # Your logic here
        result = await some_processing_function()

        logger.info("Processing completed successfully")
        return result

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        if config.development_mode:
            raise
        return ProcessingResult.error(str(e))
```

### Error Handling Pattern
```python
try:
    result = await risky_operation()
except SpecificException as e:
    logger.error(f"Specific error occurred: {e}")
    # Handle specific case
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    if config.development_mode:
        raise  # Re-raise in development
    return default_value
```

## 🔧 Troubleshooting

### Common Issues

**Import errors after cleanup:**
- Check if imports need to be relative (same directory) vs absolute
- Ensure `__init__.py` files exist in package directories

**Type checking errors:**
- Add type stubs: `pip install types-<package-name>`
- Use `# type: ignore` sparingly with explanation comments
- Check `pyproject.toml` for mypy configuration

**Pre-commit hook failures:**
- Run the failing hook manually: `pre-commit run <hook-name>`
- Skip problematic hooks temporarily: `git commit --no-verify`
- Update hook versions: `pre-commit autoupdate`

**Formatting conflicts:**
- Black and isort are configured to work together
- If conflicts occur, run black last: `isort . && black .`

### IDE-Specific Setup

#### PyCharm
- Install plugins: Python, .ignore, Pre-commit Hook Plugin
- Configure: Settings > Tools > External Tools (add black, isort, mypy)
- Set interpreter to your virtual environment

#### Vim/Neovim
- Use plugins: ale, black, isort, mypy
- Configure LSP with pylsp or pyright

## 📚 Additional Resources

- [PEP 8 Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

**Following these standards ensures code quality, maintainability, and team consistency!** 🎯

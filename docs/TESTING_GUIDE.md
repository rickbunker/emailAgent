# Email Agent Testing Guide

## 🚀 Quick Start

The Email Agent project is now equipped with a comprehensive testing and quality assurance system. Here's how to use it:

### 1. **One-Command Testing**
```bash
# Run all tests and quality checks
make test

# Quick testing (skip slower checks)
make test-quick

# Run with detailed output
python scripts/test_harness.py --verbose
```

### 2. **Individual Tools**
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

## 🛠️ Available Tools

### **Code Quality Tools**
- **Black** - Code formatting
- **isort** - Import sorting
- **Ruff** - Fast Python linter
- **Pylint** - Comprehensive code analysis
- **MyPy** - Type checking
- **Bandit** - Security scanning
- **Pre-commit** - Git hooks for quality control

### **Testing Framework**
- **Pytest** - Test runner with async support
- **Coverage** - Test coverage reporting
- **Pytest-mock** - Mocking utilities

## 📁 Project Configuration

### **pyproject.toml**
All tools are configured in `pyproject.toml`:
- **Black**: Line length 88, Python 3.8+ targets
- **isort**: Black-compatible profile
- **MyPy**: Strict type checking enabled
- **Pytest**: Async support, markers, coverage
- **Pylint**: Reasonable complexity limits
- **Ruff**: Modern Python linting rules

### **.pre-commit-config.yaml**
Pre-commit hooks automatically run on git commits:
- Code formatting (black, isort)
- Linting (ruff, pylint)
- Security scanning (bandit)
- Documentation style (pydocstyle)
- Secret detection

## 🧪 Test Structure

```
tests/
├── test_config.py          # Configuration system tests
├── test_web_ui_smoke.py    # Basic web UI smoke tests
└── conftest.py             # Shared test fixtures (future)
```

### **Test Categories (Pytest Markers)**
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.email` - Email interface tests
- `@pytest.mark.ai` - AI processing tests
- `@pytest.mark.web` - Web interface tests

## 🎯 Test Harness Features

The `scripts/test_harness.py` provides comprehensive testing:

### **Command Line Options**
```bash
# Basic usage
python scripts/test_harness.py

# Options
--quick       # Skip slower checks (bandit, full mypy)
--format      # Run formatters before tests
--coverage    # Generate coverage reports
--verbose     # Show detailed output
--fix         # Auto-fix issues where possible
--pre-commit-only  # Only run pre-commit checks
```

### **What It Tests**
1. **Dependency Check** - Verifies all tools are installed
2. **Code Formatting** - Black, isort (optional with --format)
3. **Linting** - Ruff (fast), Pylint (comprehensive)
4. **Type Checking** - MyPy with strict settings
5. **Security** - Bandit security scanning
6. **Tests** - Full pytest suite with optional coverage
7. **Pre-commit** - All git hooks

## 📊 Quality Standards

### **Type Safety**
- All functions must have type hints
- MyPy configured for strict checking
- Optional imports handled properly

### **Code Style**
- Black formatting (88 character lines)
- Organized imports (isort)
- Google-style docstrings required

### **Testing Requirements**
- Unit tests for all public functions
- Integration tests for key workflows
- Smoke tests for web interfaces
- Mock external dependencies

### **Security**
- Bandit security scanning
- Secret detection in pre-commit
- No hardcoded credentials

## 🔧 Development Workflow

### **Setup Development Environment**
```bash
# Install all dependencies and setup hooks
make setup

# Or manually:
pip install -r requirements-dev.txt
pre-commit install
```

### **Pre-Commit Workflow**
```bash
# Pre-commit hooks run automatically on git commit
git add .
git commit -m "Your changes"

# Or run manually on all files
make pre-commit
```

### **Testing Workflow**
```bash
# Quick check during development
make test-quick

# Full check before commit
make test

# Fix formatting issues
make format

# Check specific area
pytest tests/test_config.py -v
```

## 🚨 Common Issues & Solutions

### **Import Errors in Tests**
- **Solution**: Added `pythonpath = ["."]` to pytest config
- Tests can now import from `src` package

### **Type Checking Failures**
- **Common**: Using `|` union syntax (requires Python 3.10+)
- **Solution**: Use `Union[A, B]` instead of `A | B`
- **Common**: Missing type annotations
- **Solution**: Add type hints to all functions

### **Linting Failures**
- **Ruff**: Fast, focuses on common issues
- **Pylint**: Comprehensive, may be strict
- **Solution**: Use `--fix` option to auto-fix many issues

### **Pre-commit Hook Failures**
- **Solution**: Run `make format` before committing
- Or use `git commit --no-verify` to skip hooks (not recommended)

## 📈 Continuous Improvement

### **Coverage Goals**
- Aim for >80% test coverage
- Focus on critical business logic
- Use `make test-coverage` to generate reports

### **Adding New Tests**
1. Create test files in `tests/` directory
2. Use descriptive test names: `test_function_with_valid_input_returns_success`
3. Add appropriate pytest markers
4. Mock external dependencies

### **Tool Updates**
- Update `.pre-commit-config.yaml` versions regularly
- Run `pre-commit autoupdate` to update hook versions
- Keep `requirements-dev.txt` current

## 🎯 IDE Integration

### **VS Code Settings**
Add to `.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true
}
```

### **PyCharm Settings**
- Enable Black formatter
- Configure MyPy as external tool
- Set up pytest as default test runner

## 🔗 Quick Reference

### **Essential Commands**
```bash
make test        # Full test suite
make test-quick  # Quick tests only
make format      # Format all code
make lint        # Run linters
make clean       # Clean up files
make status      # Show project status
```

### **Files to Know**
- `pyproject.toml` - All tool configuration
- `.pre-commit-config.yaml` - Git hook configuration
- `Makefile` - Development shortcuts
- `scripts/test_harness.py` - Comprehensive testing
- `requirements-dev.txt` - Development dependencies

---

**Happy Testing! 🧪** For questions or issues, check the tool output or run with `--verbose` for detailed information.

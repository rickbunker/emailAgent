# Email Agent Development Makefile
#
# This Makefile provides convenient shortcuts for common development tasks.
# All commands are run in the virtual environment automatically.

.PHONY: help install test test-quick test-coverage lint format type-check security clean docs pre-commit setup

# Default target
help:
	@echo "Email Agent Development Commands"
	@echo "================================"
	@echo "Setup:"
	@echo "  make install       Install all dependencies (dev + prod)"
	@echo "  make setup         Complete development environment setup"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test          Run full test suite with all checks"
	@echo "  make test-quick    Run quick tests (skip slow checks)"
	@echo "  make test-coverage Run tests with coverage reports"
	@echo "  make lint          Run linting (ruff + pylint)"
	@echo "  make type-check    Run type checking (mypy)"
	@echo "  make security      Run security scan (bandit)"
	@echo "  make format        Format code (black + isort)"
	@echo "  make pre-commit    Run pre-commit hooks on all files"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Clean up generated files"
	@echo "  make clean-all     Deep clean including caches"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          Generate documentation"

# Setup and installation
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup: install
	pre-commit install
	@echo "✅ Development environment set up successfully!"
	@echo "💡 Run 'make test' to verify everything works"

# Testing commands
test:
	python scripts/test_harness.py

test-quick:
	python scripts/test_harness.py --quick

test-coverage:
	python scripts/test_harness.py --coverage

# Individual tool commands
lint:
	ruff check src tests
	pylint src --fail-under=8.0

format:
	black src tests scripts
	isort src tests scripts

type-check:
	mypy src

security:
	bandit -r src -f txt

pre-commit:
	pre-commit run --all-files

# Test runners (direct pytest)
pytest:
	pytest tests/ -v

pytest-coverage:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Cleanup commands
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf bandit-report.json

clean-all: clean
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build dist

# Documentation
docs:
	@echo "📚 Documentation generation not yet implemented"
	@echo "💡 Consider adding Sphinx documentation"

# Development helpers
check-tools:
	@echo "🔧 Checking development tools..."
	@python -c "import black, isort, mypy, pylint, ruff, bandit, pytest; print('✅ All tools available')" || echo "❌ Missing tools - run 'make install'"

# Run the Flask app for development
run-dev:
	python app.py

# Initialize memory systems
init-memory:
	@echo "🧠 Initializing Memory Systems..."
	@echo "This will load knowledge base data into Qdrant"
	@echo ""
	python scripts/initialize_memory.py

# Clean memory systems (clear Qdrant)
clean-memory:
	@echo "🗑️  Clearing Memory Systems..."
	@echo "This will delete all Qdrant collections"
	@echo ""
	python scripts/clear_qdrant.py

# Run the new FastAPI server
run-api:
	@echo "🚀 Starting FastAPI server..."
	python -m src.web_api.main

# Quick fix common issues
fix:
	python scripts/test_harness.py --fix --format

# Show project status
status:
	@echo "📊 Project Status"
	@echo "=================="
	@echo "📁 Project root: $(shell pwd)"
	@echo "🐍 Python version: $(shell python --version)"
	@echo "📦 Pip packages: $(shell pip list | wc -l) installed"
	@echo "🧪 Test files: $(shell find tests -name '*.py' | wc -l) found"
	@echo "📄 Source files: $(shell find src -name '*.py' | wc -l) found"
	@echo "✅ Git hooks: $(shell ls .git/hooks/ | grep -v sample | wc -l) installed"

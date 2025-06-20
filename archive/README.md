# Archive Directory

This directory contains outdated code and documentation from the Email Agent project that has been superseded by the new FastAPI-based architecture.

## Directory Structure

### `/old_asset_system/`
Contains the original monolithic `AssetDocumentAgent` class:
- `asset_document_agent_old_6260_lines.py` - The main 6,260-line class that handled all document processing
- `asset_document_agent_old.py` - An earlier version of the same class

### `/old_web_ui/`
Contains the original Flask-based web UI:
- `app.py` - The 5,272-line Flask application
- `human_review.py` - Human review queue functionality
- `templates/` - Old Jinja2 templates
- `static/` - CSS, JavaScript, and images

### `/old_docs/`
Contains outdated documentation that references the old architecture:
- `README_OLD.md` - The original project README
- `ASSET_DOCUMENT_MANAGEMENT_README.md` - Old asset management documentation
- `ASSET_MANAGEMENT_REWRITE_*.md` - Documentation from a previous rewrite attempt
- `EMAIL_INTERFACE_README.md` - Email interface documentation (references old code)
- `DEPLOYMENT_GUIDE.md` - Deployment guide for the old Flask app
- `TESTING_GUIDE.md` - Testing documentation for the old system
- `LOGGING_GUIDE.md` - Logging guide with old code examples
- `DEVELOPMENT_SETUP.md` - Development setup for the old architecture

## Why These Were Archived

As part of the major refactoring from a monolithic Flask application to a modular FastAPI + HTMX architecture:

1. **Code Modernization**: The old `AssetDocumentAgent` was a 6,260-line monolith that mixed business logic, data access, and presentation concerns
2. **Architecture Improvement**: Moving from tightly coupled Flask views to a service-oriented architecture with clear separation of concerns
3. **Documentation Accuracy**: Old docs referenced classes and patterns that no longer exist in the new architecture

## Current Documentation

For current documentation, see:
- `/docs/REFACTORING_PROGRESS.md` - Current refactoring status
- `/docs/NEW_API_DESIGN.md` - New API architecture
- `/docs/CODING_STANDARDS.md` - Current development standards

## Note

These files are kept for historical reference and to help understand the evolution of the project. They should not be used as reference for current development.

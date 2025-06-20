# Archived Data and Test Files

This directory contains test data and runtime files from the old system that are no longer needed.

## Contents

### `/assets/`
Test documents organized by asset IDs:
- `i3_verticals` - Test documents for i3 Verticals
- `Trimble_BoA` - Test documents for Trimble Bank of America
- `Gray_IV` - Test documents for Gray IV
- Other test asset folders

### `/data_directory/`
Runtime data from the old system:
- `processed_emails.json` - Email processing history
- `processing_runs.json` - Processing run logs
- `human_review_queue.json` - Items pending human review
- Subdirectories for assets, quarantine, unmatched files, etc.

## Note
This data was archived during the FastAPI refactoring. It represents test data and runtime state from the old Flask-based system and should not be used with the new architecture.

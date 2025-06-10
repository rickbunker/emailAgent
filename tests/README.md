# Email Agent Tests

This directory contains all test files for the Email Agent system.

## Test Categories

### Authentication Tests
- `test_msgraph_connection.py` - Test Microsoft Graph connection (old method)
- `test_msgraph_web_auth.py` - Test web-based Microsoft Graph authentication 
- `test_msgraph_integration.py` - Test full Microsoft Graph integration

### Performance Tests
- `test_100_real_emails.py` - Process 100 real emails through the complete pipeline
- `test_emails_with_attachments.py` - Test email processing with attachments (performance focus)

### Feature Tests
- `simple_phase3_test.py` - Basic Phase 3 document classification test
- `test_phase3_classification.py` - Complete Phase 3 classification and intelligence tests

## Running Tests

### Individual Tests
Run any test from the project root directory:

```bash
# Microsoft Graph authentication
python tests/test_msgraph_web_auth.py

# Document classification
python tests/test_phase3_classification.py

# Performance testing
python tests/test_100_real_emails.py
```

### Prerequisites

1. **Microsoft Graph Tests**: Require `examples/msgraph_credentials.json` with Azure app credentials
2. **Gmail Tests**: Require `examples/gmail_credentials.json` with Google API credentials  
3. **Performance Tests**: Require actual email accounts with emails/attachments
4. **ClamAV Tests**: Require ClamAV installed and running

### Test Configuration

Most tests automatically configure themselves, but you may need to:

1. Set up email credentials in the `examples/` directory
2. Ensure Qdrant vector database is running (for memory tests)
3. Have ClamAV installed for virus scanning tests

## Test Status

- ✅ **Authentication**: Microsoft Graph web auth working
- ✅ **Document Classification**: Phase 3 AI classification working  
- ✅ **Virus Scanning**: ClamAV integration working
- ⚠️ **Performance**: Slow processing identified, needs optimization
- 🔄 **Memory Integration**: Qdrant integration working but needs performance tuning

## Adding New Tests

When adding new tests:

1. Place them in this `tests/` directory
2. Use the import pattern: `sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))`
3. Follow the naming convention: `test_<functionality>.py`
4. Add documentation to this README 
# 🛠️ Scripts Directory

This directory contains development, debugging, and utility scripts for the Email Agent project.

## 📁 Contents

### 🔍 **Debug Scripts**
- **`debug_msgraph.py`** - Microsoft Graph API debugging and troubleshooting
- **`test_msgraph_simple.py`** - Simple Microsoft Graph connection testing

### ⚡ **Performance Scripts**  
- **`test_parallel_processing.py`** - Performance testing for parallel email processing

### 🔧 **Utility Scripts**
- **`grabsource.sh`** - Source code extraction utility
- **`test-virus.txt`** - EICAR test virus file for antivirus testing

## 🚀 Usage

### Run Debug Scripts
```bash
# Test Microsoft Graph connection
python scripts/test_msgraph_simple.py

# Debug Microsoft Graph API issues
python scripts/debug_msgraph.py

# Test parallel processing performance
python scripts/test_parallel_processing.py
```

### Utility Scripts
```bash
# Extract source code (if needed)
./scripts/grabsource.sh

# Test virus scanning (use with caution)
# The test-virus.txt file contains the EICAR test string
```

## ⚠️ **Important Notes**

- **`test-virus.txt`** contains the EICAR test virus signature - do not copy or execute
- Debug scripts may require credentials setup (see main project README)
- Performance scripts may take significant time to complete
- All scripts should be run from the project root directory

## 🔗 **Related Documentation**

- Main project setup: `../README.md`
- Microsoft Graph setup: `../MSGRAPH_SETUP.md`
- Testing documentation: `../tests/README.md` 
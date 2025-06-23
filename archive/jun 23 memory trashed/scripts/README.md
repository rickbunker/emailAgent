# 🛠️ Scripts Directory

This directory contains development, debugging, and utility scripts for the Email Agent project.

## 📁 Contents

### 🔍 **Debug Scripts**
- **`debug_msgraph.py`** - Comprehensive Microsoft Graph API debugging and troubleshooting utility
  - Tests authentication, mailbox access, email retrieval, and permissions
  - Provides detailed diagnostic information and common solutions
  - Usage: `python scripts/debug_msgraph.py [--test-auth|--test-mailbox|--test-emails] [--verbose]`

- **`test_msgraph_simple.py`** - Simple Microsoft Graph connection testing
  - Quick validation script for basic connectivity
  - Minimal output for rapid troubleshooting
  - Usage: `python scripts/test_msgraph_simple.py`

### ⚡ **Performance Scripts**
- **`test_parallel_processing.py`** - Comprehensive parallel email processing performance testing
  - Benchmarks sequential vs parallel processing performance
  - Tests memory usage, concurrency scaling, and throughput
  - Usage: `python scripts/test_parallel_processing.py [--emails N] [--concurrency N] [--with-attachments]`

### 🧪 **Testing Infrastructure**
- **`test_harness.py`** - Main test harness for code quality and validation
  - Runs linting (ruff, pylint), type checking (mypy), security scans (bandit)
  - Executes pytest test suite with optional coverage reporting
  - Usage: `python scripts/test_harness.py [--quick] [--coverage] [--verbose] [--fix]`

### 🔧 **Utility Scripts**
- **`grabsource.sh`** - Source code extraction and packaging utility
  - Creates clean source distributions excluding build artifacts
  - Supports tar, zip, and copy formats with optional inclusions
  - Usage: `./scripts/grabsource.sh [--output DIR] [--format tar|zip|copy] [--include-docs|--include-tests]`

- **`test-virus.txt`** - EICAR test virus file for antivirus testing
  - Contains the standard EICAR test signature for validating ClamAV functionality
  - **⚠️ HARMLESS TEST FILE** - Safe to use, not a real virus

## 🚀 Usage Examples

### Quick Microsoft Graph Test
```bash
# Simple connectivity test
python scripts/test_msgraph_simple.py

# Comprehensive debugging
python scripts/debug_msgraph.py --verbose
```

### Performance Testing
```bash
# Basic performance test
python scripts/test_parallel_processing.py

# Comprehensive test with attachments
python scripts/test_parallel_processing.py --emails 20 --concurrency 10 --with-attachments
```

### Code Quality Testing
```bash
# Quick test suite
make test-quick
# Or directly: python scripts/test_harness.py --quick

# Full test suite with coverage
make test
# Or directly: python scripts/test_harness.py --coverage
```

### Source Code Extraction
```bash
# Basic source export
./scripts/grabsource.sh

# Full export with documentation and tests
./scripts/grabsource.sh --include-docs --include-tests --format zip --output ./exports

# Copy source to directory
./scripts/grabsource.sh --format copy --output /tmp/emailagent_backup
```

## ⚠️ **Important Notes**

- **`test-virus.txt`** contains the EICAR test virus signature - **harmless for testing only**
- All debug scripts require proper Microsoft Graph credentials setup
- Performance scripts may take significant time for large test sets
- Test harness is integrated with the Makefile for convenient usage
- All scripts should be run from the project root directory
- Source extraction script automatically excludes sensitive configuration files

## 🔗 **Integration with Development Workflow**

These scripts are integrated into the development workflow:

- **Makefile targets** use `test_harness.py` for quality assurance
- **CI/CD pipelines** can leverage these scripts for automated testing
- **Performance monitoring** can use the benchmarking scripts
- **Debugging workflows** are streamlined with the Graph debugging tools
- **Source distribution** is simplified with the extraction utility

## 🔗 **Related Documentation**

- Main project setup: `../README.md`
- Microsoft Graph setup: `../docs/MSGRAPH_SETUP.md`
- Testing documentation: `../docs/TESTING_GUIDE.md`
- Development setup: `../docs/DEVELOPMENT_SETUP.md`

## Memory System Initialization

### ⚠️ IMPORTANT: Memory Initialization vs. Application Startup

**Memory initialization is SEPARATE from normal application startup:**

- **Normal Application Startup**: Reads existing patterns from persistent memory (Qdrant)
- **Memory Initialization**: Only run when explicitly needed to reset or initially populate memory

### When to Initialize Memory

Memory initialization should ONLY be run in these specific scenarios:

1. **Initial System Deployment** - First-time setup on a new environment
2. **Testing Environment Reset** - Clearing test data to start fresh
3. **Knowledge Base Updates** - After significant changes to JSON pattern files
4. **Emergency Reset** - Recovering from corrupted memory state

### When NOT to Initialize Memory

**NEVER run initialization in production unless absolutely necessary because:**
- It will reset patterns to baseline versions
- All learned improvements from human feedback will be preserved in episodic memory
- But refined pattern effectiveness scores will be lost
- The system will need to re-learn optimizations

### Production Memory Persistence

In production, the memory system:
- **Persists across application restarts** (stored in Qdrant)
- **Continuously learns** from human feedback
- **Refines pattern effectiveness** over time
- **Grows in intelligence** without manual intervention

The JSON files serve as version-controlled baselines, but the living memory in Qdrant becomes increasingly valuable over time.

### Initialization Scripts

#### `initialize_memory.py`
Main script for setting up or resetting the memory system.

```bash
# First-time setup
python scripts/initialize_memory.py

# Reset to baseline patterns (preserves episodic learning)
python scripts/initialize_memory.py --reset
```

**When to use:**
- Initial system deployment
- After updating JSON pattern files
- To reset to baseline patterns while preserving learned feedback

#### Individual Pattern Loaders

These scripts load specific pattern types into memory:

- `load_spam_patterns.py` - Spam detection patterns
- `load_contact_patterns.py` - Contact extraction patterns
- `load_asset_types.py` - Asset types and document categories
- `load_all_patterns.py` - Loads all patterns (used by initialize_memory.py)

**Note:** These are typically called by `initialize_memory.py`, not directly.

## Development Workflow

### Adding New Patterns

1. Update the appropriate JSON file in `/knowledge`
2. Test the changes locally
3. Commit the JSON changes to version control
4. Run `python scripts/initialize_memory.py` to load into memory
5. Agents will now use the new patterns from memory

### Testing Pattern Changes

```bash
# Load patterns into a test environment
python scripts/load_spam_patterns.py  # or other specific loader

# Verify patterns loaded correctly
# Check the script output for confirmation
```

## Architecture Principles

1. **JSON files = Source Code**: Version controlled, human-readable pattern definitions
2. **Memory = Runtime**: Where agents read patterns during operation
3. **Initialization = Compilation**: Converting JSON to memory entries
4. **Learning = Runtime Updates**: Human feedback updates memory, not JSON files

This separation ensures:
- Clean version control of baseline patterns
- Runtime learning without modifying source files
- Easy reset to baseline when needed
- Clear audit trail of pattern changes

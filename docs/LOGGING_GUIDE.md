# Asset Document Management System Logging Guide

A sophisticated, decorator-based logging system designed to provide detailed insights into the **Memory-Driven Asset Document Processing Agent** operations.

## 🎯 **System Overview**

The logging system provides comprehensive observability for all components of the asset document management system, from email processing through memory-driven learning to human review workflows.

### **Key Features**

- 🎯 **Decorator-based logging** - Easy to apply to any function or method
- 📊 **Multi-level logging** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- 🔒 **Security-aware** - Automatically redacts sensitive data
- ⚡ **Async support** - Works with both sync and async functions
- ⏱️ **Performance tracking** - Function execution timing and memory usage
- 🧠 **Memory system integration** - Tracks learning and pattern storage
- 📄 **Asset processing tracking** - Complete document processing pipeline
- 🌐 **Web UI integration** - Human review and API request logging
- 🔄 **Structured logging** - JSON format for analysis and monitoring

## 🚀 **Quick Start**

### **1. Basic Asset Processing Logging**

```python
from src.utils.logging_system import get_logger, log_function

# Get a logger for your module
logger = get_logger(__name__)

@log_function()
async def process_asset_document(attachment_data: dict, email_data: dict):
    """Process asset document with comprehensive logging."""
    logger.info(f"Processing document: {attachment_data['filename']}")

    # Processing logic here
    result = {
        "status": "success",
        "document_category": "rent_roll",
        "confidence": 0.89,
        "asset_id": "asset_123"
    }

    logger.info(f"Classification: {result['document_category']} "
               f"(confidence: {result['confidence']:.3f})")
    return result

# When called, this will log:
# INFO - 🔵 ENTER process_asset_document(attachment_data={'filename': 'rent_roll.xlsx', ...}, email_data={...})
# INFO - Processing document: rent_roll.xlsx
# INFO - Classification: rent_roll (confidence: 0.890)
# DEBUG - 🟢 EXIT process_asset_document -> {'status': 'success', ...} [0.245s]
```

### **2. Memory System Logging**

```python
from src.utils.logging_system import log_function, get_logger

class ProceduralMemory:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.ProceduralMemory")

    @log_function()
    async def learn_classification_pattern(
        self,
        filename: str,
        email_subject: str,
        predicted_category: str,
        confidence: float
    ):
        """Learn from classification with detailed logging."""
        self.logger.info(f"🧠 Learning pattern: {predicted_category} from {filename}")

        # Store pattern logic
        pattern_id = "pattern_abc123"

        self.logger.info(f"✅ Pattern stored: {pattern_id} (confidence: {confidence:.3f})")
        return pattern_id

# Logs:
# INFO - 🔵 ENTER learn_classification_pattern(filename=rent_roll.xlsx, ...)
# INFO - 🧠 Learning pattern: rent_roll from rent_roll.xlsx
# INFO - ✅ Pattern stored: pattern_abc123 (confidence: 0.890)
# DEBUG - 🟢 EXIT learn_classification_pattern -> pattern_abc123 [0.156s]
```

### **3. Production Configuration**

```python
from src.utils.logging_system import LogConfig, configure_logging

# Production configuration for asset processing
production_config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_to_stdout=False,  # File logging only in production
    log_file="/var/log/asset-document-agent/app.log",
    log_arguments=False,  # Don't log arguments in production for privacy
    log_return_values=False,
    max_file_size=100 * 1024 * 1024,  # 100MB
    backup_count=10,
    enable_json_logging=True,  # Structured logging for analysis
    include_memory_metrics=True  # Track memory usage
)

configure_logging(production_config)
```

## 📊 **Logging Levels and Usage**

### **INFO Level - Production Monitoring**
Perfect for tracking asset processing flow and system health:

```python
from src.utils.logging_system import log_info

@log_info
async def classify_document(filename: str, content: bytes):
    """Classify document with minimal logging for production."""
    # Only logs: "🔵 ENTER classify_document"
    return {"category": "financial_statements", "confidence": 0.92}
```

### **DEBUG Level - Development and Troubleshooting**
Comprehensive logging for development and debugging:

```python
from src.utils.logging_system import log_debug

@log_debug
async def match_asset_from_content(email_subject: str, known_assets: list):
    """Match asset with detailed logging for debugging."""
    # Logs entry with arguments, exit with return value, and timing
    return [("asset_123", 0.95), ("asset_456", 0.78)]
```

### **Custom Logging Levels**
Asset-specific logging levels for different scenarios:

```python
from src.utils.logging_system import log_function

# High-detail logging for memory operations
@log_function(level="DEBUG", log_memory_usage=True)
async def store_learning_pattern(pattern_data: dict):
    """Store learning pattern with memory tracking."""
    return {"pattern_id": "abc123", "stored": True}

# Minimal logging for frequent operations
@log_function(level="INFO", log_arguments=False, log_timing=False)
async def check_duplicate(file_hash: str):
    """Check for duplicates with minimal logging overhead."""
    return None  # No duplicate found
```

## 🏗️ **Component Integration Examples**

### **Asset Document Agent**

```python
from src.utils.logging_system import log_function, get_logger

class AssetDocumentAgent:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.AssetDocumentAgent")

    @log_function()
    async def enhanced_process_attachment(
        self,
        attachment_data: dict,
        email_data: dict
    ):
        """Enhanced processing with memory-driven classification."""
        filename = attachment_data.get('filename', 'unknown')
        self.logger.info(f"📄 Processing: {filename}")

        # Security scanning
        self.logger.info("🔒 Starting security scan")
        security_result = await self.security_scan(attachment_data['content'])

        if security_result['is_clean']:
            self.logger.info("✅ Security scan passed")
        else:
            self.logger.warning(f"⚠️ Security threat detected: {security_result['threat']}")
            return ProcessingResult(status=ProcessingStatus.QUARANTINED)

        # Memory-driven classification
        self.logger.info("🧠 Starting memory-driven classification")
        classification_result = await self.classify_with_memory(
            filename, email_data['subject'], email_data['body']
        )

        self.logger.info(
            f"📊 Classification: {classification_result['category']} "
            f"(confidence: {classification_result['confidence']:.3f})"
        )

        # Asset matching
        self.logger.info("🎯 Starting asset matching")
        asset_matches = await self.identify_asset_from_content(
            email_data['subject'], email_data['body'], filename
        )

        if asset_matches:
            best_match = asset_matches[0]
            self.logger.info(
                f"🏢 Asset match: {best_match[0][:8]} "
                f"(confidence: {best_match[1]:.3f})"
            )
        else:
            self.logger.info("❌ No asset matches found")

        return ProcessingResult(status=ProcessingStatus.SUCCESS)

    @log_function()
    async def learn_from_human_feedback(
        self,
        filename: str,
        system_prediction: str,
        human_correction: str
    ):
        """Learn from human feedback with detailed logging."""
        self.logger.info(
            f"👥 Learning from feedback: {system_prediction} -> {human_correction}"
        )

        pattern_id = await self.procedural_memory.learn_from_human_feedback(
            filename, system_prediction, human_correction
        )

        self.logger.info(f"✅ Human feedback learned: {pattern_id}")
        return pattern_id
```

### **Email Interface Logging**

```python
from src.utils.logging_system import log_function, get_logger

class GmailInterface:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.GmailInterface")

    @log_function()
    async def connect(self, credentials: dict):
        """Connect to Gmail with comprehensive logging."""
        self.logger.info("🔐 Initiating Gmail connection")

        try:
            # Authentication logic
            self.logger.info("✅ Gmail authentication successful")
            return True
        except Exception as e:
            self.logger.error(f"❌ Gmail authentication failed: {e}")
            raise

    @log_function()
    async def list_emails(self, criteria: EmailSearchCriteria):
        """List emails with asset-focused logging."""
        self.logger.info(
            f"📧 Searching emails: {criteria.max_results} max, "
            f"attachments: {criteria.has_attachments}"
        )

        emails = []  # Email fetching logic

        attachment_count = sum(len(email.attachments) for email in emails)
        self.logger.info(
            f"📊 Found {len(emails)} emails, {attachment_count} total attachments"
        )

        return emails

    @log_function()
    async def process_mailbox_emails(self, max_emails: int = 20):
        """Process mailbox with parallel processing logging."""
        self.logger.info(f"🔄 Starting mailbox processing (max: {max_emails})")

        start_time = time.time()

        # Parallel processing logic
        results = await self.process_emails_parallel(emails)

        processing_time = time.time() - start_time
        successful = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)

        self.logger.info(
            f"🏁 Mailbox processing complete: {successful}/{len(results)} successful "
            f"in {processing_time:.1f}s"
        )

        return results
```

### **Security Service Logging**

```python
from src.utils.logging_system import log_function, get_logger

class SecurityService:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.SecurityService")

    @log_function()
    async def scan_file_antivirus(self, file_content: bytes, filename: str):
        """Antivirus scanning with security-focused logging."""
        file_size = len(file_content)
        self.logger.info(f"🔍 Scanning {filename} ({file_size:,} bytes)")

        if not self.clamscan_path:
            self.logger.warning("⚠️ ClamAV not available - skipping antivirus scan")
            return True, None

        scan_start = time.time()

        # Scanning logic here
        is_clean = True
        threat_name = None

        scan_time = time.time() - scan_start

        if is_clean:
            self.logger.info(f"✅ File clean: {filename} (scanned in {scan_time:.3f}s)")
        else:
            self.logger.error(
                f"🚨 THREAT DETECTED: {filename} -> {threat_name} "
                f"(scanned in {scan_time:.3f}s)"
            )

        return is_clean, threat_name

    @log_function()
    def calculate_file_hash(self, file_content: bytes):
        """Calculate file hash with security logging."""
        if not file_content:
            self.logger.error("❌ Empty file content for hash calculation")
            raise ValueError("File content cannot be empty")

        file_hash = hashlib.sha256(file_content).hexdigest()
        self.logger.debug(f"🔐 File hash: {file_hash[:16]}...")

        return file_hash
```

### **Web UI Logging**

```python
from src.utils.logging_system import log_function, get_logger
from flask import request

class WebUILogger:
    def __init__(self):
        self.logger = get_logger(f"{__name__}.WebUI")

    @log_function()
    def api_process_emails(self):
        """API endpoint logging for email processing."""
        interface_type = request.json.get('interface_type', 'gmail')
        max_emails = request.json.get('max_emails', 20)

        self.logger.info(
            f"🌐 API request: process emails ({interface_type}, max: {max_emails})"
        )

        # Processing logic
        results = {"processed": 15, "errors": 0}

        self.logger.info(
            f"📊 API response: {results['processed']} processed, "
            f"{results['errors']} errors"
        )

        return results

    @log_function()
    def resolve_human_review(self, review_id: str):
        """Human review resolution logging."""
        correction_data = request.json

        self.logger.info(
            f"👥 Human review resolved: {review_id} "
            f"({correction_data['system_prediction']} -> "
            f"{correction_data['human_correction']})"
        )

        # Learning integration
        self.logger.info(f"🧠 Learning from human feedback: {review_id}")

        return {"status": "resolved", "learned": True}

    @log_function()
    def asset_management_activity(self, action: str, asset_data: dict):
        """Asset management activity logging."""
        asset_name = asset_data.get('deal_name', 'unknown')

        self.logger.info(f"🏢 Asset {action}: {asset_name}")

        if action == "created":
            self.logger.info(
                f"📋 New asset: {asset_data.get('asset_type')} with "
                f"{len(asset_data.get('identifiers', []))} identifiers"
            )

        return {"action": action, "asset": asset_name}
```

### **Procedural Memory Detailed Logging**

```python
from src.utils.logging_system import log_function, get_logger

class ProceduralMemory:
    def __init__(self, qdrant_client):
        self.logger = get_logger(f"{__name__}.ProceduralMemory")
        self.qdrant = qdrant_client

    @log_function()
    async def classify_document(
        self,
        filename: str,
        email_subject: str,
        email_body: str
    ):
        """Document classification with memory pattern matching."""
        self.logger.info(f"🔍 Classifying: {filename}")

        # Find similar patterns
        self.logger.debug("🔍 Searching for similar patterns in memory")
        similar_patterns = await self.find_similar_patterns(
            filename, email_subject, email_body
        )

        if similar_patterns:
            best_pattern = similar_patterns[0]
            self.logger.info(
                f"📋 Found {len(similar_patterns)} similar patterns, "
                f"best: {best_pattern.category} (similarity: {best_pattern.similarity:.3f})"
            )

            return best_pattern.category, best_pattern.confidence
        else:
            self.logger.info("❌ No similar patterns found in memory")
            return "unknown", 0.0

    @log_function()
    async def learn_classification_pattern(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        predicted_category: str,
        confidence: float,
        source: str = "auto_learning"
    ):
        """Store learning pattern with comprehensive logging."""
        pattern_id = str(uuid.uuid4())

        self.logger.info(
            f"🧠 Storing learning pattern: {predicted_category} "
            f"(confidence: {confidence:.3f}, source: {source})"
        )

        # Create embeddings
        self.logger.debug("🔢 Generating embeddings for pattern storage")

        # Store in Qdrant
        try:
            # Storage logic here
            self.logger.info(f"✅ Pattern stored successfully: {pattern_id[:8]}")

            # Update statistics
            self.stats['patterns_learned'] += 1
            self.logger.debug(
                f"📊 Total patterns in memory: {self.stats['patterns_learned']}"
            )

            return pattern_id

        except Exception as e:
            self.logger.error(f"❌ Failed to store pattern: {e}")
            raise

    @log_function()
    async def learn_from_human_feedback(
        self,
        filename: str,
        system_prediction: str,
        human_correction: str
    ):
        """Learn from human corrections with priority logging."""
        self.logger.info(
            f"👥 Human feedback: {system_prediction} -> {human_correction} "
            f"for {filename}"
        )

        # Higher priority for human feedback patterns
        confidence = 0.95  # High confidence for human corrections
        source = "human_feedback"

        pattern_id = await self.learn_classification_pattern(
            filename, "", "", human_correction, confidence, source
        )

        # Track human feedback statistics
        self.stats['human_corrections'] += 1
        correction_rate = self.stats['human_corrections'] / max(self.stats['classifications'], 1)

        self.logger.info(
            f"📈 Human feedback stored: {pattern_id[:8]} "
            f"(correction rate: {correction_rate:.1%})"
        )

        return pattern_id
```

## 🔧 **Advanced Configuration**

### **Environment-Specific Configurations**

```python
from src.utils.logging_system import LogConfig

# Development configuration
development_config = LogConfig(
    level="DEBUG",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/asset_agent_dev.log",
    log_arguments=True,
    log_return_values=True,
    log_execution_time=True,
    enable_json_logging=False,  # Human-readable for development
    include_memory_metrics=True,
    log_asset_processing_details=True
)

# Production configuration
production_config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_to_stdout=False,
    log_file="/var/log/asset-document-agent/app.log",
    max_file_size=100 * 1024 * 1024,  # 100MB
    backup_count=10,
    log_arguments=False,  # Privacy in production
    log_return_values=False,
    enable_json_logging=True,  # Structured for analysis
    include_performance_metrics=True,
    compress_rotated_logs=True
)

# Testing configuration
testing_config = LogConfig(
    level="DEBUG",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/test_asset_agent.log",
    enable_test_mode=True,  # Special test markers
    log_memory_leaks=True
)

# High-performance configuration
performance_config = LogConfig(
    level="WARNING",  # Minimal logging for max performance
    log_to_file=True,
    log_to_stdout=False,
    log_arguments=False,
    log_return_values=False,
    log_execution_time=False,
    enable_async_logging=True,  # Non-blocking logging
    buffer_size=10000  # Batch log writes
)
```

### **Asset-Specific Logging Configuration**

```python
# Asset processing focused configuration
asset_processing_config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_file="/var/log/asset-document-agent/asset_processing.log",

    # Asset-specific settings
    log_asset_processing_details=True,
    log_memory_learning=True,
    log_human_feedback=True,
    log_security_events=True,
    log_performance_metrics=True,

    # Custom log formats for asset processing
    include_asset_context=True,  # Include asset IDs in logs
    include_document_types=True,  # Include document categories
    include_confidence_scores=True,  # Include ML confidence

    # Privacy and security
    redact_email_content=True,
    redact_file_content=True,
    log_data_flow=True  # Track document movement
)

# Memory system specific configuration
memory_config = LogConfig(
    level="DEBUG",
    log_file="/var/log/asset-document-agent/memory_system.log",

    # Memory-specific logging
    log_vector_operations=True,
    log_pattern_matching=True,
    log_learning_events=True,
    log_similarity_scores=True,

    # Performance tracking
    log_query_performance=True,
    log_memory_usage=True,
    log_collection_stats=True
)
```

## 🔒 **Security and Privacy Features**

### **Sensitive Data Protection**

The logging system automatically protects sensitive information relevant to asset processing:

```python
@log_function()
async def process_confidential_document(
    filename: str,
    content: bytes,
    api_key: str,
    email_content: str,
    financial_data: dict
):
    """Process confidential document with automatic data redaction."""
    # Logs: process_confidential_document(
    #   filename=financial_report.pdf,
    #   content=<bytes REDACTED>,
    #   api_key=<str REDACTED>,
    #   email_content=<str REDACTED>,
    #   financial_data=<dict REDACTED>
    # )
    return {"processed": True}
```

**Default Sensitive Keys for Asset Processing:**
- `password`, `token`, `secret`, `key`, `credential`, `auth`
- `access_token`, `refresh_token`, `client_secret`, `api_key`
- `content`, `body`, `email_content`, `file_content`
- `financial_data`, `personal_info`, `ssn`, `account_number`
- `private_key`, `certificate`, `signature`

**Custom Sensitive Keys:**
```python
asset_config = LogConfig(
    sensitive_keys=[
        'password', 'token', 'secret', 'private_key',
        'financial_data', 'tenant_info', 'loan_details',
        'borrower_data', 'investment_details', 'portfolio_data'
    ]
)
```

### **Audit Trail Logging**

```python
from src.utils.logging_system import audit_log

@audit_log("DOCUMENT_PROCESSED")
async def process_asset_document(attachment_data: dict, email_data: dict):
    """Process document with audit trail."""
    # Creates audit entry: DOCUMENT_PROCESSED by user_id at timestamp
    return processing_result

@audit_log("HUMAN_REVIEW_RESOLVED")
async def resolve_human_review(review_id: str, user_id: str, correction: dict):
    """Resolve human review with audit trail."""
    # Creates audit entry: HUMAN_REVIEW_RESOLVED by user_id at timestamp
    return resolution_result
```

## 📈 **Performance Monitoring**

### **Execution Time Tracking**

```python
@log_function(track_performance=True)
async def memory_intensive_operation(large_dataset: list):
    """Track performance for memory-intensive operations."""
    # Automatically logs:
    # - Execution time
    # - Memory usage before/after
    # - CPU usage during execution
    return processed_data

# Example output:
# INFO - 🔵 ENTER memory_intensive_operation [Memory: 245MB, CPU: 12%]
# INFO - 🟢 EXIT memory_intensive_operation [0.156s] [Memory: 312MB (+67MB), CPU: 18%]
```

### **Parallel Processing Monitoring**

```python
@log_function(track_concurrency=True)
async def process_emails_parallel(emails: list, max_concurrent: int = 5):
    """Monitor parallel processing performance."""
    # Logs concurrent operation metrics
    # - Active workers
    # - Queue depth
    # - Throughput rate
    return results
```

## 🧪 **Testing and Debugging**

### **Debug Mode Features**

```python
# Enable debug mode for detailed troubleshooting
debug_config = LogConfig(
    level="DEBUG",
    enable_debug_mode=True,
    log_stack_traces=True,
    log_variable_states=True,
    log_memory_allocations=True
)

@log_function(debug_mode=True)
async def troubleshoot_classification(filename: str, content: str):
    """Debug classification issues with detailed logging."""
    # Logs intermediate steps, variable states, and decision paths
    return classification_result
```

### **Test Environment Logging**

```python
# Test-specific logging configuration
test_config = LogConfig(
    level="DEBUG",
    log_file="logs/test_run.log",
    enable_test_markers=True,  # Add [TEST] prefix to all logs
    log_test_data=True,
    capture_test_metrics=True
)

@log_function(test_mode=True)
async def test_asset_matching():
    """Test asset matching with test-specific logging."""
    # Adds test context and captures test metrics
    return test_results
```

## 📊 **Log Analysis and Monitoring**

### **Structured Logging for Analysis**

```python
# Enable JSON logging for analysis tools
analysis_config = LogConfig(
    enable_json_logging=True,
    include_correlation_ids=True,  # Track related operations
    include_user_context=True,
    include_asset_context=True
)

# Example JSON log entry:
{
    "timestamp": "2024-03-15T10:30:45.123Z",
    "level": "INFO",
    "module": "asset_document_agent",
    "function": "process_attachment",
    "message": "Document classified",
    "correlation_id": "req_abc123",
    "asset_id": "asset_456",
    "document_category": "rent_roll",
    "confidence": 0.89,
    "processing_time_ms": 245,
    "memory_usage_mb": 67
}
```

### **Log Aggregation and Search**

```python
# Search logs for specific patterns
from src.utils.logging_system import LogAnalyzer

analyzer = LogAnalyzer()

# Find classification errors
errors = analyzer.search_logs(
    level="ERROR",
    module="asset_document_agent",
    time_range="last_24h"
)

# Performance analysis
slow_operations = analyzer.find_slow_operations(
    threshold_ms=1000,
    time_range="last_week"
)

# Memory pattern analysis
learning_stats = analyzer.analyze_memory_learning(
    time_range="last_month"
)
```

## 🔗 **Integration with Monitoring Tools**

### **Prometheus Metrics Integration**

```python
from src.utils.logging_system import MetricsLogger

metrics_logger = MetricsLogger()

@log_function(emit_metrics=True)
async def process_document_with_metrics(attachment_data: dict):
    """Process document and emit Prometheus metrics."""
    # Automatically emits:
    # - documents_processed_total counter
    # - processing_time_seconds histogram
    # - classification_confidence histogram
    # - memory_usage_bytes gauge
    return result
```

### **ELK Stack Integration**

```python
# Configure for Elasticsearch/Logstash
elk_config = LogConfig(
    enable_json_logging=True,
    log_format="elk",
    include_elk_metadata=True,
    elk_index_pattern="asset-document-agent-{date}"
)
```

## 📋 **Best Practices**

### **1. Strategic Logging Placement**
```python
# Log at component boundaries
@log_function()  # Always log entry/exit
async def process_attachment(data):
    pass

# Log business logic decisions
def classify_document(filename):
    if confidence > 0.8:
        logger.info(f"High confidence classification: {category}")
    else:
        logger.warning(f"Low confidence classification: {category} ({confidence:.3f})")

# Log external service interactions
async def store_in_qdrant(data):
    logger.info("Storing pattern in Qdrant")
    # ... storage logic
    logger.info("Pattern stored successfully")
```

### **2. Context-Rich Logging**
```python
# Include relevant context
logger.info(
    f"Processing {filename} from {sender_email} "
    f"(asset: {asset_id}, confidence: {confidence:.3f})"
)

# Use correlation IDs for related operations
correlation_id = str(uuid.uuid4())
logger.info(f"[{correlation_id}] Starting email processing pipeline")
```

### **3. Performance-Conscious Logging**
```python
# Avoid expensive operations in log statements
# Bad:
logger.debug(f"Processing data: {expensive_computation(data)}")

# Good:
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Processing data: {expensive_computation(data)}")

# Use lazy evaluation
logger.debug("Processing data: %s", lambda: expensive_computation(data))
```

### **4. Security-First Logging**
```python
# Never log sensitive data directly
# Bad:
logger.info(f"User password: {password}")

# Good:
logger.info(f"User authentication successful for {username}")

# Use audit logs for security events
@audit_log("SECURITY_SCAN_COMPLETED")
async def scan_file(filename, content):
    pass
```

## 📞 **Production Support**

### **Log Monitoring Checklist**
- [ ] Log files rotating properly
- [ ] No sensitive data in logs
- [ ] Error rates within acceptable limits
- [ ] Performance metrics tracked
- [ ] Audit trails complete
- [ ] Debug information available for troubleshooting

### **Emergency Debugging**
```python
# Enable emergency debug mode
from src.utils.logging_system import enable_emergency_debug

# Temporarily increase logging detail
enable_emergency_debug(
    duration_minutes=30,
    include_memory_dumps=True,
    include_stack_traces=True
)
```

### **Log Analysis Commands**
```bash
# Monitor real-time processing
tail -f /var/log/asset-document-agent/app.log | grep "Processing"

# Find classification errors
grep "ERROR.*classification" /var/log/asset-document-agent/*.log

# Monitor memory learning
grep "Learning pattern" /var/log/asset-document-agent/*.log | tail -20

# Check performance issues
grep "SLOW" /var/log/asset-document-agent/*.log
```

---

**🎯 The Asset Document Management System logging provides complete observability into every aspect of the intelligent document processing pipeline!**

From email ingestion through memory-driven learning to human review, every operation is logged with appropriate detail for monitoring, debugging, and continuous improvement.

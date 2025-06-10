# Email Agent Logging System Guide

A comprehensive, decorator-based logging system designed to provide detailed insights into the email agent's operations.

## Features

- **Decorator-based**: Easy to apply to any function or method
- **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Dual output**: Log to files, console, or both
- **Sensitive data protection**: Automatically redacts passwords, tokens, and secrets
- **Async support**: Works with both sync and async functions
- **Execution timing**: Track function performance
- **Exception logging**: Automatic exception capture and logging
- **Configurable**: Flexible configuration for different environments

## Quick Start

### 1. Basic Usage

```python
from utils.logging_system import get_logger, log_function

# Get a logger for your module
logger = get_logger(__name__)

@log_function()
def process_email(email_id: str, sender: str):
    logger.info(f"Processing email from {sender}")
    return {"processed": True, "email_id": email_id}

# When called, this will log:
# INFO - 🔵 ENTER process_email(email_id=email_001, sender=user@example.com)
# INFO - Processing email from user@example.com  
# DEBUG - 🟢 EXIT process_email -> {'processed': True, 'email_id': 'email_001'} [0.001s]
```

### 2. Configure Logging

```python
from utils.logging_system import LogConfig, configure_logging

# Production configuration
production_config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_to_stdout=False,  # Only file logging in production
    log_file="logs/emailagent_production.log",
    log_arguments=False,  # Don't log arguments in production
    log_return_values=False,
    max_file_size=100 * 1024 * 1024,  # 100MB
    backup_count=5
)

configure_logging(production_config)
```

## Logging Levels

### INFO Level
- Logs function entry only
- No arguments or return values
- Good for production monitoring

```python
from utils.logging_system import log_info

@log_info
def authenticate_user(username: str, password: str):
    # Only logs: "🔵 ENTER authenticate_user"
    return {"authenticated": True}
```

### DEBUG Level  
- Logs function entry with arguments
- Logs function exit with return values
- Logs execution time
- Great for development and debugging

```python
from utils.logging_system import log_debug

@log_debug
def classify_document(filename: str, content: str):
    # Logs entry with arguments, exit with return value, and timing
    return {"category": "financial_statement", "confidence": 0.89}
```

## Integration Examples

### Gmail Interface

```python
from utils.logging_system import log_function, get_logger

class GmailInterface:
    def __init__(self):
        self.logger = get_logger("gmail_interface")
    
    @log_function()
    async def connect(self, credentials_file: str, token_file: str = None):
        """Connect to Gmail API."""
        self.logger.info("Establishing Gmail connection")
        # Connection logic here
        return {"connected": True, "user_email": "user@gmail.com"}
    
    @log_debug
    async def list_emails(self, query: str = None, max_results: int = 10):
        """Retrieve emails with detailed logging."""
        self.logger.info(f"Fetching emails with query: {query}")
        # Email fetching logic
        return [{"id": "email_001", "subject": "Test Email"}]
```

### Document Classification

```python
from utils.logging_system import log_function, get_logger

class DocumentClassifier:
    def __init__(self):
        self.logger = get_logger("document_classifier")
    
    @log_function()
    def classify(self, filename: str, content: str, asset_type: str):
        """Classify document with logging."""
        self.logger.info(f"Classifying {filename} for {asset_type}")
        
        # Classification logic here
        result = {
            "category": "financial_statement",
            "confidence": 0.92,
            "asset_type": asset_type
        }
        
        self.logger.info(f"Classification: {result['category']} "
                        f"(confidence: {result['confidence']:.2f})")
        return result
```

### Security Pipeline

```python
from utils.logging_system import log_function, get_logger

class SecurityPipeline:
    def __init__(self):
        self.logger = get_logger("security_pipeline")
    
    @log_function()
    def virus_scan(self, file_path: str, config: dict):
        """Scan file for viruses."""
        self.logger.info(f"Scanning {file_path} for threats")
        
        # Virus scanning logic
        result = {"clean": True, "threats_found": 0}
        
        if result["clean"]:
            self.logger.info("File passed security scan")
        else:
            self.logger.warning(f"Threats detected: {result['threats_found']}")
        
        return result
```

### Memory System

```python
from utils.logging_system import log_function, get_logger

class MemorySystem:
    def __init__(self):
        self.logger = get_logger("memory_system")
    
    @log_function()
    async def store(self, data: dict, collection: str):
        """Store data in vector database."""
        self.logger.info(f"Storing data in {collection} collection")
        
        # Storage logic here
        result = {"stored": True, "vector_id": "vec_12345"}
        
        self.logger.info(f"Data stored successfully: {result['vector_id']}")
        return result
    
    @log_debug
    async def query(self, query_text: str, collection: str, limit: int = 5):
        """Query vector database with detailed logging."""
        self.logger.info(f"Querying {collection} collection")
        
        # Query logic here
        results = [{"id": "result_001", "score": 0.95}]
        
        self.logger.info(f"Found {len(results)} results")
        return results
```

## Configuration Options

### LogConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | str | "INFO" | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_to_file` | bool | True | Enable file logging |
| `log_to_stdout` | bool | True | Enable console logging |
| `log_file` | str | "logs/emailagent.log" | Log file path |
| `max_file_size` | int | 10MB | Maximum log file size before rotation |
| `backup_count` | int | 5 | Number of backup files to keep |
| `log_arguments` | bool | True | Log function arguments |
| `log_return_values` | bool | True | Log return values |
| `log_execution_time` | bool | True | Log execution time |
| `max_arg_length` | int | 500 | Maximum length for argument values |
| `sensitive_keys` | List[str] | [...] | Keys to redact (password, token, etc.) |

### Environment-Specific Configurations

```python
# Development
dev_config = LogConfig(
    level="DEBUG",
    log_arguments=True,
    log_return_values=True,
    log_execution_time=True
)

# Production  
prod_config = LogConfig(
    level="INFO",
    log_to_stdout=False,
    log_arguments=False,
    log_return_values=False,
    max_file_size=100 * 1024 * 1024  # 100MB
)

# Testing
test_config = LogConfig(
    level="DEBUG", 
    log_file="logs/test_emailagent.log"
)
```

## Security Features

### Sensitive Data Protection

The logging system automatically redacts sensitive information:

```python
@log_function()
def authenticate(username: str, password: str, api_key: str):
    # Logs: authenticate(username=testuser, password=<str REDACTED>, api_key=<str REDACTED>)
    return {"token": "secret_token"}
```

Default sensitive keys:
- password, token, secret, key, credential, auth
- access_token, refresh_token, client_secret, api_key

Add custom sensitive keys:

```python
config = LogConfig(
    sensitive_keys=['password', 'token', 'secret', 'private_key', 'certificate']
)
```

## Advanced Usage

### Manual Logging

```python
from utils.logging_system import get_logger

logger = get_logger("my_module")

# Standard logging methods
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Exception Handling

The logging system automatically captures and logs exceptions:

```python
@log_function()
def risky_operation(data: str):
    if data == "bad":
        raise ValueError("Invalid data")
    return {"processed": data}

# When exception occurs, logs:
# ERROR - 🔴 ERROR risky_operation raised ValueError: Invalid data [0.001s]
```

### Performance Monitoring

Track execution times for performance optimization:

```python
@log_function()  # Automatically logs execution time
def slow_operation():
    import time
    time.sleep(1)
    return "completed"

# Logs: EXIT slow_operation -> completed [1.001s]
```

## Testing

Run the comprehensive logging tests:

```bash
# Test basic logging functionality
python tests/test_logging_system.py

# Test integration with email agent components  
python tests/test_logging_integration.py
```

## Log File Management

Log files are automatically rotated when they reach the configured size:

- `logs/emailagent.log` - Current log file
- `logs/emailagent.log.1` - Previous log file
- `logs/emailagent.log.2` - Older log file
- etc.

## Best Practices

1. **Use appropriate log levels**: DEBUG for development, INFO for production
2. **Configure sensitive data protection**: Add domain-specific sensitive keys
3. **Monitor log file sizes**: Configure rotation to prevent disk space issues
4. **Use structured logging**: Include relevant context in log messages
5. **Test logging configuration**: Verify logging works in your environment

## Integration Checklist

- [ ] Configure logging in your main application
- [ ] Add decorators to key functions (authentication, email processing, classification)
- [ ] Set up log file rotation and management
- [ ] Configure sensitive data protection
- [ ] Test logging in development and production environments
- [ ] Monitor log files for insights and debugging

---

The logging system is now ready to provide comprehensive insights into your email agent's operations! 
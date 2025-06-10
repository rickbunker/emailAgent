"""
Configuration Management for Email Agent System

Centralized configuration management for the asset document management system.
Handles environment variables, API keys, database connections, logging settings, and
application-wide constants.

Features:
    - Environment-based configuration with fallback defaults
    - Secure credential management via environment variables
    - Database and API endpoint configuration
    - Logging configuration for different environments
    - Asset classification settings and document categories
    - Memory system configuration for Qdrant vector database

Environment Variables Required:
    - OPENAI_API_KEY: OpenAI API key for document classification
    - GMAIL_CLIENT_ID: Gmail API client ID  
    - GMAIL_CLIENT_SECRET: Gmail API client secret
    - GMAIL_REFRESH_TOKEN: Gmail API refresh token
    - MSGRAPH_CLIENT_ID: Microsoft Graph client ID
    - MSGRAPH_TENANT_ID: Microsoft Graph tenant ID
    - MSGRAPH_REDIRECT_URI: Microsoft Graph OAuth redirect URI
    - QDRANT_URL: Qdrant database URL (optional, defaults to localhost)
    - QDRANT_API_KEY: Qdrant API key (optional)
    - LANGGRAPH_ENV: Environment (development/staging/production)
"""

import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Logging system
from .utils.logging_system import get_logger, log_function

# Initialize logger
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Configuration for database connections."""
    
    # Qdrant Vector Database
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_size: int = 1536  # OpenAI embedding dimension
    qdrant_timeout: int = 30
    
    # Connection settings
    max_retries: int = 3
    connection_timeout: int = 10
    
    # Collections configuration
    collections: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "contacts": {"description": "Contact information and relationships", "vector_size": 1536, "distance": "Cosine"},
        "assets": {"description": "Asset information and properties", "vector_size": 1536, "distance": "Cosine"},
        "documents": {"description": "Document content and metadata", "vector_size": 1536, "distance": "Cosine"},
        "processing_history": {"description": "Email processing history and results", "vector_size": 1536, "distance": "Cosine"},
        "sender_patterns": {"description": "Sender behavior patterns and classifications", "vector_size": 1536, "distance": "Cosine"}
    })


@dataclass  
class APIConfig:
    """Configuration for external API connections."""
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-ada-002"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.1
    
    # Gmail API Configuration
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_scopes: List[str] = field(default_factory=lambda: [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send', 
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    # Microsoft Graph API Configuration
    msgraph_client_id: str = ""
    msgraph_tenant_id: str = ""
    msgraph_redirect_uri: str = "http://localhost:8080"
    msgraph_scopes: List[str] = field(default_factory=lambda: [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/User.Read'
    ])
    
    # API Rate Limiting
    max_requests_per_minute: int = 60
    request_timeout: int = 30


@dataclass
class SecurityConfig:
    """Configuration for security and virus scanning."""
    
    # ClamAV Configuration
    clamav_enabled: bool = True
    clamav_daemon_socket: str = "/var/run/clamav/clamd.ctl"
    clamav_command_timeout: int = 30
    clamav_max_filesize: int = 100 * 1024 * 1024  # 100MB
    
    # SpamAssassin Configuration  
    spamassassin_enabled: bool = True
    spamassassin_threshold: float = 5.0
    spamassassin_timeout: int = 15
    
    # File Processing Security
    allowed_file_extensions: List[str] = field(default_factory=lambda: [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.csv', '.json', '.xml', '.zip', '.rar'
    ])
    max_attachment_size: int = 50 * 1024 * 1024  # 50MB
    quarantine_directory: str = "quarantine/"


@dataclass
class MemoryConfig:
    """Configuration for memory system and data storage."""
    
    # Base paths
    base_memory_path: str = "memory/"
    procedural_memory_path: str = "memory/procedural/"
    semantic_memory_path: str = "memory/semantic/"
    episodic_memory_path: str = "memory/episodic/"
    
    # Cache configuration
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour
    
    # Memory retention
    max_memory_age_days: int = 365
    cleanup_interval_hours: int = 24


class EmailAgentConfig:
    """
    Main configuration class for the Email Agent system.
    
    Centralizes all configuration settings and provides methods for
    environment-specific configuration loading and validation.
    """
    
    def __init__(self, environment: str = "development"):
        """
        Initialize configuration with environment-specific settings.
        
        Args:
            environment: Environment name (development, staging, production)
        """
        self.environment = environment
        self.logger = get_logger(f"{__name__}.EmailAgentConfig")
        
        # Load configuration sections
        self.database = self._load_database_config()
        self.api = self._load_api_config()
        self.security = self._load_security_config()
        self.memory = self._load_memory_config()
        
        # Application settings
        self.app_name = "EmailAgent"
        self.app_version = "1.0.0"
        self.debug = environment == "development"
        
        # Initialize directories
        self._create_directories()
    
    @log_function()
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment variables."""
        return DatabaseConfig(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        )
    
    @log_function()
    def _load_api_config(self) -> APIConfig:
        """Load API configuration from environment variables."""
        return APIConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            gmail_client_id=os.getenv("GMAIL_CLIENT_ID", ""),
            gmail_client_secret=os.getenv("GMAIL_CLIENT_SECRET", ""),
            gmail_refresh_token=os.getenv("GMAIL_REFRESH_TOKEN", ""),
            msgraph_client_id=os.getenv("MSGRAPH_CLIENT_ID", ""),
            msgraph_tenant_id=os.getenv("MSGRAPH_TENANT_ID", ""),
        )
    
    @log_function()
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment variables."""
        return SecurityConfig()
    
    @log_function()
    def _load_memory_config(self) -> MemoryConfig:
        """Load memory system configuration."""
        return MemoryConfig()
    
    @log_function()
    def _create_directories(self) -> None:
        """Create necessary directories for the application."""
        directories = [
            "logs/", "temp/", "quarantine/", 
            self.memory.base_memory_path,
            self.memory.procedural_memory_path,
            self.memory.semantic_memory_path,
            self.memory.episodic_memory_path,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Global configuration instance
@log_function()
def get_config(environment: Optional[str] = None) -> EmailAgentConfig:
    """Get the global configuration instance."""
    if environment is None:
        environment = os.getenv("LANGGRAPH_ENV", "development")
    
    return EmailAgentConfig(environment)


# Default configuration instance
config = get_config()

# Email systems configuration
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

MSGRAPH_SCOPES = [
    'https://graph.microsoft.com/Mail.ReadWrite',
    'https://graph.microsoft.com/Mail.Send',
    'https://graph.microsoft.com/User.Read'
]

# Logging Configuration
LOGGING_CONFIG = {
    # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "level": "INFO",
    
    # Output destinations
    "log_to_file": True,
    "log_to_stdout": True,
    
    # File configuration
    "log_file": "logs/emailagent.log",
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "backup_count": 10,
    
    # Format configuration
    "format_string": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    
    # Function logging configuration
    "log_arguments": True,
    "log_return_values": True,
    "log_execution_time": True,
    "max_arg_length": 1000,  # Max chars for argument values
    
    # Sensitive data filtering
    "sensitive_keys": [
        'password', 'token', 'secret', 'key', 'credential', 'auth',
        'access_token', 'refresh_token', 'client_secret', 'api_key'
    ]
}

# Environment-specific logging overrides
DEVELOPMENT_LOGGING = {
    "level": "DEBUG",
    "log_arguments": True,
    "log_return_values": True,
    "log_execution_time": True
}

PRODUCTION_LOGGING = {
    "level": "INFO", 
    "log_arguments": False,
    "log_return_values": False,
    "log_execution_time": False,
    "log_to_stdout": False  # Only log to file in production
}

# Testing logging configuration
TESTING_LOGGING = {
    "level": "DEBUG",
    "log_to_file": True,
    "log_to_stdout": True,
    "log_file": "logs/test_emailagent.log"
} 
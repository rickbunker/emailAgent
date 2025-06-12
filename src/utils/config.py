"""
Configuration management for Email Agent.

Loads configuration from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional, List, Union
from dataclasses import dataclass


@dataclass
class EmailAgentConfig:
    """Configuration class for Email Agent application."""
    
    # Gmail Configuration
    gmail_credentials_path: str
    gmail_token_path: str
    
    # Microsoft Graph Configuration  
    msgraph_credentials_path: str
    
    # Database/Storage
    qdrant_host: str
    qdrant_port: int
    qdrant_api_key: Optional[str]
    
    # Application Settings
    flask_env: str
    flask_secret_key: str
    flask_host: str
    flask_port: int
    
    # Processing Configuration
    assets_base_path: str
    processed_attachments_path: str
    default_hours_back: int
    max_emails_per_batch: int
    enable_virus_scanning: bool
    enable_spam_filtering: bool
    
    # Human Review Thresholds
    low_confidence_threshold: float
    requires_review_threshold: float
    
    # Logging
    log_level: str
    log_file_path: str
    log_max_size_mb: int
    log_backup_count: int
    
    # Security
    max_attachment_size_mb: int
    allowed_file_extensions: List[str]
    clamav_socket_path: Optional[str]
    
    # Development
    debug: bool
    development_mode: bool

    @classmethod
    def from_env(cls) -> 'EmailAgentConfig':
        """Load configuration from environment variables."""
        
        # Helper function to parse boolean values
        def parse_bool(value: str, default: bool = False) -> bool:
            if not value:
                return default
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Helper function to parse list values
        def parse_list(value: str, separator: str = ',') -> List[str]:
            if not value:
                return []
            return [item.strip() for item in value.split(separator) if item.strip()]
        
        return cls(
            # Gmail Configuration
            gmail_credentials_path=os.getenv('GMAIL_CREDENTIALS_PATH', 'config/gmail_credentials.json'),
            gmail_token_path=os.getenv('GMAIL_TOKEN_PATH', 'config/gmail_token.json'),
            
            # Microsoft Graph Configuration
            msgraph_credentials_path=os.getenv('MSGRAPH_CREDENTIALS_PATH', 'config/msgraph_credentials.json'),
            
            # Database/Storage
            qdrant_host=os.getenv('QDRANT_HOST', 'localhost'),
            qdrant_port=int(os.getenv('QDRANT_PORT', '6333')),
            qdrant_api_key=os.getenv('QDRANT_API_KEY'),
            
            # Application Settings
            flask_env=os.getenv('FLASK_ENV', 'development'),
            flask_secret_key=os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production'),
            flask_host=os.getenv('FLASK_HOST', '127.0.0.1'),
            flask_port=int(os.getenv('FLASK_PORT', '5000')),
            
            # Processing Configuration
            assets_base_path=os.getenv('ASSETS_BASE_PATH', './assets'),
            processed_attachments_path=os.getenv('PROCESSED_ATTACHMENTS_PATH', './processed_attachments'),
            default_hours_back=int(os.getenv('DEFAULT_HOURS_BACK', '24')),
            max_emails_per_batch=int(os.getenv('MAX_EMAILS_PER_BATCH', '100')),
            enable_virus_scanning=parse_bool(os.getenv('ENABLE_VIRUS_SCANNING', 'true')),
            enable_spam_filtering=parse_bool(os.getenv('ENABLE_SPAM_FILTERING', 'true')),
            
            # Human Review Thresholds
            low_confidence_threshold=float(os.getenv('LOW_CONFIDENCE_THRESHOLD', '0.7')),
            requires_review_threshold=float(os.getenv('REQUIRES_REVIEW_THRESHOLD', '0.5')),
            
            # Logging
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file_path=os.getenv('LOG_FILE_PATH', 'logs/email_agent.log'),
            log_max_size_mb=int(os.getenv('LOG_MAX_SIZE_MB', '10')),
            log_backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            
            # Security
            max_attachment_size_mb=int(os.getenv('MAX_ATTACHMENT_SIZE_MB', '50')),
            allowed_file_extensions=parse_list(os.getenv('ALLOWED_FILE_EXTENSIONS', 'pdf,docx,xlsx,jpg,png,txt')),
            clamav_socket_path=os.getenv('CLAMAV_SOCKET_PATH'),
            
            # Development
            debug=parse_bool(os.getenv('DEBUG', 'false')),
            development_mode=parse_bool(os.getenv('DEVELOPMENT_MODE', 'false'))
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check required credential files exist
        for path, name in [
            (self.gmail_credentials_path, "Gmail credentials"),
            (self.msgraph_credentials_path, "Microsoft Graph credentials")
        ]:
            if not Path(path).exists():
                errors.append(f"{name} file not found: {path}")
        
        # Validate thresholds
        if not (0.0 <= self.low_confidence_threshold <= 1.0):
            errors.append("Low confidence threshold must be between 0.0 and 1.0")
        
        if not (0.0 <= self.requires_review_threshold <= 1.0):
            errors.append("Requires review threshold must be between 0.0 and 1.0")
        
        # Validate directories exist or can be created
        for path, name in [
            (self.assets_base_path, "Assets base directory"),
            (self.processed_attachments_path, "Processed attachments directory"),
            (Path(self.log_file_path).parent, "Log directory")
        ]:
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {name}: {path} - {e}")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.flask_env.lower() == 'production'
    
    def get_credential_path(self, service: str) -> str:
        """Get credential path for a specific service."""
        if service.lower() == 'gmail':
            return self.gmail_credentials_path
        elif service.lower() in ['msgraph', 'microsoft', 'graph']:
            return self.msgraph_credentials_path
        else:
            raise ValueError(f"Unknown service: {service}")


def load_config() -> EmailAgentConfig:
    """Load and validate configuration from environment."""
    config = EmailAgentConfig.from_env()
    
    errors = config.validate()
    if errors:
        print("⚠️  Configuration validation errors:")
        for error in errors:
            print(f"   - {error}")
        
        if config.is_production():
            raise RuntimeError("Configuration validation failed in production mode")
        else:
            print("   Continuing in development mode...")
    
    return config


# Global configuration instance
config = load_config() 
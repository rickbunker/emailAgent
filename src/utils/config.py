"""
Configuration management for Email Agent.

Loads configuration from environment variables with sensible defaults.
Includes memory monitoring and system resource validation for production readiness.
"""

# # Standard library imports
import os
import psutil
from dataclasses import dataclass
from pathlib import Path

from .logging_system import get_logger

# Initialize logger
logger = get_logger(__name__)

# Project root directory (parent of src/)
# Get the actual project root by finding the directory containing 'src'
_config_file = Path(__file__).resolve()  # This file is in src/utils/config.py
_src_dir = _config_file.parent.parent  # Go up to src/
PROJECT_ROOT = _src_dir.parent  # Go up to project root

# Verify we found the right directory (should contain app.py and requirements.txt)
if (
    not (PROJECT_ROOT / "app.py").exists()
    or not (PROJECT_ROOT / "requirements.txt").exists()
):
    # Fallback: search upward for the project root
    current = _config_file.parent
    while current.parent != current:  # Stop at filesystem root
        if (current / "app.py").exists() and (current / "requirements.txt").exists():
            PROJECT_ROOT = current
            break
        current = current.parent


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
    qdrant_api_key: str | None
    qdrant_url: str

    # Memory System Configuration (Phase 1.3 Addition)
    semantic_memory_max_items: int
    procedural_memory_max_items: int
    episodic_memory_max_items: int
    contact_memory_max_items: int
    embedding_model: str

    # Memory weights for combined decision logic (Phase 2.1)
    procedural_memory_weight: float
    semantic_memory_weight: float
    episodic_memory_weight: float
    contact_memory_weight: float

    # Search limits for memory systems
    semantic_search_limit: int
    episodic_search_limit: int
    contact_search_limit: int

    # Similarity thresholds for memory matching
    semantic_similarity_threshold: float
    episodic_similarity_threshold: float
    minimum_combined_confidence: float

    # Phase 3: Enhanced Context Integration
    # Asset type context filtering (Phase 3.1)
    asset_type_boost_factor: float
    asset_type_penalty_factor: float
    context_confidence_threshold: float
    category_constraint_strength: float
    asset_context_weight: float

    # Multi-source context clues (Phase 3.2)
    sender_context_weight: float
    subject_context_weight: float
    body_context_weight: float
    filename_context_weight: float
    unified_context_threshold: float
    context_agreement_bonus: float
    context_conflict_penalty: float

    # Phase 4.3: Additional episodic memory pattern analysis settings
    criteria_match_threshold: float
    similarity_threshold: float
    max_similar_cases: int
    pattern_analysis_limit: int

    # Phase 4.4: Contact memory trust evaluation settings
    default_sender_trust_score: float
    max_organization_contacts: int

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

    # Parallel Processing Configuration
    max_concurrent_emails: int
    max_concurrent_attachments: int
    email_batch_size: int
    processing_timeout_seconds: int

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
    allowed_file_extensions: list[str]
    clamav_socket_path: str | None

    # Development
    debug: bool
    development_mode: bool

    # Web UI Configuration
    web_ui_log_file: str
    processed_emails_file: str
    human_review_queue_file: str
    review_attachments_path: str

    # Email Search Configuration
    inbox_labels: list[str]
    max_search_results: int

    # Mailbox Configuration
    gmail_mailbox_id: str
    gmail_mailbox_name: str
    msgraph_mailbox_id: str
    msgraph_mailbox_name: str

    # Phase 6.2: Memory Monitoring Configuration
    memory_monitoring_enabled: bool
    memory_cleanup_threshold: float  # Percentage (0.0-1.0) when cleanup kicks in
    memory_warning_threshold: float  # Percentage (0.0-1.0) when warnings are logged
    memory_performance_logging: bool
    memory_usage_check_interval: int  # Seconds between memory usage checks
    memory_cleanup_batch_size: int  # Number of items to remove per cleanup batch
    memory_stats_log_interval: int  # Seconds between memory statistics logging

    # Phase 6.2: System Resource Validation
    min_available_memory_gb: float  # Minimum system RAM required
    min_available_disk_gb: float  # Minimum disk space required
    max_memory_usage_ratio: float  # Maximum ratio of memory limits to system RAM
    system_resource_check_enabled: bool

    @classmethod
    def from_env(cls) -> "EmailAgentConfig":
        """Load configuration from environment variables."""

        # Helper function to parse boolean values
        def parse_bool(value: str, default: bool = False) -> bool:
            if not value:
                return default
            return value.lower() in ("true", "1", "yes", "on")

        # Helper function to parse list values
        def parse_list(value: str, separator: str = ",") -> list[str]:
            if not value:
                return []
            return [item.strip() for item in value.split(separator) if item.strip()]

        # Construct qdrant_url from host and port
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        qdrant_url = f"http://{qdrant_host}:{qdrant_port}"

        return cls(
            # Gmail Configuration
            gmail_credentials_path=os.getenv(
                "GMAIL_CREDENTIALS_PATH",
                str(PROJECT_ROOT / "config/gmail_credentials.json"),
            ),
            gmail_token_path=os.getenv(
                "GMAIL_TOKEN_PATH", str(PROJECT_ROOT / "config/gmail_token.json")
            ),
            # Microsoft Graph Configuration
            msgraph_credentials_path=os.getenv(
                "MSGRAPH_CREDENTIALS_PATH",
                str(PROJECT_ROOT / "config/msgraph_credentials.json"),
            ),
            # Database/Storage
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            qdrant_url=qdrant_url,
            # Memory System Configuration (recommended production limits)
            semantic_memory_max_items=int(
                os.getenv("SEMANTIC_MEMORY_MAX_ITEMS", "50000")
            ),
            procedural_memory_max_items=int(
                os.getenv("PROCEDURAL_MEMORY_MAX_ITEMS", "10000")
            ),
            episodic_memory_max_items=int(
                os.getenv("EPISODIC_MEMORY_MAX_ITEMS", "100000")
            ),
            contact_memory_max_items=int(
                os.getenv("CONTACT_MEMORY_MAX_ITEMS", "25000")
            ),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            # Memory weights for combined decision logic (Phase 2.1)
            procedural_memory_weight=float(
                os.getenv("PROCEDURAL_MEMORY_WEIGHT", "0.25")
            ),
            semantic_memory_weight=float(os.getenv("SEMANTIC_MEMORY_WEIGHT", "0.3")),
            episodic_memory_weight=float(os.getenv("EPISODIC_MEMORY_WEIGHT", "0.2")),
            contact_memory_weight=float(os.getenv("CONTACT_MEMORY_WEIGHT", "0.25")),
            # Search limits for memory systems
            semantic_search_limit=int(os.getenv("SEMANTIC_SEARCH_LIMIT", "10")),
            episodic_search_limit=int(os.getenv("EPISODIC_SEARCH_LIMIT", "5")),
            contact_search_limit=int(os.getenv("CONTACT_SEARCH_LIMIT", "10")),
            # Similarity thresholds for memory matching
            semantic_similarity_threshold=float(
                os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.3")
            ),
            episodic_similarity_threshold=float(
                os.getenv("EPISODIC_SIMILARITY_THRESHOLD", "0.25")
            ),
            minimum_combined_confidence=float(
                os.getenv("MINIMUM_COMBINED_CONFIDENCE", "0.2")
            ),
            # Phase 3: Enhanced Context Integration
            # Asset type context filtering (Phase 3.1)
            asset_type_boost_factor=float(os.getenv("ASSET_TYPE_BOOST_FACTOR", "1.5")),
            asset_type_penalty_factor=float(
                os.getenv("ASSET_TYPE_PENALTY_FACTOR", "0.6")
            ),
            context_confidence_threshold=float(
                os.getenv("CONTEXT_CONFIDENCE_THRESHOLD", "0.3")
            ),
            category_constraint_strength=float(
                os.getenv("CATEGORY_CONSTRAINT_STRENGTH", "0.8")
            ),
            asset_context_weight=float(os.getenv("ASSET_CONTEXT_WEIGHT", "0.3")),
            # Multi-source context clues (Phase 3.2)
            sender_context_weight=float(os.getenv("SENDER_CONTEXT_WEIGHT", "0.25")),
            subject_context_weight=float(os.getenv("SUBJECT_CONTEXT_WEIGHT", "0.35")),
            body_context_weight=float(os.getenv("BODY_CONTEXT_WEIGHT", "0.25")),
            filename_context_weight=float(os.getenv("FILENAME_CONTEXT_WEIGHT", "0.15")),
            unified_context_threshold=float(
                os.getenv("UNIFIED_CONTEXT_THRESHOLD", "0.4")
            ),
            context_agreement_bonus=float(os.getenv("CONTEXT_AGREEMENT_BONUS", "0.2")),
            context_conflict_penalty=float(
                os.getenv("CONTEXT_CONFLICT_PENALTY", "0.3")
            ),
            # Phase 4.3: Additional episodic memory pattern analysis settings
            criteria_match_threshold=float(
                os.getenv("CRITERIA_MATCH_THRESHOLD", "0.4")
            ),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.2")),
            max_similar_cases=int(os.getenv("MAX_SIMILAR_CASES", "10")),
            pattern_analysis_limit=int(os.getenv("PATTERN_ANALYSIS_LIMIT", "100")),
            # Phase 4.4: Contact memory trust evaluation settings
            default_sender_trust_score=float(
                os.getenv("DEFAULT_SENDER_TRUST_SCORE", "0.3")
            ),
            max_organization_contacts=int(os.getenv("MAX_ORGANIZATION_CONTACTS", "50")),
            # Application Settings
            flask_env=os.getenv("FLASK_ENV", "development"),
            flask_secret_key=os.getenv(
                "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
            ),
            flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
            flask_port=int(os.getenv("FLASK_PORT", "5001")),
            # Processing Configuration
            assets_base_path=os.getenv(
                "ASSETS_BASE_PATH", str(PROJECT_ROOT / "assets")
            ),
            processed_attachments_path=os.getenv(
                "PROCESSED_ATTACHMENTS_PATH",
                str(PROJECT_ROOT / "processed_attachments"),
            ),
            default_hours_back=int(os.getenv("DEFAULT_HOURS_BACK", "24")),
            max_emails_per_batch=int(os.getenv("MAX_EMAILS_PER_BATCH", "100")),
            enable_virus_scanning=parse_bool(
                os.getenv("ENABLE_VIRUS_SCANNING", "true")
            ),
            enable_spam_filtering=parse_bool(
                os.getenv("ENABLE_SPAM_FILTERING", "true")
            ),
            # Parallel Processing Configuration
            max_concurrent_emails=int(os.getenv("MAX_CONCURRENT_EMAILS", "5")),
            max_concurrent_attachments=int(
                os.getenv("MAX_CONCURRENT_ATTACHMENTS", "10")
            ),
            email_batch_size=int(os.getenv("EMAIL_BATCH_SIZE", "20")),
            processing_timeout_seconds=int(
                os.getenv("PROCESSING_TIMEOUT_SECONDS", "300")
            ),
            # Human Review Thresholds
            low_confidence_threshold=float(
                os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.7")
            ),
            requires_review_threshold=float(
                os.getenv("REQUIRES_REVIEW_THRESHOLD", "0.5")
            ),
            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file_path=os.getenv(
                "LOG_FILE_PATH", str(PROJECT_ROOT / "logs/email_agent.log")
            ),
            log_max_size_mb=int(os.getenv("LOG_MAX_SIZE_MB", "10")),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            # Security
            max_attachment_size_mb=int(os.getenv("MAX_ATTACHMENT_SIZE_MB", "50")),
            allowed_file_extensions=parse_list(
                os.getenv("ALLOWED_FILE_EXTENSIONS", "pdf,docx,xlsx,jpg,png,txt")
            ),
            clamav_socket_path=os.getenv("CLAMAV_SOCKET_PATH"),
            # Development
            debug=parse_bool(os.getenv("DEBUG", "false")),
            development_mode=parse_bool(os.getenv("DEVELOPMENT_MODE", "false")),
            # Web UI Configuration
            web_ui_log_file=os.getenv(
                "WEB_UI_LOG_FILE", str(PROJECT_ROOT / "logs/web_ui.log")
            ),
            processed_emails_file=os.getenv(
                "PROCESSED_EMAILS_FILE",
                str(PROJECT_ROOT / "data/processed_emails.json"),
            ),
            human_review_queue_file=os.getenv(
                "HUMAN_REVIEW_QUEUE_FILE",
                str(PROJECT_ROOT / "data/human_review_queue.json"),
            ),
            review_attachments_path=os.getenv(
                "REVIEW_ATTACHMENTS_PATH", str(PROJECT_ROOT / "data/review_attachments")
            ),
            # Email Search Configuration
            inbox_labels=parse_list(os.getenv("INBOX_LABELS", "INBOX,Inbox")),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "100")),
            # Mailbox Configuration
            gmail_mailbox_id=os.getenv("GMAIL_MAILBOX_ID", "gmail_primary"),
            gmail_mailbox_name=os.getenv(
                "GMAIL_MAILBOX_NAME", "Gmail (Primary Account)"
            ),
            msgraph_mailbox_id=os.getenv("MSGRAPH_MAILBOX_ID", "msgraph_primary"),
            msgraph_mailbox_name=os.getenv(
                "MSGRAPH_MAILBOX_NAME", "Microsoft 365 (Primary Account)"
            ),
            # Phase 6.2: Memory Monitoring Configuration
            memory_monitoring_enabled=parse_bool(
                os.getenv("MEMORY_MONITORING_ENABLED", "true")
            ),
            memory_cleanup_threshold=float(
                os.getenv(
                    "MEMORY_CLEANUP_THRESHOLD", "0.85"
                )  # 85% full triggers cleanup
            ),
            memory_warning_threshold=float(
                os.getenv(
                    "MEMORY_WARNING_THRESHOLD", "0.75"
                )  # 75% full triggers warnings
            ),
            memory_performance_logging=parse_bool(
                os.getenv("MEMORY_PERFORMANCE_LOGGING", "true")
            ),
            memory_usage_check_interval=int(
                os.getenv("MEMORY_USAGE_CHECK_INTERVAL", "300")  # Check every 5 minutes
            ),
            memory_cleanup_batch_size=int(
                os.getenv(
                    "MEMORY_CLEANUP_BATCH_SIZE", "1000"
                )  # Remove 1000 items per batch
            ),
            memory_stats_log_interval=int(
                os.getenv("MEMORY_STATS_LOG_INTERVAL", "3600")  # Log stats every hour
            ),
            # Phase 6.2: System Resource Validation
            min_available_memory_gb=float(
                os.getenv("MIN_AVAILABLE_MEMORY_GB", "2.0")  # Require 2GB RAM minimum
            ),
            min_available_disk_gb=float(
                os.getenv("MIN_AVAILABLE_DISK_GB", "5.0")  # Require 5GB disk minimum
            ),
            max_memory_usage_ratio=float(
                os.getenv(
                    "MAX_MEMORY_USAGE_RATIO", "0.5"
                )  # Memory limits <= 50% of system RAM
            ),
            system_resource_check_enabled=parse_bool(
                os.getenv("SYSTEM_RESOURCE_CHECK_ENABLED", "true")
            ),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Check required credential files exist
        for path, name in [
            (self.gmail_credentials_path, "Gmail credentials"),
            (self.msgraph_credentials_path, "Microsoft Graph credentials"),
        ]:
            if not Path(path).exists():
                errors.append(f"{name} file not found: {path}")

        # Validate thresholds
        if not (0.0 <= self.low_confidence_threshold <= 1.0):
            errors.append("Low confidence threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.requires_review_threshold <= 1.0):
            errors.append("Requires review threshold must be between 0.0 and 1.0")

        # Phase 6.2: Validate memory monitoring thresholds
        if not (0.0 <= self.memory_cleanup_threshold <= 1.0):
            errors.append("Memory cleanup threshold must be between 0.0 and 1.0")

        if not (0.0 <= self.memory_warning_threshold <= 1.0):
            errors.append("Memory warning threshold must be between 0.0 and 1.0")

        if self.memory_warning_threshold >= self.memory_cleanup_threshold:
            errors.append(
                "Memory warning threshold must be less than cleanup threshold"
            )

        if not (0.0 <= self.max_memory_usage_ratio <= 1.0):
            errors.append("Max memory usage ratio must be between 0.0 and 1.0")

        # Validate intervals
        if self.memory_usage_check_interval < 60:
            errors.append("Memory usage check interval must be at least 60 seconds")

        if self.memory_stats_log_interval < 300:
            errors.append("Memory stats log interval must be at least 300 seconds")

        if self.memory_cleanup_batch_size < 100:
            errors.append("Memory cleanup batch size must be at least 100")

        # Validate parallel processing settings
        if self.max_concurrent_emails < 1:
            errors.append("max_concurrent_emails must be at least 1")

        if self.max_concurrent_attachments < 1:
            errors.append("max_concurrent_attachments must be at least 1")

        if self.email_batch_size < 1:
            errors.append("email_batch_size must be at least 1")

        if self.processing_timeout_seconds < 30:
            errors.append("processing_timeout_seconds must be at least 30")

        # Validate directories exist or can be created
        for path, name in [
            (self.assets_base_path, "Assets base directory"),
            (self.processed_attachments_path, "Processed attachments directory"),
            (Path(self.log_file_path).parent, "Log directory"),
        ]:
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create {name}: {path} - {e}")

        # Phase 6.2: System resource validation
        if self.system_resource_check_enabled:
            try:
                resource_errors = self.validate_system_resources()
                errors.extend(resource_errors)
            except Exception as e:
                errors.append(f"System resource check failed: {e}")

        return errors

    def validate_system_resources(self) -> list[str]:
        """
        Validate system resources meet minimum requirements.

        Returns:
            List of validation error messages
        """
        errors = []

        try:
            # Check available memory
            memory_info = psutil.virtual_memory()
            available_memory_gb = memory_info.available / (1024**3)
            total_memory_gb = memory_info.total / (1024**3)

            if available_memory_gb < self.min_available_memory_gb:
                errors.append(
                    f"Insufficient available memory: {available_memory_gb:.1f}GB "
                    f"(required: {self.min_available_memory_gb}GB)"
                )

            # Calculate total memory requirements from limits
            total_memory_items = (
                self.semantic_memory_max_items
                + self.procedural_memory_max_items
                + self.episodic_memory_max_items
                + self.contact_memory_max_items
            )

            # Estimate memory usage (rough calculation: ~2KB per item on average)
            estimated_memory_usage_gb = (total_memory_items * 2048) / (1024**3)
            memory_usage_ratio = estimated_memory_usage_gb / total_memory_gb

            if memory_usage_ratio > self.max_memory_usage_ratio:
                errors.append(
                    f"Memory limits too high: {memory_usage_ratio:.1%} of system RAM "
                    f"(max allowed: {self.max_memory_usage_ratio:.1%})"
                )

            # Check available disk space
            disk_usage = psutil.disk_usage(self.assets_base_path)
            available_disk_gb = disk_usage.free / (1024**3)

            if available_disk_gb < self.min_available_disk_gb:
                errors.append(
                    f"Insufficient disk space: {available_disk_gb:.1f}GB "
                    f"(required: {self.min_available_disk_gb}GB)"
                )

        except Exception as e:
            errors.append(f"Failed to check system resources: {e}")

        return errors

    def get_memory_limits_summary(self) -> dict[str, int]:
        """
        Get summary of configured memory limits.

        Returns:
            Dictionary with memory type limits
        """
        return {
            "semantic": self.semantic_memory_max_items,
            "procedural": self.procedural_memory_max_items,
            "episodic": self.episodic_memory_max_items,
            "contact": self.contact_memory_max_items,
            "total": (
                self.semantic_memory_max_items
                + self.procedural_memory_max_items
                + self.episodic_memory_max_items
                + self.contact_memory_max_items
            ),
        }

    def get_system_resource_info(self) -> dict[str, any]:
        """
        Get current system resource information.

        Returns:
            Dictionary with system resource stats
        """
        try:
            memory_info = psutil.virtual_memory()
            disk_usage = psutil.disk_usage(self.assets_base_path)

            return {
                "memory": {
                    "total_gb": memory_info.total / (1024**3),
                    "available_gb": memory_info.available / (1024**3),
                    "used_percent": memory_info.percent,
                },
                "disk": {
                    "total_gb": disk_usage.total / (1024**3),
                    "available_gb": disk_usage.free / (1024**3),
                    "used_percent": (disk_usage.used / disk_usage.total) * 100,
                },
                "cpu": {
                    "count": psutil.cpu_count(),
                    "usage_percent": psutil.cpu_percent(interval=1),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.flask_env.lower() == "production"

    def get_credential_path(self, service: str) -> str:
        """Get credential path for a specific service."""
        if service.lower() == "gmail":
            return self.gmail_credentials_path
        elif service.lower() in ["msgraph", "microsoft", "graph"]:
            return self.msgraph_credentials_path
        else:
            raise ValueError(f"Unknown service: {service}")


def load_config() -> EmailAgentConfig:
    """Load and validate configuration from environment."""
    config = EmailAgentConfig.from_env()

    errors = config.validate()
    if errors:
        logger.warning("⚠️  Configuration validation errors:")
        for error in errors:
            logger.warning("   - %s", error)

        if config.is_production():
            raise RuntimeError("Configuration validation failed in production mode")
        else:
            logger.warning("   Continuing in development mode...")

    # Log system resource information if monitoring is enabled
    if config.system_resource_check_enabled:
        try:
            resource_info = config.get_system_resource_info()
            memory_limits = config.get_memory_limits_summary()

            logger.info("📊 System Resource Summary:")
            logger.info(
                f"   Memory: {resource_info['memory']['available_gb']:.1f}GB available / {resource_info['memory']['total_gb']:.1f}GB total"
            )
            logger.info(
                f"   Disk: {resource_info['disk']['available_gb']:.1f}GB available / {resource_info['disk']['total_gb']:.1f}GB total"
            )
            logger.info(
                f"   CPU: {resource_info['cpu']['count']} cores, {resource_info['cpu']['usage_percent']:.1f}% usage"
            )
            logger.info("🧠 Memory Limits Configured:")
            for memory_type, limit in memory_limits.items():
                if memory_type != "total":
                    logger.info(f"   {memory_type.capitalize()}: {limit:,} items")
            logger.info(f"   Total: {memory_limits['total']:,} items")

        except Exception as e:
            logger.warning(f"Failed to log system resources: {e}")

    return config


# Global configuration instance
config = load_config()

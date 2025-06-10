"""
Utility Systems Package for EmailAgent

Complete utility package for private market asset management environments.
Provides essential utility functions, logging systems, configuration management,
and shared infrastructure for the EmailAgent system.

Features:
    - logging system with structured output
    - Configuration management and validation
    - Shared utility functions and helpers
    - Performance monitoring and optimization
    - Error handling and debugging support
    - development tools

Business Context:
    Designed for asset management firms requiring business
    utility infrastructure with logging, configuration
    management, and shared services for email automation and
    document processing systems.

Technical Architecture:
    - LoggingSystem: Complete logging with structured output
    - Configuration: Centralized configuration management
    - Utilities: Shared helper functions and tools
    - Performance: Monitoring and optimization utilities
    - Error Handling: error management

Components:
    - logging_system: logging infrastructure
    - config_utils: Configuration management utilities
    - performance_utils: Performance monitoring tools
    - error_handling: Error management and reporting
    - debugging_utils: Development and debugging support

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

from .logging_system import get_logger, log_function, LogConfig

# Package metadata
__version__ = "1.0.0"
__author__ = "Email Agent Development Team"
__license__ = "Private - Asset Management Use Only"

# Initialize package logger
logger = get_logger(__name__)

# Public API exports
__all__ = [
    # Core logging system
    'get_logger',
    'log_function',
    'LogConfig',
    
    # Package metadata
    '__version__',
    '__author__',
    '__license__'
]

# Package initialization logging
logger.info(f"Utils package initialized - Version {__version__}")
logger.debug("Core logging system loaded with configuration")
logger.debug("Utility infrastructure ready for EmailAgent operations")

# Package-level convenience functions
@log_function()
def get_package_info() -> dict:
    """
    Get complete package information and metadata.
    
    Provides detailed information about the utils package
    capabilities, version, and available utilities.
    
    Returns:
        Dictionary containing package information and metadata
        
    Example:
        >>> from utils import get_package_info
        >>> info = get_package_info()
        >>> print(info['version'])
        '1.0.0'
    """
    logger.info("Retrieving utils package information")
    
    return {
        'name': 'EmailAgent Utils Package',
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'description': 'Complete utility package for private market asset management environments',
        'capabilities': [
            'logging system',
            'Configuration management',
            'Performance monitoring',
            'Error handling and debugging',
            'Shared utility functions'
        ],
        'components': [
            'logging_system',
            'config_utils',
            'performance_utils',
            'error_handling',
            'debugging_utils'
        ],
        'business_context': 'Asset management email automation and document processing'
    }

@log_function()
def configure_logging(
    level: str = 'INFO',
    format_type: str = 'structured',
    output_file: str = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> LogConfig:
    """
    Configure logging system with business context.
    
    Provides convenient package-level logging configuration
    with business settings for asset management environments.
    
    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        format_type: Log format type ('structured', 'simple', 'json')
        output_file: Optional log file path for persistent logging
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to maintain
        
    Returns:
        Configured LogConfig instance
        
    Example:
        >>> from utils import configure_logging
        >>> log_config = configure_logging(
        ...     level='DEBUG',
        ...     format_type='structured',
        ...     output_file='emailagent.log'
        ... )
    """
    logger.info(f"Configuring logging system: level={level}, format={format_type}")
    
    return LogConfig(
        level=level,
        format_type=format_type,
        output_file=output_file,
        max_file_size=max_file_size,
        backup_count=backup_count,
        include_business_context=True,
        enable_performance_tracking=True
    )

@log_function()
def get_system_status() -> dict:
    """
    Get complete system status and health information.
    
    Provides system health, performance metrics, and operational
    status for monitoring and troubleshooting asset management
    email automation systems.
    
    Returns:
        Dictionary containing system status and health metrics
        
    Example:
        >>> from utils import get_system_status
        >>> status = get_system_status()
        >>> print(f"System healthy: {status['healthy']}")
    """
    logger.info("Retrieving system status and health information")
    
    import platform
    import psutil
    import os
    from datetime import datetime, UTC
    
    try:
        # System information
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor() or 'Unknown',
            'hostname': platform.node()
        }
        
        # Resource utilization
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resource_info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': memory.percent,
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': disk.percent,
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2)
        }
        
        # Process information
        current_process = psutil.Process(os.getpid())
        process_info = {
            'pid': current_process.pid,
            'memory_mb': round(current_process.memory_info().rss / (1024**2), 2),
            'cpu_percent': current_process.cpu_percent(),
            'num_threads': current_process.num_threads(),
            'create_time': datetime.fromtimestamp(current_process.create_time(), UTC).isoformat()
        }
        
        # Health assessment
        healthy = (
            resource_info['cpu_percent'] < 80 and
            resource_info['memory_percent'] < 85 and
            resource_info['disk_percent'] < 90
        )
        
        status = {
            'healthy': healthy,
            'timestamp': datetime.now(UTC).isoformat(),
            'uptime_seconds': round(psutil.boot_time()),
            'system': system_info,
            'resources': resource_info,
            'process': process_info,
            'warnings': []
        }
        
        # Add warnings for resource constraints
        if resource_info['cpu_percent'] > 70:
            status['warnings'].append(f"High CPU usage: {resource_info['cpu_percent']}%")
        
        if resource_info['memory_percent'] > 80:
            status['warnings'].append(f"High memory usage: {resource_info['memory_percent']}%")
        
        if resource_info['disk_percent'] > 85:
            status['warnings'].append(f"High disk usage: {resource_info['disk_percent']}%")
        
        logger.info(f"System status retrieved - Healthy: {healthy}, CPU: {resource_info['cpu_percent']}%, Memory: {resource_info['memory_percent']}%")
        return status
        
    except Exception as e:
        logger.error(f"Error retrieving system status: {e}")
        return {
            'healthy': False,
            'timestamp': datetime.now(UTC).isoformat(),
            'error': str(e),
            'warnings': ['Unable to retrieve complete system status']
        }

# Utility constants for asset management environments
ASSET_MANAGEMENT_CONSTANTS = {
    'DEFAULT_MEMORY_LIMITS': {
        'contact_memory': 5000,
        'episodic_memory': 3000,
        'semantic_memory': 2000,
        'procedural_memory': 1000
    },
    'PERFORMANCE_THRESHOLDS': {
        'max_cpu_percent': 80,
        'max_memory_percent': 85,
        'max_disk_percent': 90,
        'max_response_time_ms': 5000
    },
    'BUSINESS_CATEGORIES': [
        'private_equity',
        'real_estate',
        'private_credit',
        'infrastructure',
        'hedge_fund',
        'family_office',
        'institutional_investor',
        'service_provider'
    ],
    'EMAIL_CLASSIFICATIONS': [
        'investment_inquiry',
        'due_diligence',
        'fund_performance',
        'investor_update',
        'compliance_notification',
        'operational_update',
        'market_intelligence',
        'relationship_management'
    ]
}

# Export utility constants
__all__.extend([
    'get_package_info',
    'configure_logging',
    'get_system_status',
    'ASSET_MANAGEMENT_CONSTANTS'
])

logger.debug("Utils package initialization completed successfully")
logger.debug(f"Exported utilities: {len(__all__)} components available") 
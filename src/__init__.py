"""
Email Agent - Asset Document Management System

A LangGraph-based email management system specialized for asset document 
management in private market investments including commercial real estate, private equity, 
private credit, and infrastructure investments.

Core Features:
    - Gmail and Microsoft Graph API integration
    - AI-powered document classification (25+ categories)
    - ClamAV virus scanning and SpamAssassin spam detection  
    - Qdrant vector database memory system
    - Complete logging and monitoring
    - Async/await architecture for optimal performance

Main Components:
    - agents: Core AI agents for document processing and classification
    - email_interface: Unified interface for Gmail and Microsoft Graph APIs
    - memory: Qdrant-based vector database system for storage
    - tools: Security and utility tools (virus scanning, spam detection)
    - utils: Utility modules including complete logging system

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License: Private - Inveniam Capital Partners, LLC use only
Copyright: 2025 Inveniam Capital Partners, LLC and Rick Bunker
"""

from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Logging system
from .utils.logging_system import get_logger, configure_logging, LogConfig, log_function

# Initialize package-level logger
logger = get_logger(__name__)

# Package version and metadata
__version__ = "1.0.0"
__author__ = "Email Agent Development Team"
__description__ = "Asset Document Management System"

# Main components
__all__ = [
    # Core modules
    "agents",
    "email_interface", 
    "memory",
    "tools",
    "utils",
    
    # Configuration
    "config",
    
    # Logging utilities
    "get_logger",
    "configure_logging", 
    "LogConfig",
    "log_function",
    
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
]

@log_function()
def initialize_package(log_level: str = "INFO", log_to_file: bool = True) -> Dict[str, Any]:
    """
    Initialize the Email Agent package with logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to enable file logging
        
    Returns:
        Dict containing initialization status and configuration
        
    Raises:
        ImportError: If required dependencies are missing
        ConfigurationError: If configuration is invalid
    """
    logger.info("Initializing Email Agent package")
    
    try:
        # Configure package-level logging
        config = LogConfig(
            level=log_level,
            log_to_file=log_to_file,
            log_to_stdout=True,
            log_file="logs/emailagent.log"
        )
        configure_logging(config)
        
        initialization_result = {
            "status": "initialized",
            "version": __version__,
            "log_level": log_level,
            "log_to_file": log_to_file,
            "components_available": __all__[:5],  # Core components only
            "python_version": sys.version,
            "package_path": str(Path(__file__).parent)
        }
        
        logger.info(f"Email Agent v{__version__} initialized successfully")
        return initialization_result
        
    except Exception as e:
        logger.error(f"Failed to initialize Email Agent package: {e}")
        raise

@log_function()
def get_package_info() -> Dict[str, Any]:
    """
    Get complete package information.
    
    Returns:
        Dict containing package version, components, and system info
    """
    logger.debug("Retrieving package information")
    
    package_info = {
        "name": "emailAgent",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "components": {
            "agents": "AI agents for document processing",
            "email_interface": "Gmail and Microsoft Graph integration", 
            "memory": "Qdrant vector database system",
            "tools": "Security and utility tools",
            "utils": "Logging and utility modules"
        },
        "features": [
            "Gmail API integration",
            "Microsoft Graph API integration", 
            "AI document classification",
            "Virus scanning (ClamAV)",
            "Spam detection (SpamAssassin)",
            "Vector database memory",
            "Complete logging"
        ],
        "python_version": sys.version,
        "package_path": str(Path(__file__).parent)
    }
    
    return package_info


# Package initialization
if __name__ != "__main__":
    # Automatically initialize with default settings when imported
    try:
        initialize_package()
    except Exception as e:
        print(f"Warning: Email Agent package initialization failed: {e}") 
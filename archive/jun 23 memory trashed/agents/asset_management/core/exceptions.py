"""
Custom exceptions for the asset management system.

This module defines all custom exceptions used throughout the asset
management system for better error handling and debugging.
"""

# # Standard library imports
from typing import Any, Optional


class AssetManagementError(Exception):
    """Base exception for all asset management errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize the exception with message and optional details.

        Args:
            message: Error message
            details: Additional error context
        """
        super().__init__(message)
        self.details = details or {}


class AssetNotFoundError(AssetManagementError):
    """Raised when an asset cannot be found."""

    def __init__(self, asset_id: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize asset not found error.

        Args:
            asset_id: The asset ID that was not found
            details: Additional error context
        """
        message = f"Asset not found: {asset_id}"
        super().__init__(message, details)
        self.asset_id = asset_id


class ProcessingError(AssetManagementError):
    """Raised when document processing fails."""

    pass


class IdentificationError(AssetManagementError):
    """Raised when asset identification fails."""

    pass


class ClassificationError(AssetManagementError):
    """Raised when document classification fails."""

    pass


class MemorySystemError(AssetManagementError):
    """Raised when memory system operations fail."""

    pass


class ConfigurationError(AssetManagementError):
    """Raised when configuration is invalid or missing."""

    pass


class SecurityError(AssetManagementError):
    """Raised when security checks fail (AV scan, file validation)."""

    pass

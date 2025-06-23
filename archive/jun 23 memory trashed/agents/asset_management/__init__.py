"""
Asset Management System - Clean Architecture Implementation.

This package provides a modular, maintainable asset management system that:
- Identifies assets using sender mappings and pattern matching
- Classifies documents with proper categorization
- Learns from experience through episodic memory
- Avoids false positives through proper confidence thresholds

Key components:
- AssetIdentifier: Main asset identification service
- DocumentClassifier: Document categorization service
- EpisodicLearner: Learning from past experiences
- Data models: Asset, ProcessingResult, etc.
"""

# Version info
__version__ = "2.0.0"
__author__ = "Email Agent Team"

# # Local application imports
from src.asset_management.classification.document_classifier import DocumentClassifier

# Core data models
from src.asset_management.core.data_models import (
    Asset,
    AssetMatch,
    AssetType,
    CategoryMatch,
    ClassificationContext,
    ConfidenceLevel,
    DocumentCategory,
    IdentificationContext,
    ProcessingResult,
    ProcessingStatus,
    SenderMapping,
)

# Core exceptions
from src.asset_management.core.exceptions import (
    AssetManagementError,
    AssetNotFoundError,
    ClassificationError,
    ConfigurationError,
    IdentificationError,
    MemorySystemError,
    ProcessingError,
    SecurityError,
)

# Main services
from src.asset_management.identification.asset_identifier import AssetIdentifier
from src.asset_management.memory_integration.episodic_learner import (
    Decision,
    EpisodicLearner,
    Outcome,
)

# Memory integration
from src.asset_management.memory_integration.sender_mappings import SenderMappingService

# Import AssetService
from src.asset_management.services.asset_service import AssetService

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Data models
    "Asset",
    "AssetType",
    "DocumentCategory",
    "ProcessingStatus",
    "ProcessingResult",
    "ConfidenceLevel",
    "AssetMatch",
    "CategoryMatch",
    "IdentificationContext",
    "ClassificationContext",
    "SenderMapping",
    # Exceptions
    "AssetManagementError",
    "AssetNotFoundError",
    "ProcessingError",
    "IdentificationError",
    "ClassificationError",
    "MemorySystemError",
    "ConfigurationError",
    "SecurityError",
    # Services
    "AssetIdentifier",
    "DocumentClassifier",
    "SenderMappingService",
    "EpisodicLearner",
    "Decision",
    "Outcome",
    "AssetService",
]

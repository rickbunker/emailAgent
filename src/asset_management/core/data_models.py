"""
Core data models for the asset management system.

This module contains all the essential data structures, enums, and models
used throughout the asset management system. These definitions maintain
compatibility with the existing system while providing a clean foundation
for the new architecture.
"""

# # Standard library imports
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


class AssetType(Enum):
    """Private market asset types supported by the system."""

    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    PRIVATE_CREDIT = "private_credit"
    PRIVATE_EQUITY = "private_equity"
    INFRASTRUCTURE = "infrastructure"


class DocumentCategory(Enum):
    """Document classification categories across all asset types."""

    # Commercial Real Estate
    RENT_ROLL = "rent_roll"
    FINANCIAL_STATEMENTS = "financial_statements"
    PROPERTY_PHOTOS = "property_photos"
    APPRAISAL = "appraisal"
    LEASE_DOCUMENTS = "lease_documents"
    PROPERTY_MANAGEMENT = "property_management"

    # Private Credit
    LOAN_DOCUMENTS = "loan_documents"
    BORROWER_FINANCIALS = "borrower_financials"
    COVENANT_COMPLIANCE = "covenant_compliance"
    CREDIT_MEMO = "credit_memo"
    LOAN_MONITORING = "loan_monitoring"

    # Private Equity
    PORTFOLIO_REPORTS = "portfolio_reports"
    INVESTOR_UPDATES = "investor_updates"
    BOARD_MATERIALS = "board_materials"
    DEAL_DOCUMENTS = "deal_documents"
    VALUATION_REPORTS = "valuation_reports"

    # Infrastructure
    ENGINEERING_REPORTS = "engineering_reports"
    CONSTRUCTION_UPDATES = "construction_updates"
    REGULATORY_DOCUMENTS = "regulatory_documents"
    OPERATIONS_REPORTS = "operations_reports"

    # General
    LEGAL_DOCUMENTS = "legal_documents"
    TAX_DOCUMENTS = "tax_documents"
    INSURANCE = "insurance"
    CORRESPONDENCE = "correspondence"
    UNKNOWN = "unknown"


class ProcessingStatus(Enum):
    """
    Document processing status enumeration.

    Represents the various states a document can be in during the
    multi-phase processing pipeline from initial validation through
    final storage and classification.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    QUARANTINED = "quarantined"
    DUPLICATE = "duplicate"
    INVALID_TYPE = "invalid_type"
    AV_SCAN_FAILED = "av_scan_failed"
    ERROR = "error"


class ConfidenceLevel(Enum):
    """Confidence levels for document routing decisions."""

    HIGH = "high"  # >= high_confidence_threshold
    MEDIUM = "medium"  # >= medium_confidence_threshold
    LOW = "low"  # >= low_confidence_threshold
    VERY_LOW = "very_low"  # < low_confidence_threshold


@dataclass
class Asset:
    """
    Asset definition for private market investments.

    Represents a single investment asset with all associated
    metadata and organizational information.
    """

    deal_id: str
    deal_name: str
    asset_name: str
    asset_type: AssetType
    folder_path: str
    identifiers: list[str]
    created_date: datetime
    last_updated: datetime
    metadata: Optional[dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """
    Result of document processing operations.

    Contains all metadata and outcomes from the multi-phase
    document processing pipeline including classification results.
    """

    status: ProcessingStatus
    file_hash: Optional[str] = None
    file_path: Optional[Path] = None
    confidence: float = 0.0
    error_message: Optional[str] = None
    quarantine_reason: Optional[str] = None
    duplicate_of: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    # Phase 3: Document Classification
    document_category: Optional[DocumentCategory] = None
    confidence_level: Optional[ConfidenceLevel] = None
    matched_asset_id: Optional[str] = None
    asset_confidence: float = 0.0
    classification_metadata: Optional[dict[str, Any]] = None

    @classmethod
    def success_result(
        cls,
        file_hash: str,
        confidence: float = 1.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ProcessingResult":
        """Create a successful processing result."""
        return cls(
            status=ProcessingStatus.SUCCESS,
            file_hash=file_hash,
            confidence=confidence,
            metadata=metadata or {},
        )

    @classmethod
    def error_result(cls, error_message: str) -> "ProcessingResult":
        """Create an error processing result."""
        return cls(status=ProcessingStatus.ERROR, error_message=error_message)


@dataclass
class IdentificationContext:
    """
    Context information for asset identification.

    Contains all available information that can be used to identify
    which asset a document belongs to.
    """

    filename: str
    sender_email: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    file_content_preview: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    def get_combined_text(self) -> str:
        """Get all text combined for analysis."""
        parts = [self.filename]
        if self.email_subject:
            parts.append(self.email_subject)
        if self.email_body:
            parts.append(self.email_body)
        if self.file_content_preview:
            parts.append(self.file_content_preview)
        return " ".join(parts).lower()


@dataclass
class AssetMatch:
    """
    Result of asset identification attempt.

    Contains the matched asset (if any) and confidence information
    about the match quality.
    """

    asset_id: str
    asset_name: str
    confidence: float
    match_source: str  # 'sender_mapping', 'pattern_match', 'episodic_learning'
    match_details: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Determine confidence level from raw score using config thresholds."""
        # Get thresholds from config
        high_threshold = getattr(config, "high_confidence_threshold", 0.85)
        medium_threshold = getattr(config, "medium_confidence_threshold", 0.65)
        low_threshold = getattr(config, "low_confidence_threshold", 0.40)

        if self.confidence >= high_threshold:
            return ConfidenceLevel.HIGH
        elif self.confidence >= medium_threshold:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= low_threshold:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class ClassificationContext:
    """
    Context information for document classification.

    Contains all available information that can be used to classify
    a document into the appropriate category.
    """

    filename: str
    asset_type: AssetType
    asset_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    file_content_preview: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass
class CategoryMatch:
    """
    Result of document classification attempt.

    Contains the matched category and confidence information
    about the classification quality.
    """

    category: DocumentCategory
    confidence: float
    match_source: str  # 'filename_pattern', 'content_analysis', 'episodic_learning'
    match_details: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Determine confidence level from raw score using config thresholds."""
        # Get thresholds from config
        high_threshold = getattr(config, "high_confidence_threshold", 0.85)
        medium_threshold = getattr(config, "medium_confidence_threshold", 0.65)
        low_threshold = getattr(config, "low_confidence_threshold", 0.40)

        if self.confidence >= high_threshold:
            return ConfidenceLevel.HIGH
        elif self.confidence >= medium_threshold:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= low_threshold:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


@dataclass
class SenderMapping:
    """
    Mapping between email sender and asset.

    Represents an existing sender-to-asset mapping from the
    asset_management_sender_mappings collection.
    """

    mapping_id: str
    sender_email: str
    asset_id: str
    confidence: float
    created_date: datetime
    last_activity: Optional[datetime] = None
    email_count: int = 0
    metadata: Optional[dict[str, Any]] = None

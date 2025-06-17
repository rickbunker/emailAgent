"""
Asset Document Agent - Memory-Driven Architecture

A learning document processing agent that replaces hardcoded patterns with
memory-driven classification. Maintains backward compatibility while providing
true agentic behavior through procedural memory and human feedback learning.

Key Features:
    - Learns classification patterns from successful processing
    - Adapts from human feedback without code changes
    - Uses semantic similarity instead of regex patterns
    - Modular architecture with specialized services
    - Backward compatible with existing web UI

Replaces: 2,788 lines of hardcoded patterns with learning code

Author: Rick Bunker, rbunker@inveniam.io
License: For Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
# Standard library imports
import asyncio
import hashlib
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# # Third-party imports
# Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# Local imports
from ..memory.procedural import ProceduralMemory
from ..utils.config import config
from ..utils.logging_system import get_logger, log_function

# Initialize module logger
logger = get_logger(__name__)


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


class ConfidenceLevel(Enum):
    """Confidence levels for document routing decisions."""

    HIGH = "high"  # >= 85% - Auto-process
    MEDIUM = "medium"  # >= 65% - Process with confirmation
    LOW = "low"  # >= 40% - Save uncategorized
    VERY_LOW = "very_low"  # < 40% - Human review required


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


class SecurityService:
    """
    Handles file validation and security scanning operations.

    Provides virus scanning, file type validation, and hash calculation
    services for attachment processing.
    """

    def __init__(self) -> None:
        """Initialize security service with ClamAV detection."""
        self.logger = get_logger(f"{__name__}.SecurityService")
        self.clamscan_path = self._find_clamscan()

    def _find_clamscan(self) -> Optional[str]:
        """
        Find ClamAV clamscan executable.

        Returns:
            Path to clamscan executable if found, None otherwise
        """
        try:
            result = subprocess.run(
                ["which", "clamscan"],
                capture_output=True,
                text=True,
                timeout=5,  # 5 second timeout for finding clamscan
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                self.logger.info("Found clamscan at: %s", path)
                return path
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            self.logger.debug("Failed to find clamscan: %s", e)

        self.logger.warning("ClamAV not available - antivirus scanning disabled")
        return None

    async def scan_file_antivirus(
        self, file_content: bytes, filename: str
    ) -> tuple[bool, Optional[str]]:
        """
        Scan file content with ClamAV antivirus.

        Args:
            file_content: Raw file bytes to scan
            filename: Original filename for logging

        Returns:
            Tuple of (is_clean, threat_name)

        Raises:
            SecurityError: If scanning process fails critically
        """
        if not self.clamscan_path:
            self.logger.warning("ClamAV not available - skipping scan for %s", filename)
            return True, None

        temp_path = None
        try:
            # Create temporary file for scanning
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name

            # Run clamscan asynchronously
            process = await asyncio.create_subprocess_exec(
                self.clamscan_path,
                "--stdout",
                "--no-summary",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30,  # 30 second timeout for antivirus scan
            )

            stdout_text = stdout.decode("utf-8") if stdout else ""

            # Check for virus detection
            if "Infected files: 1" in stdout_text or process.returncode == 1:
                threat_name = self._extract_threat_name(stdout_text, temp_path)
                self.logger.warning("Virus detected in %s: %s", filename, threat_name)
                return False, threat_name

            if process.returncode == 0:
                return True, None

            # Handle other errors
            stderr_text = stderr.decode("utf-8") if stderr else ""
            self.logger.warning("ClamAV scan error for %s: %s", filename, stderr_text)
            return False, f"Scan error: {stderr_text}"

        except asyncio.TimeoutError:
            self.logger.warning("ClamAV scan timeout for %s", filename)
            return False, "Scan timeout"
        except Exception as e:
            self.logger.error("Antivirus scan failed for %s: %s", filename, e)
            return False, f"Scan error: {str(e)}"
        finally:
            # Clean up temporary file
            if temp_path:
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass

    def _extract_threat_name(self, stdout: str, temp_path: str) -> str:
        """Extract threat name from ClamAV output."""
        for line in stdout.splitlines():
            if temp_path in line and ": " in line:
                threat_name = line.split(": ")[1].strip()
                if threat_name.upper() != "OK":
                    return threat_name
        return "Unknown virus detected"

    def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content.

        Args:
            file_content: Raw file bytes

        Returns:
            Hexadecimal SHA256 hash string

        Raises:
            ValueError: If file_content is empty or None
        """
        if not file_content:
            raise ValueError("File content cannot be empty or None")

        file_hash = hashlib.sha256(file_content).hexdigest()
        logger.debug("Calculated SHA256 hash: %s...", file_hash[:16])
        return file_hash

    def validate_file_type(self, filename: str) -> bool:
        """
        Validate file type against allowed extensions.

        Args:
            filename: Name of the file to validate

        Returns:
            True if file type is allowed, False otherwise
        """
        if not filename:
            return False

        file_extension = Path(filename).suffix.lower()
        allowed_extensions = {
            ".pdf",
            ".xlsx",
            ".xls",
            ".doc",
            ".docx",
            ".pptx",
            ".jpg",
            ".png",
            ".dwg",
        }

        is_valid = file_extension in allowed_extensions
        logger.debug("File type validation for %s: %s", filename, is_valid)
        return is_valid

    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size against configured limits.

        Args:
            file_size: Size in bytes

        Returns:
            True if size is within limits, False otherwise
        """
        max_size = config.max_attachment_size_mb * 1024 * 1024
        is_valid = file_size <= max_size

        if not is_valid:
            logger.warning(
                "File size %d bytes exceeds limit of %d MB",
                file_size,
                config.max_attachment_size_mb,
            )

        return is_valid


class AssetDocumentAgent:
    """
    Memory-Driven Asset Document Agent.

    Replaces the original 2,788-line hardcoded agent with a learning system
    that adapts from successful classifications and human feedback.

    Key Features:
        - Learns from successful processing patterns
        - Adapts from human corrections without code changes
        - Uses semantic similarity instead of hardcoded regex
        - Maintains backward compatibility with existing interfaces

    Example:
        >>> agent = AssetDocumentAgent(qdrant_client)
        >>> await agent.initialize_collections()
        >>> result = await agent.process_attachment(attachment_data, email_data)
    """

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        base_assets_path: str = "./assets",
        clamav_socket: Optional[str] = None,
    ) -> None:
        """
        Initialize the learning agent.

        Args:
            qdrant_client: Connected Qdrant client instance for vector storage
            base_assets_path: Base directory for storing asset documents
            clamav_socket: ClamAV socket path (reserved for future use)

        Raises:
            OSError: If base assets path cannot be created
        """
        self.logger = get_logger(f"{__name__}.AssetDocumentAgent")
        self.logger.info("Initializing Memory-Driven Asset Document Agent")

        # Core components
        self.qdrant = qdrant_client
        self.base_assets_path = Path(base_assets_path)

        # Create base directory
        try:
            self.base_assets_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(
                "Asset storage path initialized: %s", self.base_assets_path
            )
        except OSError as e:
            self.logger.error("Failed to create assets directory: %s", e)
            raise

        # Initialize services
        self.security = SecurityService()
        self.procedural_memory = (
            ProceduralMemory(qdrant_client) if qdrant_client else None
        )

        # Processing statistics
        self.stats: dict[str, int] = {
            "processed": 0,
            "quarantined": 0,
            "duplicates": 0,
            "errors": 0,
            "learned": 0,
            "corrected": 0,
        }

        # Backward compatibility - collection names
        self.COLLECTIONS = {
            "assets": "asset_management_assets",
            "asset_sender_mappings": "asset_management_sender_mappings",
            "processed_documents": "asset_management_processed_documents",
            "unknown_senders": "asset_management_unknown_senders",
        }

        self.logger.info("Memory-driven agent initialized successfully")

    async def initialize_collections(self) -> bool:
        """
        Initialize Qdrant collections for asset management.

        Returns:
            True if initialization successful, False otherwise
        """
        if not self.qdrant:
            self.logger.warning("Qdrant client not provided - skipping initialization")
            return False

        try:
            # Initialize procedural memory collections
            if self.procedural_memory:
                await self.procedural_memory.initialize_collections()
                self.logger.info("Procedural memory collections initialized")

            # Initialize other collections as needed
            for collection_name in self.COLLECTIONS.values():
                if not await self._collection_exists(collection_name):
                    await self._create_collection(
                        collection_name, 384  # Standard sentence transformer dimension
                    )
                    self.logger.info("Created collection: %s", collection_name)

            self.logger.info("All collections initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize collections: %s", e)
            return False

    async def _collection_exists(self, collection_name: str) -> bool:
        """Check if a Qdrant collection exists."""
        try:
            collections = self.qdrant.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception:
            return False

    async def _create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a Qdrant collection with specified vector size."""
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    @log_function()
    async def process_single_attachment(
        self, attachment_data: dict[str, Any], email_data: dict[str, Any]
    ) -> ProcessingResult:
        """
        Process a single email attachment through validation pipeline.

        Args:
            attachment_data: Dictionary with 'filename' and 'content' keys
            email_data: Dictionary with email metadata

        Returns:
            ProcessingResult with status and metadata
        """
        filename = attachment_data.get("filename", "unknown_attachment")
        content = attachment_data.get("content", b"")

        self.logger.info("Processing attachment: %s", filename)

        try:
            # Step 1: Basic validation
            if not content:
                return ProcessingResult.error_result("No file content available")

            # Step 2: Security scanning
            is_clean, threat_name = await self.security.scan_file_antivirus(
                content, filename
            )
            if not is_clean:
                self.stats["quarantined"] += 1
                file_hash = self.security.calculate_file_hash(content)
                return ProcessingResult(
                    status=ProcessingStatus.QUARANTINED,
                    file_hash=file_hash,
                    quarantine_reason=threat_name,
                )

            # Step 3: File validation
            if not self.security.validate_file_type(filename):
                return ProcessingResult(
                    status=ProcessingStatus.INVALID_TYPE,
                    error_message=f"File type {Path(filename).suffix} not allowed",
                )

            if not self.security.validate_file_size(len(content)):
                return ProcessingResult(
                    status=ProcessingStatus.INVALID_TYPE,
                    error_message="File size exceeds configured limit",
                )

            # Step 4: Calculate hash and check duplicates
            file_hash = self.security.calculate_file_hash(content)
            duplicate_id = await self.check_duplicate(file_hash)
            if duplicate_id:
                self.stats["duplicates"] += 1
                return ProcessingResult(
                    status=ProcessingStatus.DUPLICATE,
                    file_hash=file_hash,
                    duplicate_of=duplicate_id,
                )

            # Success - prepare metadata
            self.stats["processed"] += 1

            metadata = {
                "filename": filename,
                "file_size": len(content),
                "sender_email": email_data.get("sender_email"),
                "email_subject": email_data.get("subject"),
                "processing_date": datetime.now(UTC).isoformat(),
                "file_extension": Path(filename).suffix.lower(),
            }

            return ProcessingResult.success_result(file_hash, 1.0, metadata)

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.error("Processing error for %s: %s", filename, e)
            return ProcessingResult.error_result(str(e))

    @log_function()
    async def enhanced_process_attachment(
        self, attachment_data: dict[str, Any], email_data: dict[str, Any]
    ) -> ProcessingResult:
        """
        Enhanced processing with memory-driven classification and asset matching.

        Args:
            attachment_data: Dictionary with 'filename' and 'content' keys
            email_data: Dictionary with email metadata

        Returns:
            ProcessingResult with classification and confidence data
        """
        # Start with basic processing
        result = await self.process_single_attachment(attachment_data, email_data)

        if result.status != ProcessingStatus.SUCCESS:
            return result

        # Add memory-driven classification and asset matching
        if self.procedural_memory:
            filename = attachment_data.get("filename", "")
            email_subject = email_data.get("subject", "")
            email_body = email_data.get("body", "")

            try:
                # Step 1: Memory-driven document classification
                (
                    category_str,
                    classification_confidence,
                ) = await self.procedural_memory.classify_document(
                    filename, email_subject, email_body
                )

                # Step 2: Memory-driven asset identification
                known_assets = await self.list_assets()
                asset_matches = await self.identify_asset_from_content(
                    email_subject, email_body, filename, known_assets
                )

                # Determine best asset match
                matched_asset_id = None
                asset_confidence = 0.0
                if asset_matches:
                    matched_asset_id, asset_confidence = asset_matches[0]

                # Step 3: Learn from high-confidence results
                if classification_confidence > 0.75:  # Auto-learning threshold
                    await self.procedural_memory.learn_classification_pattern(
                        filename,
                        email_subject,
                        email_body,
                        category_str,
                        "unknown",  # Asset type determined separately
                        classification_confidence,
                        "auto_learning",
                    )
                    self.stats["learned"] += 1

                # Convert to enum for backward compatibility
                try:
                    document_category = DocumentCategory(category_str)
                except ValueError:
                    document_category = DocumentCategory.UNKNOWN

                # Determine overall confidence level
                overall_confidence = (classification_confidence + asset_confidence) / 2
                if overall_confidence >= 0.85:
                    confidence_level = ConfidenceLevel.HIGH
                elif overall_confidence >= 0.65:
                    confidence_level = ConfidenceLevel.MEDIUM
                elif overall_confidence >= config.low_confidence_threshold:
                    confidence_level = ConfidenceLevel.LOW
                else:
                    confidence_level = ConfidenceLevel.VERY_LOW

                # Update result with memory-driven classification
                result.document_category = document_category
                result.confidence_level = confidence_level
                result.matched_asset_id = matched_asset_id
                result.asset_confidence = asset_confidence
                result.classification_metadata = {
                    "classification_confidence": classification_confidence,
                    "asset_confidence": asset_confidence,
                    "overall_confidence": overall_confidence,
                    "learning_source": "procedural_memory",
                    "patterns_used": "memory_driven",
                }

                self.logger.info(
                    f"Memory-driven results: {category_str} ({classification_confidence:.3f}), "
                    f"Asset: {matched_asset_id[:8] if matched_asset_id else 'none'} ({asset_confidence:.3f})"
                )

            except Exception as e:
                self.logger.warning(
                    "Memory-driven processing failed, using fallback: %s", e
                )
                result.document_category = DocumentCategory.UNKNOWN
                result.confidence_level = ConfidenceLevel.VERY_LOW

        return result

    async def learn_from_human_feedback(
        self,
        filename: str,
        email_subject: str,
        email_body: str,
        system_prediction: str,
        human_correction: str,
        asset_type: str = "unknown",
    ) -> str:
        """
        Learn from human corrections to improve future classifications.

        Args:
            filename: Original filename
            email_subject: Email subject line
            email_body: Email body content
            system_prediction: What the system predicted
            human_correction: What the human corrected it to
            asset_type: Asset type context

        Returns:
            Pattern ID of the learned correction
        """
        if not self.procedural_memory:
            self.logger.warning("No procedural memory available for learning")
            return "no_memory_available"

        self.logger.info(
            "Learning from human feedback: %s -> %s",
            system_prediction,
            human_correction,
        )

        pattern_id = await self.procedural_memory.learn_from_human_feedback(
            filename,
            email_subject,
            email_body,
            system_prediction,
            human_correction,
            asset_type,
        )

        self.stats["corrected"] += 1
        return pattern_id

    async def get_sender_assets(self, sender_email: str) -> list[dict[str, Any]]:
        """Get all assets associated with a sender."""
        self.logger.info("Checking sender asset mappings for: %s", sender_email)

        assets = []

        if not self.qdrant:
            self.logger.warning(
                "Qdrant client not available - cannot check sender mappings"
            )
            return assets

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="sender_email",
                            match=MatchValue(value=sender_email.lower()),
                        )
                    ]
                ),
                limit=100,
            )

            if search_result[0]:
                self.logger.info("Found %d sender mapping(s)", len(search_result[0]))

                for point in search_result[0]:
                    mapping_data = {
                        "asset_id": point.payload.get("asset_id"),
                        "confidence": point.payload.get("confidence", 0.0),
                        "created_date": point.payload.get("created_date"),
                        "mapping_id": point.id,
                    }
                    assets.append(mapping_data)
                    self.logger.debug(
                        "Mapping: %s (confidence: %.3f)",
                        mapping_data["asset_id"],
                        mapping_data["confidence"],
                    )
            else:
                self.logger.info("No sender mappings found for: %s", sender_email)

        except Exception as e:
            self.logger.error("Error checking sender mappings: %s", e)

        return assets

    async def identify_asset_from_content(
        self,
        email_subject: str,
        email_body: str = "",
        filename: str = "",
        known_assets: Optional[list[Asset]] = None,
    ) -> list[tuple[str, float]]:
        """
        Enhanced memory-driven asset identification with sophisticated matching logic.

        This method now replicates the proven fuzzy matching approach from the old system
        while using memory-driven patterns for adaptability.

        Args:
            email_subject: Email subject line
            email_body: Email body content
            filename: Attachment filename
            known_assets: List of known assets to match against

        Returns:
            List of (asset_id, confidence_score) tuples, sorted by confidence
        """
        self.logger.info("🧠 Enhanced memory-driven asset identification")
        self.logger.info(f"📧 Subject: '{email_subject}'")
        self.logger.info(f"📄 Filename: '{filename}'")

        if not known_assets:
            self.logger.info("❌ No assets available for matching")
            return []

        if not self.procedural_memory:
            self.logger.warning("❌ No procedural memory - cannot use learned patterns")
            return []

        try:
            # Combine all text for analysis (like old system)
            combined_text = f"{email_subject} {email_body} {filename}".lower()
            self.logger.info(f"🔤 Combined text: '{combined_text[:100]}...'")

            # Get asset matching patterns from procedural memory
            scroll_result = self.procedural_memory.qdrant.scroll(
                collection_name=self.procedural_memory.collections["asset_patterns"],
                limit=1000,
                with_payload=True,
                with_vectors=False,
            )

            if not scroll_result[0]:
                self.logger.info("❌ No asset matching patterns in procedural memory")
                return []

            asset_scores: dict[str, float] = {}
            patterns_available = len(scroll_result[0])

            self.logger.info(
                f"📊 Checking {len(known_assets)} assets against {patterns_available} patterns"
            )

            # Evaluate each known asset with enhanced logic
            for asset in known_assets:
                max_asset_confidence = 0.0

                self.logger.debug(
                    f"\n🏢 Evaluating: {asset.deal_name} ({asset.deal_id[:8]})"
                )

                # Check each stored pattern to see if it applies to this asset
                for point in scroll_result[0]:
                    try:
                        pattern_data = point.payload.get("pattern_data", {})
                        pattern_asset_id = pattern_data.get("asset_id", "")

                        # Check if this pattern is specifically for this asset
                        if pattern_asset_id and pattern_asset_id == asset.deal_id:
                            # This is a specific asset pattern
                            pattern_confidence = await self._evaluate_asset_pattern(
                                pattern_data, combined_text, asset
                            )
                            max_asset_confidence = max(
                                max_asset_confidence, pattern_confidence
                            )

                            self.logger.debug(
                                f"   📋 Specific pattern match: {pattern_confidence:.3f}"
                            )

                        # Also check generic asset-type patterns
                        elif not pattern_asset_id:
                            pattern_asset_type = pattern_data.get("asset_type", "")
                            if (
                                pattern_asset_type
                                and hasattr(asset, "asset_type")
                                and pattern_asset_type == asset.asset_type.value
                            ):
                                pattern_confidence = await self._evaluate_asset_pattern(
                                    pattern_data, combined_text, asset
                                )
                                # Reduce confidence for generic patterns
                                pattern_confidence *= 0.8
                                max_asset_confidence = max(
                                    max_asset_confidence, pattern_confidence
                                )

                                self.logger.debug(
                                    f"   🎯 Generic pattern match: {pattern_confidence:.3f}"
                                )

                    except Exception as e:
                        self.logger.debug(f"Error evaluating asset pattern: {e}")

                # Apply minimum confidence threshold (like old system)
                min_confidence = 0.5
                if max_asset_confidence >= min_confidence:
                    asset_scores[asset.deal_id] = max_asset_confidence
                    self.logger.info(
                        f"   ⭐ QUALIFIED: {asset.deal_name} -> {max_asset_confidence:.3f}"
                    )
                else:
                    self.logger.debug(
                        f"   ❌ Below threshold: {asset.deal_name} -> {max_asset_confidence:.3f}"
                    )

            # Convert to sorted list (highest confidence first)
            asset_matches = [
                (asset_id, confidence) for asset_id, confidence in asset_scores.items()
            ]
            asset_matches.sort(key=lambda x: x[1], reverse=True)

            # Enhanced result logging (like old system)
            self.logger.info("🏁 Enhanced asset identification complete")
            if asset_matches:
                self.logger.info(
                    f"📈 Found {len(asset_matches)} qualifying asset matches:"
                )
                for i, (asset_id, confidence) in enumerate(
                    asset_matches[:3]
                ):  # Show top 3
                    asset_name = next(
                        (a.deal_name for a in known_assets if a.deal_id == asset_id),
                        "Unknown",
                    )
                    self.logger.info(f"   {i+1}. {asset_name} -> {confidence:.3f}")
            else:
                self.logger.info("❌ No qualifying asset matches found")

            return asset_matches

        except Exception as e:
            self.logger.error(f"Enhanced asset identification failed: {e}")
            return []

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using SequenceMatcher.
        This replicates the old system's fuzzy matching capability.
        """
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    async def _evaluate_asset_pattern(
        self,
        pattern_data: dict[str, Any],
        combined_text: str,
        asset: Asset,
    ) -> float:
        """
        Enhanced asset pattern evaluation that replicates the old system's
        sophisticated matching logic while using memory-driven patterns.
        """
        max_confidence = 0.0

        self.logger.debug(f"🔍 Enhanced evaluation for asset: {asset.deal_name}")

        # Step 1: Collect all asset identifiers to check (like the old system)
        all_identifiers = [
            asset.deal_name,
            asset.asset_name,
        ] + asset.identifiers

        # Add pattern-specific identifiers if available
        pattern_identifiers = pattern_data.get("identifiers", [])
        if pattern_identifiers:
            all_identifiers.extend(pattern_identifiers)

        # Remove duplicates and None values
        all_identifiers = list(set(filter(None, all_identifiers)))

        self.logger.debug(f"🏷️ Checking identifiers: {all_identifiers}")

        # Step 2: Check each identifier with multiple matching strategies
        for identifier in all_identifiers:
            if not identifier:
                continue

            identifier_lower = identifier.lower()
            identifier_confidence = 0.0

            # Strategy 1: Exact match (highest confidence)
            if identifier_lower in combined_text:
                identifier_confidence = 0.95
                self.logger.debug(
                    f"   ✅ EXACT: '{identifier_lower}' -> {identifier_confidence}"
                )

            # Strategy 2: Fuzzy matching if exact match not found
            elif len(identifier_lower) >= 3:
                words = combined_text.split()

                # Check different phrase lengths (3, 2, 1 words) like old system
                for word_group_size in [3, 2, 1]:
                    for i in range(len(words) - word_group_size + 1):
                        phrase = " ".join(words[i : i + word_group_size])

                        if len(phrase) < 3:  # Skip very short phrases
                            continue

                        # Calculate similarity using SequenceMatcher (replaces Levenshtein)
                        similarity = self._calculate_similarity(
                            identifier_lower, phrase
                        )

                        # Fuzzy match threshold (same as old system)
                        if similarity >= 0.8:
                            confidence = similarity * 0.9  # Slightly lower than exact
                            identifier_confidence = max(
                                identifier_confidence, confidence
                            )

                            self.logger.debug(
                                f"   🎯 FUZZY: '{identifier_lower}' ~= '{phrase}' "
                                f"(sim: {similarity:.3f}) -> {confidence:.3f}"
                            )

            max_confidence = max(max_confidence, identifier_confidence)

        # Step 3: Apply asset-type keyword boosts (replicated from old system)
        asset_keywords = pattern_data.get("keywords", [])
        if asset_keywords:
            keyword_matches = sum(
                1 for keyword in asset_keywords if keyword.lower() in combined_text
            )

            if keyword_matches > 0:
                keyword_boost = min(keyword_matches * 0.1, 0.3)  # Max 30% boost
                old_confidence = max_confidence
                max_confidence = min(max_confidence + keyword_boost, 1.0)

                self.logger.debug(
                    f"   🚀 KEYWORD BOOST: {keyword_matches} matches -> "
                    f"+{keyword_boost:.3f} ({old_confidence:.3f} -> {max_confidence:.3f})"
                )

        # Step 4: Pattern source reliability boost
        pattern_source = pattern_data.get("source", "")
        if pattern_source == "enhanced_fix":
            reliability_boost = 0.1
            max_confidence = min(max_confidence + reliability_boost, 1.0)
            self.logger.debug(f"   ⭐ ENHANCED PATTERN BOOST: +{reliability_boost:.3f}")

        # Step 5: Asset type matching boost
        pattern_asset_type = pattern_data.get("asset_type", "")
        if pattern_asset_type and hasattr(asset, "asset_type"):
            if pattern_asset_type == asset.asset_type.value:
                type_boost = 0.05
                max_confidence = min(max_confidence + type_boost, 1.0)
                self.logger.debug(f"   🎯 ASSET TYPE MATCH: +{type_boost:.3f}")

        self.logger.debug(f"   📊 Final confidence: {max_confidence:.3f}")
        return max_confidence

    async def save_attachment_to_asset_folder(
        self,
        attachment_content: bytes,
        filename: str,
        processing_result: ProcessingResult,
        asset_id: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Save processed attachment to the appropriate asset folder.

        Uses the asset's defined folder_path to ensure consistent file organization.
        Creates document category subfolders within the asset's designated path.

        Args:
            attachment_content: Binary content of the attachment
            filename: Original filename of the attachment
            processing_result: Result of processing including classification
            asset_id: Asset ID to save to (if known)

        Returns:
            Path where file was saved, or None if saving failed
        """
        try:
            target_folder = None

            # Determine target folder based on asset match and confidence
            if asset_id and processing_result.confidence_level in [
                ConfidenceLevel.HIGH,
                ConfidenceLevel.MEDIUM,
            ]:
                # High/Medium confidence: Save to specific asset folder
                asset = await self.get_asset(asset_id)
                if asset:
                    # Use the asset's predefined folder path
                    asset_base_folder = self.base_assets_path / asset.folder_path

                    # Create document category subfolder within asset folder
                    if (
                        processing_result.document_category
                        and processing_result.document_category
                        != DocumentCategory.UNKNOWN
                    ):
                        target_folder = (
                            asset_base_folder
                            / processing_result.document_category.value
                        )
                        self.logger.info(
                            "Saving to asset folder with category: %s/%s",
                            asset.deal_name,
                            processing_result.document_category.value,
                        )
                    else:
                        target_folder = asset_base_folder / "uncategorized"
                        self.logger.info(
                            "Saving to asset folder (uncategorized): %s/uncategorized",
                            asset.deal_name,
                        )
                else:
                    self.logger.warning("Asset not found for ID: %s", asset_id)
                    # Fallback to generic uncategorized folder
                    target_folder = (
                        self.base_assets_path / "uncategorized" / "unknown_asset"
                    )

            elif asset_id and processing_result.confidence_level == ConfidenceLevel.LOW:
                # Low confidence with asset match: Save to asset's review subfolder
                asset = await self.get_asset(asset_id)
                if asset:
                    asset_base_folder = self.base_assets_path / asset.folder_path
                    target_folder = asset_base_folder / "needs_review"
                    self.logger.info(
                        "Saving to asset review folder: %s/needs_review",
                        asset.deal_name,
                    )
                else:
                    target_folder = (
                        self.base_assets_path / "to_be_reviewed" / "low_confidence"
                    )
            else:
                # Very low confidence or no asset match: Use review folders
                if processing_result.confidence_level == ConfidenceLevel.VERY_LOW:
                    target_folder = (
                        self.base_assets_path / "to_be_reviewed" / "very_low_confidence"
                    )
                    self.logger.info(
                        "Saving to general review folder: very low confidence"
                    )
                else:
                    target_folder = (
                        self.base_assets_path / "to_be_reviewed" / "no_asset_match"
                    )
                    self.logger.info("Saving to general review folder: no asset match")

            # Create folder structure
            target_folder.mkdir(parents=True, exist_ok=True)

            # Generate unique filename to avoid conflicts
            file_path = target_folder / filename
            counter = 1
            while file_path.exists():
                # Add counter to filename if it already exists
                stem = Path(filename).stem
                suffix = Path(filename).suffix
                new_filename = f"{stem}_{counter:03d}{suffix}"
                file_path = target_folder / new_filename
                counter += 1

            # Save the file
            with open(file_path, "wb") as f:
                f.write(attachment_content)

            self.logger.info("💾 File saved to: %s", file_path)

            # Update processing result with file path
            processing_result.file_path = file_path

            return file_path

        except Exception as e:
            self.logger.error("Failed to save attachment %s: %s", filename, e)
            return None

    async def store_processed_document(
        self,
        file_hash: str,
        processing_result: ProcessingResult,
        asset_id: Optional[str] = None,
    ) -> str:
        """Store processed document metadata in Qdrant."""
        document_id = str(uuid.uuid4())

        if not self.qdrant:
            return document_id

        try:
            dummy_vector = [0.0] * 384  # Placeholder vector

            payload = {
                "document_id": document_id,
                "file_hash": file_hash,
                "status": processing_result.status.value,
                "confidence": processing_result.confidence,
                "processing_date": datetime.now(UTC).isoformat(),
                "metadata": processing_result.metadata or {},
            }

            if asset_id:
                payload["asset_id"] = asset_id

            if processing_result.file_path:
                payload["file_path"] = str(processing_result.file_path)

            if processing_result.document_category:
                payload["document_category"] = processing_result.document_category.value

            if processing_result.confidence_level:
                payload["confidence_level"] = processing_result.confidence_level.value

            point = PointStruct(id=document_id, vector=dummy_vector, payload=payload)

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["processed_documents"], points=[point]
            )

            self.logger.info("📊 Document metadata stored: %s...", document_id[:8])
            return document_id

        except Exception as e:
            self.logger.error("Failed to store processed document: %s", e)
            return document_id

    async def check_duplicate(self, file_hash: str) -> Optional[str]:
        """
        Check if file hash already exists in processed documents.

        Args:
            file_hash: SHA256 hash of file content

        Returns:
            Document ID if duplicate found, None otherwise
        """
        if not self.qdrant:
            return None

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["processed_documents"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_hash", match=MatchValue(value=file_hash)
                        )
                    ]
                ),
                limit=1,
            )

            if search_result[0]:
                return search_result[0][0].payload.get("document_id")

            return None

        except Exception as e:
            self.logger.warning("Error checking duplicates: %s", e)
            return None

    def get_processing_stats(self) -> dict[str, Any]:
        """
        Get processing statistics including learning metrics.

        Returns:
            Dictionary with comprehensive processing statistics
        """
        total = sum(self.stats.values())

        return {
            "total_processed": self.stats["processed"],
            "successful": self.stats["processed"],
            "quarantined": self.stats["quarantined"],
            "duplicates": self.stats["duplicates"],
            "errors": self.stats["errors"],
            "learned_patterns": self.stats["learned"],
            "human_corrections": self.stats["corrected"],
            "learning_rate": (self.stats["learned"] / max(self.stats["processed"], 1)),
            "success_rate": (
                (self.stats["processed"] / max(total, 1) * 100) if total > 0 else 0.0
            ),
        }

    async def health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive agent health check.

        Returns:
            Dictionary with health status information
        """
        health = {
            "clamscan_available": self.security.clamscan_path is not None,
            "base_path_writable": False,
            "procedural_memory_available": self.procedural_memory is not None,
            "learned_patterns": 0,
            "qdrant_connected": self.qdrant is not None,
        }

        # Check file system
        try:
            test_file = self.base_assets_path / ".health_check"
            test_file.touch()
            test_file.unlink()
            health["base_path_writable"] = True
        except OSError:
            pass

        # Check procedural memory
        if self.procedural_memory:
            try:
                collection_name = self.procedural_memory.collections[
                    "classification_patterns"
                ]
                result = self.procedural_memory.qdrant.count(
                    collection_name=collection_name
                )
                health["learned_patterns"] = result.count
            except Exception:
                pass

        return health

    # Backward compatibility methods - simplified versions for basic functionality
    async def create_asset(
        self,
        deal_name: str,
        asset_name: str,
        asset_type: AssetType,
        identifiers: Optional[list[str]] = None,
    ) -> str:
        """
        Create asset definition with actual storage in Qdrant.

        Args:
            deal_name: Short name for the asset
            asset_name: Full descriptive name
            asset_type: Type of private market asset
            identifiers: Alternative names/identifiers

        Returns:
            Asset deal_id (UUID)
        """
        deal_id = str(uuid.uuid4())

        if not self.qdrant:
            self.logger.warning("No Qdrant client - asset creation disabled")
            return deal_id

        try:
            # Create asset record in Qdrant
            asset_data = {
                "deal_id": deal_id,
                "deal_name": deal_name,
                "asset_name": asset_name,
                "asset_type": asset_type.value,
                "identifiers": identifiers or [],
                "created_date": datetime.now(UTC).isoformat(),
                "last_updated": datetime.now(UTC).isoformat(),
                "folder_path": f"{deal_id}_{deal_name.replace(' ', '_')}",
            }

            # Store in assets collection
            point = PointStruct(
                id=deal_id, vector=[0.0] * 384, payload=asset_data  # Placeholder vector
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["assets"], points=[point]
            )

            # Create asset folder structure
            asset_folder = self.base_assets_path / asset_data["folder_path"]
            asset_folder.mkdir(parents=True, exist_ok=True)

            self.logger.info("✅ Created and stored asset: %s (%s)", deal_name, deal_id)
            return deal_id

        except Exception as e:
            self.logger.error("Failed to create asset %s: %s", deal_name, e)
            return deal_id

    async def get_asset(self, deal_id: str) -> Optional[Asset]:
        """
        Get asset by deal_id from Qdrant storage.

        Args:
            deal_id: Asset identifier

        Returns:
            Asset object if found, None otherwise
        """
        if not self.qdrant:
            self.logger.debug("No Qdrant client - cannot retrieve asset")
            return None

        try:
            # Retrieve specific asset by ID
            points = self.qdrant.retrieve(
                collection_name=self.COLLECTIONS["assets"], ids=[deal_id]
            )

            if not points:
                self.logger.debug("Asset not found: %s", deal_id)
                return None

            payload = points[0].payload
            asset = Asset(
                deal_id=payload["deal_id"],
                deal_name=payload["deal_name"],
                asset_name=payload["asset_name"],
                asset_type=AssetType(payload["asset_type"]),
                folder_path=payload["folder_path"],
                identifiers=payload.get("identifiers", []),
                created_date=datetime.fromisoformat(payload["created_date"]),
                last_updated=datetime.fromisoformat(payload["last_updated"]),
                metadata=payload.get("metadata"),
            )

            self.logger.debug("Retrieved asset: %s", deal_id)
            return asset

        except Exception as e:
            self.logger.error("Failed to retrieve asset %s: %s", deal_id, e)
            return None

    async def list_assets(self) -> list[Asset]:
        """
        List all assets from Qdrant storage.

        Returns:
            List of Asset objects
        """
        if not self.qdrant:
            self.logger.debug("No Qdrant client - returning empty asset list")
            return []

        try:
            # Get all assets from the collection
            scroll_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["assets"],
                limit=1000,  # Adjust as needed
            )

            assets = []
            for point in scroll_result[0]:
                payload = point.payload
                try:
                    asset = Asset(
                        deal_id=payload["deal_id"],
                        deal_name=payload["deal_name"],
                        asset_name=payload["asset_name"],
                        asset_type=AssetType(payload["asset_type"]),
                        folder_path=payload["folder_path"],
                        identifiers=payload.get("identifiers", []),
                        created_date=datetime.fromisoformat(payload["created_date"]),
                        last_updated=datetime.fromisoformat(payload["last_updated"]),
                        metadata=payload.get("metadata"),
                    )
                    assets.append(asset)
                except (ValueError, KeyError) as e:
                    self.logger.warning(
                        "Invalid asset data in point %s: %s", point.id, e
                    )
                    continue

            self.logger.debug("Retrieved %d assets from storage", len(assets))
            return assets

        except Exception as e:
            self.logger.error("Failed to list assets: %s", e)
            return []

    async def list_asset_sender_mappings(self) -> list[dict[str, Any]]:
        """
        List asset sender mappings (backward compatibility).

        Returns:
            List of sender mapping dictionaries
        """
        mappings = []

        if not self.qdrant:
            self.logger.debug("No Qdrant client - returning empty mappings list")
            return mappings

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                limit=1000,  # Adjust as needed
                with_payload=True,
                with_vectors=False,
            )

            for point in search_result[0]:
                payload = point.payload
                mappings.append(
                    {
                        "mapping_id": payload["mapping_id"],
                        "asset_id": payload["asset_id"],
                        "sender_email": payload["sender_email"],
                        "confidence": payload["confidence"],
                        "document_types": payload.get("document_types", []),
                        "created_date": payload["created_date"],
                        "last_activity": payload["last_activity"],
                        "email_count": payload.get("email_count", 0),
                    }
                )

            self.logger.debug(
                "Retrieved %d sender mappings from storage", len(mappings)
            )

        except Exception as e:
            self.logger.error("Failed to list sender mappings: %s", e)

        return mappings

    async def create_asset_sender_mapping(
        self,
        sender_email: str,
        deal_id: str,
        confidence: float = 1.0,
        source: str = "manual",
    ) -> str:
        """
        Create asset sender mapping (backward compatibility).

        Args:
            sender_email: Email address of sender
            deal_id: Asset deal ID to map to
            confidence: Confidence in mapping
            source: Source of mapping (manual, learned, etc.)

        Returns:
            Mapping ID
        """
        mapping_id = str(uuid.uuid4())
        self.logger.info("Created sender mapping: %s -> %s", sender_email, deal_id)
        # TODO: Implement sender mapping creation in procedural memory
        return mapping_id

    async def delete_asset_sender_mapping(self, mapping_id: str) -> bool:
        """
        Delete asset sender mapping (backward compatibility).

        Args:
            mapping_id: ID of mapping to delete

        Returns:
            True if deleted, False otherwise
        """
        self.logger.info("Deleted sender mapping: %s", mapping_id)
        # TODO: Implement sender mapping deletion in procedural memory
        return True

    async def update_asset_sender_mapping(
        self,
        mapping_id: str,
        sender_email: Optional[str] = None,
        deal_id: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> bool:
        """
        Update asset sender mapping (backward compatibility).

        Args:
            mapping_id: ID of mapping to update
            sender_email: New sender email
            deal_id: New deal ID
            confidence: New confidence

        Returns:
            True if updated, False otherwise
        """
        self.logger.info("Updated sender mapping: %s", mapping_id)
        # TODO: Implement sender mapping update in procedural memory
        return True

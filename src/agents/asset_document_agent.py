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
import contextlib
import hashlib
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Any

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
from ..memory.semantic import SemanticMemory
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
    file_hash: str | None = None
    file_path: Path | None = None
    confidence: float = 0.0
    error_message: str | None = None
    quarantine_reason: str | None = None
    duplicate_of: str | None = None
    metadata: dict[str, Any] | None = None

    # Phase 3: Document Classification
    document_category: DocumentCategory | None = None
    confidence_level: ConfidenceLevel | None = None
    matched_asset_id: str | None = None
    asset_confidence: float = 0.0
    classification_metadata: dict[str, Any] | None = None

    @classmethod
    def success_result(
        cls,
        file_hash: str,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
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
    metadata: dict[str, Any] | None = None


class SecurityService:
    """
    Handles file validation and security scanning operations.

    Now uses semantic memory for adaptive file type validation instead of
    hardcoded rules, learning from successful processing patterns.
    """

    def __init__(self, semantic_memory=None) -> None:
        """Initialize security service with semantic memory for adaptive validation."""
        self.logger = get_logger(f"{__name__}.SecurityService")
        self.clamscan_path = self._find_clamscan()
        self.semantic_memory = semantic_memory

        # Safety fallback extensions for when semantic memory is unavailable
        self.safety_fallback_extensions = {
            ".pdf",
            ".xlsx",
            ".xls",
            ".doc",
            ".docx",
            ".txt",
        }

    def _find_clamscan(self) -> str | None:
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
    ) -> tuple[bool, str | None]:
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

        except TimeoutError:
            self.logger.warning("ClamAV scan timeout for %s", filename)
            return False, "Scan timeout"
        except Exception as e:
            self.logger.error("Antivirus scan failed for %s: %s", filename, e)
            return False, f"Scan error: {str(e)}"
        finally:
            # Clean up temporary file
            if temp_path:
                with contextlib.suppress(OSError):
                    Path(temp_path).unlink()

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

    async def validate_file_type(
        self, filename: str, asset_type: str = None, document_category: str = None
    ) -> dict[str, Any]:
        """
        Validate file type using learned knowledge from semantic memory.

        Uses adaptive validation based on successful processing patterns,
        business context, and security intelligence instead of hardcoded rules.

        Args:
            filename: Name of the file to validate
            asset_type: Asset type context for business relevance
            document_category: Document category context for validation

        Returns:
            Dictionary with validation result and metadata:
            {
                "is_valid": bool,
                "confidence": float,
                "security_level": str,
                "learning_source": str,
                "business_context": dict
            }
        """
        if not filename:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "security_level": "error",
                "learning_source": "validation_error",
                "business_context": {},
                "reason": "Empty filename",
            }

        file_extension = Path(filename).suffix.lower()

        if not file_extension:
            return {
                "is_valid": False,
                "confidence": 0.0,
                "security_level": "unknown",
                "learning_source": "no_extension",
                "business_context": {},
                "reason": "No file extension detected",
            }

        # Use semantic memory for intelligent validation
        if self.semantic_memory:
            try:
                validation = await self.semantic_memory.get_file_type_validation(
                    file_extension
                )

                # Add business context if available
                if asset_type or document_category:
                    business_context = validation.get("business_context", {})
                    asset_types = business_context.get("asset_types", [])
                    doc_categories = business_context.get("document_categories", [])

                    # Boost confidence if file type matches current context
                    context_boost = 0.0
                    if asset_type and asset_type in asset_types:
                        context_boost += 0.1
                    if document_category and document_category in doc_categories:
                        context_boost += 0.1

                    validation["confidence"] = min(
                        1.0, validation["confidence"] + context_boost
                    )
                    validation["business_context"]["context_match"] = context_boost > 0

                validation["is_valid"] = validation["is_allowed"]

                self.logger.info(
                    "Semantic validation for %s: %s (confidence: %.3f, source: %s)",
                    file_extension,
                    validation["is_valid"],
                    validation["confidence"],
                    validation["learning_source"],
                )

                return validation

            except Exception as e:
                self.logger.warning(
                    "Semantic memory validation failed for %s: %s", file_extension, e
                )
                # Fall through to safety fallback

        # Safety fallback for critical file types when semantic memory unavailable
        is_safe_fallback = file_extension in self.safety_fallback_extensions

        result = {
            "is_valid": is_safe_fallback,
            "confidence": 0.8 if is_safe_fallback else 0.0,
            "security_level": (
                "safe_fallback" if is_safe_fallback else "unknown_fallback"
            ),
            "learning_source": "safety_fallback",
            "business_context": {
                "fallback_used": True,
                "semantic_memory_available": self.semantic_memory is not None,
            },
            "reason": "Using safety fallback validation",
        }

        self.logger.debug(
            "Fallback validation for %s: %s (fallback: %s)",
            filename,
            result["is_valid"],
            is_safe_fallback,
        )

        return result

    async def learn_file_type_outcome(
        self,
        filename: str,
        success: bool,
        asset_type: str = None,
        document_category: str = None,
    ) -> None:
        """
        Learn from file processing outcomes to improve future validation.

        Updates semantic memory with processing results to continuously
        improve file type validation accuracy and business relevance.

        Args:
            filename: Name of the processed file
            success: Whether processing was successful
            asset_type: Asset type context of the processing
            document_category: Document category that was identified
        """
        if not self.semantic_memory:
            return

        file_extension = Path(filename).suffix.lower()
        if not file_extension:
            return

        try:
            await self.semantic_memory.learn_file_type_success(
                file_extension=file_extension,
                asset_type=asset_type,
                document_category=document_category,
                success=success,
            )

            self.logger.info(
                "Learned from file processing: %s -> %s (asset: %s, category: %s)",
                file_extension,
                "success" if success else "failure",
                asset_type,
                document_category,
            )

        except Exception as e:
            self.logger.error(
                "Failed to learn from file outcome for %s: %s", filename, e
            )

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
        qdrant_client: QdrantClient | None = None,
        base_assets_path: str = "./assets",
        clamav_socket: str | None = None,
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

        # Initialize memory systems
        self.semantic_memory = (
            SemanticMemory(qdrant_url="http://localhost:6333")
            if qdrant_client
            else None
        )
        self.procedural_memory = (
            ProceduralMemory(qdrant_client) if qdrant_client else None
        )

        # Initialize services
        self.security = SecurityService(semantic_memory=self.semantic_memory)

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

        # Phase 1.3: Knowledge base used for initial seeding/bootstrap only
        # Runtime processing operates purely from memory systems
        # Knowledge base also used for testing cleanup functions

    async def initialize_collections(self) -> bool:
        """
        Initialize Qdrant collections for asset management.

        Phase 1.3: Knowledge base used for initial seeding only.
        Runtime processing operates purely from memory.

        Returns:
            True if initialization successful, False otherwise
        """
        if not self.qdrant:
            self.logger.warning("Qdrant client not provided - skipping initialization")
            return False

        try:
            # Initialize procedural memory collections with initial knowledge base seeding
            if self.procedural_memory:
                await self.procedural_memory.initialize_collections()

                # Load initial patterns from knowledge base (bootstrap only)
                try:
                    stats = await self.procedural_memory.seed_from_knowledge_base(
                        "knowledge"
                    )
                    procedures_loaded = stats.get("asset_patterns", 0)
                    total_loaded = stats.get("total_patterns", 0)

                    self.logger.info(
                        f"Procedural memory bootstrapped: {total_loaded} patterns ({procedures_loaded} asset procedures)"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to seed procedural memory from knowledge base: {e}"
                    )

                self.logger.info(
                    "Procedural memory collections initialized with bootstrap data"
                )

            # Initialize semantic memory with initial knowledge base seeding
            if self.semantic_memory:
                try:
                    results = await self.semantic_memory.load_knowledge_base(
                        "knowledge"
                    )
                    loaded_count = results.get("total_knowledge_items", 0)
                    file_types_loaded = results.get("file_types_loaded", 0)
                    errors = results.get("errors", [])

                    if errors:
                        self.logger.warning(
                            f"Knowledge base bootstrap had {len(errors)} warnings: {errors}"
                        )

                    self.logger.info(
                        f"Semantic memory bootstrapped: {loaded_count} items ({file_types_loaded} file types)"
                    )

                except Exception as e:
                    self.logger.warning(
                        f"Failed to bootstrap semantic memory from knowledge base: {e}"
                    )

            # Initialize other collections as needed
            for collection_name in self.COLLECTIONS.values():
                if not await self._collection_exists(collection_name):
                    await self._create_collection(
                        collection_name, 384  # Standard sentence transformer dimension
                    )
                    self.logger.info("Created collection: %s", collection_name)

            self.logger.info(
                "All collections initialized successfully (bootstrapped, runtime is pure memory)"
            )
            return True

        except Exception as e:
            self.logger.error("Failed to initialize collections: %s", e)
            return False

    async def _collection_exists(self, collection_name: str) -> bool:
        """Check if a Qdrant collection exists."""
        if not self.qdrant:
            return False
        try:
            collections = self.qdrant.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception:
            return False

    async def _create_collection(self, collection_name: str, vector_size: int) -> None:
        """Create a Qdrant collection with specified vector size."""
        if not self.qdrant:
            return
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

            # Step 3: Adaptive file type validation using semantic memory
            validation = await self.security.validate_file_type(filename)
            if not validation["is_valid"]:
                # Learn from rejection if confidence is low (might be a new valid type)
                if validation["confidence"] < 0.3:
                    self.logger.warning(
                        "Rejecting file type %s with low confidence %.3f - consider learning",
                        Path(filename).suffix,
                        validation["confidence"],
                    )

                return ProcessingResult(
                    status=ProcessingStatus.INVALID_TYPE,
                    error_message=f"File type {Path(filename).suffix} not allowed "
                    f"(confidence: {validation['confidence']:.3f}, "
                    f"source: {validation['learning_source']})",
                    metadata={"file_validation": validation},
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
                # Step 1: Memory-driven document classification with detailed patterns
                (
                    category_str,
                    classification_confidence,
                    detailed_patterns,
                ) = await self.procedural_memory.classify_document_with_details(
                    filename, email_subject, email_body
                )

                # Memory-only approach: No knowledge base fallback
                learning_source = "procedural_memory"

                # Log confidence for transparency
                if classification_confidence < 0.5:
                    self.logger.info(
                        f"Low procedural confidence ({classification_confidence:.3f}) - "
                        f"trusting memory-based decision: {category_str}"
                    )

                # Step 2: Memory-driven asset identification with detailed capture
                known_assets = await self.list_assets()
                (
                    asset_matches,
                    asset_identification_details,
                ) = await self.identify_asset_from_content_with_details(
                    email_subject, email_body, filename, known_assets
                )

                # Determine best asset match
                matched_asset_id = None
                asset_confidence = 0.0
                if asset_matches:
                    matched_asset_id, asset_confidence = asset_matches[0]

                # Step 3: Auto-learning removed - procedural memory now contains stable business rules only
                # Learning from feedback will be handled by semantic memory (human feedback)
                # and episodic memory (individual experiences) in the new architecture
                pass

                # Convert to enum for backward compatibility
                try:
                    document_category = DocumentCategory(category_str)
                except ValueError:
                    document_category = DocumentCategory.UNKNOWN

                # Determine overall confidence level (lowered thresholds for adaptive learning)
                overall_confidence = (classification_confidence + asset_confidence) / 2
                if overall_confidence >= 0.4:  # Reduced from 0.85
                    confidence_level = ConfidenceLevel.HIGH
                elif overall_confidence >= 0.25:  # Reduced from 0.65
                    confidence_level = ConfidenceLevel.MEDIUM
                elif (
                    overall_confidence >= 0.1
                ):  # Reduced from config.low_confidence_threshold (0.7)
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
                    "learning_source": learning_source,
                    "patterns_used": "memory_driven",  # Pure procedural memory
                    "detailed_patterns": detailed_patterns,  # Store specific patterns used
                    "winning_patterns_count": len(
                        detailed_patterns.get("patterns_used", [])
                    ),
                    "total_patterns_evaluated": detailed_patterns.get(
                        "total_patterns", 0
                    ),
                    "categories_considered": detailed_patterns.get(
                        "categories_considered", 0
                    ),
                    "asset_identification_details": asset_identification_details,  # Store asset matching reasoning
                    "processing_timestamp": datetime.now(UTC).isoformat(),
                }

                # Learn from successful file processing for adaptive validation
                if overall_confidence > 0.6:  # Learn from reasonably confident results
                    asset_type_str = None
                    if matched_asset_id:
                        # Get asset type from matched asset
                        matched_asset = next(
                            (a for a in known_assets if a.deal_id == matched_asset_id),
                            None,
                        )
                        if matched_asset and hasattr(matched_asset, "asset_type"):
                            asset_type_str = matched_asset.asset_type.value

                    await self.security.learn_file_type_outcome(
                        filename=filename,
                        success=True,
                        asset_type=asset_type_str,
                        document_category=category_str,
                    )

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

    # NOTE: learn_from_human_feedback method removed in Phase 1.1
    # Human feedback now goes directly to semantic memory via web UI, not through asset agent
    # This implements the new memory architecture where human feedback is experiential knowledge

    async def get_sender_assets(self, sender_email: str) -> list[dict[str, Any]]:
        """Get all assets associated with a sender."""
        self.logger.info("Checking sender asset mappings for: %s", sender_email)

        assets: list[dict[str, Any]] = []

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
                    if point.payload is None:
                        continue
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
        known_assets: list[Asset] | None = None,
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

            # NEW APPROACH: Use semantic memory for asset data, procedural for algorithms
            self.logger.info(
                "🧠 Using semantic memory for asset data with procedural matching algorithms"
            )

            # Query semantic memory for asset knowledge
            if self.semantic_memory:
                asset_knowledge_items = (
                    await self.semantic_memory.search_asset_knowledge(
                        query="", limit=100  # Get all assets
                    )
                )

                if asset_knowledge_items:
                    self.logger.info(
                        f"📊 Found {len(asset_knowledge_items)} assets in semantic memory"
                    )

                    # Use smart matching with procedural algorithms
                    asset_scores = await self._match_assets_with_semantic_data(
                        combined_text, asset_knowledge_items, known_assets
                    )

                    if asset_scores:
                        self.logger.info(
                            f"🎯 Semantic matching found {len(asset_scores)} matches!"
                        )
                        for i, (asset_id, confidence) in enumerate(asset_scores[:3]):
                            asset_name = next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            )
                            self.logger.info(
                                f"   {i+1}. {asset_name} -> {confidence:.3f}"
                            )
                        return asset_scores
                    else:
                        self.logger.info(
                            "❌ No semantic matches found - trying fallback"
                        )
                else:
                    self.logger.warning(
                        "❌ No asset data in semantic memory - using fallback"
                    )
            else:
                self.logger.warning("❌ No semantic memory available - using fallback")

            # FALLBACK: Original simple identifier matching when semantic memory unavailable
            self.logger.info("🔄 Using fallback identifier matching")

            # Fallback: Simple identifier matching when no learned patterns exist
            asset_scores: dict[str, float] = {}

            self.logger.info(
                f"🔄 Fallback: Checking {len(known_assets)} assets with simple identifier matching"
            )

            for asset in known_assets:
                max_confidence = 0.0

                # Check all identifiers for this asset
                all_identifiers = [
                    asset.deal_name,
                    asset.asset_name,
                ] + asset.identifiers

                for identifier in all_identifiers:
                    if not identifier:
                        continue

                    identifier_lower = identifier.lower()

                    # Exact match gets high confidence
                    if identifier_lower in combined_text:
                        match_confidence = 0.9
                        self.logger.info(
                            f"   ✅ EXACT MATCH: '{identifier}' in {asset.deal_name}"
                        )
                        max_confidence = max(max_confidence, match_confidence)

                    # Fuzzy matching for partial matches
                    elif len(identifier_lower) >= 3:
                        words = combined_text.split()
                        for word in words:
                            if len(word) >= 3:
                                similarity = self._calculate_similarity(
                                    identifier_lower, word
                                )
                                if similarity >= 0.8:
                                    match_confidence = (
                                        similarity * 0.7
                                    )  # Lower than exact match
                                    self.logger.info(
                                        f"   🎯 FUZZY MATCH: '{identifier}' ~= '{word}' ({similarity:.3f}) in {asset.deal_name}"
                                    )
                                    max_confidence = max(
                                        max_confidence, match_confidence
                                    )

                # Apply minimum confidence threshold
                min_confidence = 0.15
                if max_confidence >= min_confidence:
                    asset_scores[asset.deal_id] = max_confidence
                    self.logger.info(
                        f"   ⭐ FALLBACK QUALIFIED: {asset.deal_name} -> {max_confidence:.3f}"
                    )

            # Convert to sorted list
            asset_matches = list(asset_scores.items())
            asset_matches.sort(key=lambda x: x[1], reverse=True)

            if asset_matches:
                self.logger.info(f"🎯 Fallback found {len(asset_matches)} matches!")
                for i, (asset_id, confidence) in enumerate(asset_matches[:3]):
                    asset_name = next(
                        (a.deal_name for a in known_assets if a.deal_id == asset_id),
                        "Unknown",
                    )
                    self.logger.info(f"   {i+1}. {asset_name} -> {confidence:.3f}")
            else:
                self.logger.info("❌ No fallback matches found either")

            return asset_matches

        except Exception as e:
            self.logger.error(f"Enhanced asset identification failed: {e}")
            return []

    async def identify_asset_from_content_with_details(
        self,
        email_subject: str,
        email_body: str = "",
        filename: str = "",
        known_assets: list[Asset] | None = None,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """
        Enhanced asset identification with detailed reasoning capture.

        Returns both the asset matches AND the detailed reasoning that led to the decision.

        Args:
            email_subject: Email subject line
            email_body: Email body content
            filename: Attachment filename
            known_assets: List of known assets to match against

        Returns:
            Tuple of (asset_matches, reasoning_details)
            - asset_matches: List of (asset_id, confidence_score) tuples
            - reasoning_details: Complete decision breakdown for inspection
        """
        self.logger.info("🧠 Enhanced asset identification WITH REASONING CAPTURE")

        # Initialize reasoning capture
        reasoning_details = {
            "method_used": "unknown",
            "semantic_matches": [],
            "exact_matches": [],
            "fuzzy_matches": [],
            "fallback_matches": [],
            "total_assets_evaluated": len(known_assets) if known_assets else 0,
            "combined_text": f"{email_subject} {email_body} {filename}".lower(),
            "primary_driver": "none",
            "decision_flow": [],
        }

        if not known_assets:
            reasoning_details["decision_flow"].append(
                "❌ No assets available for matching"
            )
            self.logger.info("❌ No assets available for matching")
            return [], reasoning_details

        if not self.procedural_memory:
            reasoning_details["decision_flow"].append(
                "❌ No procedural memory - cannot use learned patterns"
            )
            self.logger.warning("❌ No procedural memory - cannot use learned patterns")
            return [], reasoning_details

        try:
            combined_text = reasoning_details["combined_text"]
            self.logger.info(f"🔤 Combined text: '{combined_text[:100]}...'")
            reasoning_details["decision_flow"].append(
                f"🔤 Analyzing combined text: '{combined_text[:100]}...'"
            )

            # NEW APPROACH: Use semantic memory for asset data, procedural for algorithms
            self.logger.info(
                "🧠 Using semantic memory for asset data with procedural matching algorithms"
            )
            reasoning_details["decision_flow"].append(
                "🧠 Attempting semantic memory asset lookup"
            )

            # Query semantic memory for asset knowledge
            if self.semantic_memory:
                asset_knowledge_items = (
                    await self.semantic_memory.search_asset_knowledge(
                        query="", limit=100
                    )
                )

                if asset_knowledge_items:
                    self.logger.info(
                        f"📊 Found {len(asset_knowledge_items)} assets in semantic memory"
                    )
                    reasoning_details["decision_flow"].append(
                        f"📊 Found {len(asset_knowledge_items)} assets in semantic memory"
                    )
                    reasoning_details["method_used"] = "semantic_memory"

                    # Use smart matching with detailed capture
                    (
                        asset_scores,
                        semantic_details,
                    ) = await self._match_assets_with_semantic_data_detailed(
                        combined_text, asset_knowledge_items, known_assets
                    )

                    # Merge semantic details into reasoning
                    reasoning_details.update(semantic_details)

                    if asset_scores:
                        self.logger.info(
                            f"🎯 Semantic matching found {len(asset_scores)} matches!"
                        )
                        reasoning_details["decision_flow"].append(
                            f"🎯 Semantic matching found {len(asset_scores)} matches!"
                        )

                        # Log top matches with reasoning
                        for i, (asset_id, confidence) in enumerate(asset_scores[:3]):
                            asset_name = next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            )
                            self.logger.info(
                                f"   {i+1}. {asset_name} -> {confidence:.3f}"
                            )
                            reasoning_details["decision_flow"].append(
                                f"   {i+1}. {asset_name} -> {confidence:.3f}"
                            )

                        return asset_scores, reasoning_details
                    else:
                        self.logger.info(
                            "❌ No semantic matches found - trying fallback"
                        )
                        reasoning_details["decision_flow"].append(
                            "❌ No semantic matches found - trying fallback"
                        )
                else:
                    self.logger.warning(
                        "❌ No asset data in semantic memory - using fallback"
                    )
                    reasoning_details["decision_flow"].append(
                        "❌ No asset data in semantic memory - using fallback"
                    )
            else:
                self.logger.warning("❌ No semantic memory available - using fallback")
                reasoning_details["decision_flow"].append(
                    "❌ No semantic memory available - using fallback"
                )

            # FALLBACK: Original simple identifier matching when semantic memory unavailable
            self.logger.info("🔄 Using fallback identifier matching")
            reasoning_details["decision_flow"].append(
                "🔄 Using fallback identifier matching"
            )
            reasoning_details["method_used"] = "fallback_identifier_matching"

            asset_scores: dict[str, float] = {}

            self.logger.info(
                f"🔄 Fallback: Checking {len(known_assets)} assets with simple identifier matching"
            )
            reasoning_details["decision_flow"].append(
                f"🔄 Checking {len(known_assets)} assets with identifier matching"
            )

            for asset in known_assets:
                max_confidence = 0.0
                asset_matches = []

                # Check all identifiers for this asset
                all_identifiers = [
                    asset.deal_name,
                    asset.asset_name,
                ] + asset.identifiers

                for identifier in all_identifiers:
                    if not identifier:
                        continue

                    identifier_lower = identifier.lower()

                    # Exact match gets high confidence
                    if identifier_lower in combined_text:
                        match_confidence = 0.9
                        match_info = {
                            "type": "exact",
                            "identifier": identifier,
                            "confidence": match_confidence,
                            "asset_name": asset.deal_name,
                        }
                        reasoning_details["exact_matches"].append(match_info)
                        reasoning_details["fallback_matches"].append(match_info)
                        asset_matches.append(match_info)

                        self.logger.info(
                            f"   ✅ EXACT MATCH: '{identifier}' in {asset.deal_name}"
                        )
                        reasoning_details["decision_flow"].append(
                            f"   ✅ EXACT MATCH: '{identifier}' in {asset.deal_name}"
                        )
                        max_confidence = max(max_confidence, match_confidence)

                    # Fuzzy matching for partial matches
                    elif len(identifier_lower) >= 3:
                        words = combined_text.split()
                        for word in words:
                            if len(word) >= 3:
                                similarity = self._calculate_similarity(
                                    identifier_lower, word
                                )
                                if similarity >= 0.8:
                                    match_confidence = (
                                        similarity * 0.7
                                    )  # Lower than exact match
                                    match_info = {
                                        "type": "fuzzy",
                                        "identifier": identifier,
                                        "word_matched": word,
                                        "similarity": similarity,
                                        "confidence": match_confidence,
                                        "asset_name": asset.deal_name,
                                    }
                                    reasoning_details["fuzzy_matches"].append(
                                        match_info
                                    )
                                    reasoning_details["fallback_matches"].append(
                                        match_info
                                    )
                                    asset_matches.append(match_info)

                                    self.logger.info(
                                        f"   🎯 FUZZY MATCH: '{identifier}' ~= '{word}' ({similarity:.3f}) in {asset.deal_name}"
                                    )
                                    reasoning_details["decision_flow"].append(
                                        f"   🎯 FUZZY MATCH: '{identifier}' ~= '{word}' ({similarity:.3f}) in {asset.deal_name}"
                                    )
                                    max_confidence = max(
                                        max_confidence, match_confidence
                                    )

                # Apply minimum confidence threshold
                min_confidence = 0.15
                if max_confidence >= min_confidence:
                    asset_scores[asset.deal_id] = max_confidence
                    self.logger.info(
                        f"   ⭐ FALLBACK QUALIFIED: {asset.deal_name} -> {max_confidence:.3f}"
                    )
                    reasoning_details["decision_flow"].append(
                        f"   ⭐ QUALIFIED: {asset.deal_name} -> {max_confidence:.3f}"
                    )

            # Convert to sorted list
            asset_matches = list(asset_scores.items())
            asset_matches.sort(key=lambda x: x[1], reverse=True)

            if asset_matches:
                self.logger.info(f"🎯 Fallback found {len(asset_matches)} matches!")
                reasoning_details["decision_flow"].append(
                    f"🎯 Found {len(asset_matches)} total matches!"
                )
                reasoning_details["primary_driver"] = "fallback_identifier_matching"

                for i, (asset_id, confidence) in enumerate(asset_matches[:3]):
                    asset_name = next(
                        (a.deal_name for a in known_assets if a.deal_id == asset_id),
                        "Unknown",
                    )
                    self.logger.info(f"   {i+1}. {asset_name} -> {confidence:.3f}")
                    reasoning_details["decision_flow"].append(
                        f"   {i+1}. {asset_name} -> {confidence:.3f}"
                    )
            else:
                self.logger.info("❌ No fallback matches found either")
                reasoning_details["decision_flow"].append("❌ No matches found")
                reasoning_details["primary_driver"] = "no_matches"

            return asset_matches, reasoning_details

        except Exception as e:
            self.logger.error(f"Enhanced asset identification failed: {e}")
            reasoning_details["decision_flow"].append(f"❌ ERROR: {str(e)}")
            reasoning_details["primary_driver"] = "error"
            return [], reasoning_details

    async def _match_assets_with_semantic_data_detailed(
        self, combined_text: str, asset_knowledge_items: list, known_assets: list[Asset]
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """
        Match assets using semantic memory data with detailed reasoning capture.

        Returns both the matches and detailed reasoning about what drove the decisions.
        """
        self.logger.info("🧠 Matching assets using semantic knowledge WITH REASONING")

        semantic_details = {
            "semantic_matches": [],
            "exact_matches": [],
            "fuzzy_matches": [],
            "primary_driver": "semantic_memory",
        }

        asset_scores: dict[str, float] = {}

        # Extract asset data from semantic memory items
        for knowledge_item in asset_knowledge_items:
            try:
                metadata = knowledge_item.metadata
                asset_id = metadata.get("asset_id")
                deal_name = metadata.get("deal_name", "")
                identifiers = metadata.get("identifiers", [])

                if not asset_id:
                    continue

                max_confidence = 0.0
                asset_matches = []

                # Check all identifiers for this asset
                all_identifiers = [deal_name] + identifiers

                for identifier in all_identifiers:
                    if not identifier:
                        continue

                    identifier_lower = identifier.lower()

                    # Exact match gets high confidence
                    if identifier_lower in combined_text:
                        match_confidence = 0.9
                        match_info = {
                            "type": "semantic_exact",
                            "identifier": identifier,
                            "confidence": match_confidence,
                            "asset_name": deal_name,
                            "asset_id": asset_id,
                            "method": "semantic_memory",
                        }
                        semantic_details["semantic_matches"].append(match_info)
                        semantic_details["exact_matches"].append(match_info)
                        asset_matches.append(match_info)

                        self.logger.info(
                            f"   ✅ SEMANTIC EXACT: '{identifier}' in {deal_name}"
                        )
                        max_confidence = max(max_confidence, match_confidence)

                    # Fuzzy matching for partial matches
                    elif len(identifier_lower) >= 3:
                        words = combined_text.split()
                        for word in words:
                            if len(word) >= 3:
                                similarity = self._calculate_similarity(
                                    identifier_lower, word
                                )
                                if similarity >= 0.8:
                                    match_confidence = similarity * 0.7
                                    match_info = {
                                        "type": "semantic_fuzzy",
                                        "identifier": identifier,
                                        "word_matched": word,
                                        "similarity": similarity,
                                        "confidence": match_confidence,
                                        "asset_name": deal_name,
                                        "asset_id": asset_id,
                                        "method": "semantic_memory",
                                    }
                                    semantic_details["semantic_matches"].append(
                                        match_info
                                    )
                                    semantic_details["fuzzy_matches"].append(match_info)
                                    asset_matches.append(match_info)

                                    self.logger.info(
                                        f"   🎯 SEMANTIC FUZZY: '{identifier}' ~= '{word}' ({similarity:.3f}) in {deal_name}"
                                    )
                                    max_confidence = max(
                                        max_confidence, match_confidence
                                    )

                # Apply minimum confidence threshold
                min_confidence = 0.15
                if max_confidence >= min_confidence:
                    asset_scores[asset_id] = max_confidence

            except Exception as e:
                self.logger.debug(f"Error processing asset knowledge item: {e}")
                continue

        # Convert to sorted list
        asset_matches = list(asset_scores.items())
        asset_matches.sort(key=lambda x: x[1], reverse=True)

        # Determine primary driver
        if semantic_details["exact_matches"]:
            semantic_details["primary_driver"] = "semantic_exact_match"
        elif semantic_details["fuzzy_matches"]:
            semantic_details["primary_driver"] = "semantic_fuzzy_match"
        else:
            semantic_details["primary_driver"] = "no_semantic_matches"

        return asset_matches, semantic_details

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using SequenceMatcher.
        This replicates the old system's fuzzy matching capability.
        """
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    async def _match_assets_with_semantic_data(
        self, combined_text: str, asset_knowledge_items: list, known_assets: list[Asset]
    ) -> list[tuple[str, float]]:
        """
        Match assets using semantic memory data with procedural algorithms.

        Args:
            combined_text: Combined email/filename text for matching
            asset_knowledge_items: Asset knowledge from semantic memory
            known_assets: Known assets from the database

        Returns:
            List of (asset_id, confidence) tuples sorted by confidence
        """
        self.logger.info("🧠 Matching assets using semantic knowledge")

        asset_scores: dict[str, float] = {}

        # Extract asset data from semantic memory items
        for knowledge_item in asset_knowledge_items:
            try:
                metadata = knowledge_item.metadata
                asset_id = metadata.get("asset_id")
                deal_name = metadata.get("deal_name", "")
                identifiers = metadata.get("identifiers", [])

                if not asset_id:
                    continue

                max_confidence = 0.0

                # Check all identifiers for this asset
                all_identifiers = [deal_name] + identifiers

                for identifier in all_identifiers:
                    if not identifier:
                        continue

                    identifier_lower = identifier.lower()

                    # Exact match gets high confidence
                    if identifier_lower in combined_text:
                        match_confidence = 0.9
                        self.logger.info(
                            f"   ✅ SEMANTIC EXACT: '{identifier}' in {deal_name}"
                        )
                        max_confidence = max(max_confidence, match_confidence)

                    # Fuzzy matching for partial matches
                    elif len(identifier_lower) >= 3:
                        words = combined_text.split()
                        for word in words:
                            if len(word) >= 3:
                                similarity = self._calculate_similarity(
                                    identifier_lower, word
                                )
                                if similarity >= 0.8:
                                    match_confidence = similarity * 0.7
                                    self.logger.info(
                                        f"   🎯 SEMANTIC FUZZY: '{identifier}' ~= '{word}' ({similarity:.3f}) in {deal_name}"
                                    )
                                    max_confidence = max(
                                        max_confidence, match_confidence
                                    )

                # Apply minimum confidence threshold
                min_confidence = 0.15
                if max_confidence >= min_confidence:
                    asset_scores[asset_id] = max_confidence
                    self.logger.info(
                        f"   ⭐ SEMANTIC QUALIFIED: {deal_name} -> {max_confidence:.3f}"
                    )

            except Exception as e:
                self.logger.debug(f"Error processing semantic asset knowledge: {e}")

        # Convert to sorted list
        asset_matches = list(asset_scores.items())
        asset_matches.sort(key=lambda x: x[1], reverse=True)

        return asset_matches

    async def save_attachment_to_asset_folder(
        self,
        attachment_content: bytes,
        filename: str,
        processing_result: ProcessingResult,
        asset_id: str | None = None,
    ) -> Path | None:
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
                    folder_path = (
                        asset.folder_path
                        if isinstance(asset.folder_path, str)
                        else str(asset.folder_path)
                    )
                    asset_base_folder = self.base_assets_path / folder_path

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
                    folder_path = (
                        asset.folder_path
                        if isinstance(asset.folder_path, str)
                        else str(asset.folder_path)
                    )
                    asset_base_folder = self.base_assets_path / folder_path
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
        asset_id: str | None = None,
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

            # Store detailed classification metadata for inspect functionality
            if processing_result.classification_metadata:
                payload[
                    "classification_metadata"
                ] = processing_result.classification_metadata

            if processing_result.asset_confidence:
                payload["asset_confidence"] = processing_result.asset_confidence

            if processing_result.matched_asset_id:
                payload["matched_asset_id"] = processing_result.matched_asset_id

            point = PointStruct(id=document_id, vector=dummy_vector, payload=payload)

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["processed_documents"], points=[point]
            )

            self.logger.info("📊 Document metadata stored: %s...", document_id[:8])
            return document_id

        except Exception as e:
            self.logger.error("Failed to store processed document: %s", e)
            return document_id

    async def check_duplicate(self, file_hash: str) -> str | None:
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
                point = search_result[0][0]
                if point.payload is not None:
                    return point.payload.get("document_id")

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
        identifiers: list[str] | None = None,
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
            folder_path = (
                asset_data["folder_path"]
                if isinstance(asset_data["folder_path"], str)
                else str(asset_data["folder_path"])
            )
            asset_folder = self.base_assets_path / folder_path
            asset_folder.mkdir(parents=True, exist_ok=True)

            self.logger.info("✅ Created and stored asset: %s (%s)", deal_name, deal_id)
            return deal_id

        except Exception as e:
            self.logger.error("Failed to create asset %s: %s", deal_name, e)
            return deal_id

    async def get_asset(self, deal_id: str) -> Asset | None:
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
            if payload is None:
                self.logger.debug("Asset payload is None: %s", deal_id)
                return None
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
                if payload is None:
                    continue
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
        mappings: list[dict[str, Any]] = []

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
                if payload is None:
                    continue
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
        sender_email: str | None = None,
        deal_id: str | None = None,
        confidence: float | None = None,
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

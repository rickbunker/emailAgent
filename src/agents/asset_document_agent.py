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
from ..memory.contact import ContactMemory
from ..memory.episodic import EpisodicMemory
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


@dataclass
class ContextClue:
    """
    Represents a single context clue extracted from a source.

    Contains information about what was found, where it came from,
    and how confident we are in the interpretation.
    """

    source: str  # "sender", "subject", "body", "filename"
    clue_type: str  # "asset_identifier", "document_type", "organization", "domain"
    value: str  # The actual clue value
    confidence: float  # 0.0 to 1.0
    metadata: dict[str, Any] | None = None


@dataclass
class UnifiedContext:
    """
    Unified context object combining all context sources for document processing.

    Phase 3.2 implementation that aggregates context clues from sender,
    subject, body, and filename sources with confidence scoring and
    decision auditing capabilities.

    Attributes:
        sender_context: Context clues from email sender
        subject_context: Context clues from email subject line
        body_context: Context clues from email body text
        filename_context: Context clues from attachment filename
        combined_confidence: Overall confidence in context interpretation
        context_agreement: Measure of agreement between sources (0.0-1.0)
        context_conflicts: List of conflicting interpretations
        primary_asset_hints: Most likely asset identifiers across all sources
        primary_document_hints: Most likely document type hints across all sources
        reasoning_details: Detailed breakdown of context analysis
    """

    sender_context: list[ContextClue]
    subject_context: list[ContextClue]
    body_context: list[ContextClue]
    filename_context: list[ContextClue]
    combined_confidence: float
    context_agreement: float
    context_conflicts: list[dict[str, Any]]
    primary_asset_hints: list[str]
    primary_document_hints: list[str]
    reasoning_details: dict[str, Any]

    def get_all_clues(self) -> list[ContextClue]:
        """Get all context clues from all sources."""
        return (
            self.sender_context
            + self.subject_context
            + self.body_context
            + self.filename_context
        )

    def get_clues_by_type(self, clue_type: str) -> list[ContextClue]:
        """Get all context clues of a specific type."""
        return [clue for clue in self.get_all_clues() if clue.clue_type == clue_type]

    def get_clues_by_source(self, source: str) -> list[ContextClue]:
        """Get all context clues from a specific source."""
        all_clues = self.get_all_clues()
        return [clue for clue in all_clues if clue.source == source]


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

        # Initialize memory systems (Phase 2: All four memory types)
        self.semantic_memory = (
            SemanticMemory(qdrant_url=config.qdrant_url) if qdrant_client else None
        )
        self.procedural_memory = (
            ProceduralMemory(qdrant_client) if qdrant_client else None
        )
        self.episodic_memory = EpisodicMemory(qdrant_client) if qdrant_client else None
        self.contact_memory = ContactMemory(qdrant_client) if qdrant_client else None

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

            # Initialize episodic memory collections (Phase 2: Experience tracking)
            if self.episodic_memory:
                try:
                    await self.episodic_memory.initialize_collections()
                    self.logger.info("Episodic memory collections initialized")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize episodic memory: {e}")

            # Initialize contact memory collections (Phase 2: Contact management)
            if self.contact_memory:
                try:
                    await self.contact_memory.initialize_collections()
                    self.logger.info("Contact memory collections initialized")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize contact memory: {e}")

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
                payload["classification_metadata"] = (
                    processing_result.classification_metadata
                )

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

    @log_function()
    async def identify_asset_combined(
        self,
        email_subject: str,
        email_body: str,
        filename: str,
        sender_email: str,
        known_assets: list[Asset] | None = None,
    ) -> tuple[list[tuple[str, float]], dict[str, Any]]:
        """
        Enhanced asset identification using all four memory types.

        Phase 2.1: Combined Decision Logic implementation that integrates:
        - Procedural memory (stable matching algorithms)
        - Semantic memory (asset knowledge + human feedback)
        - Episodic memory (past experiences)
        - Contact memory (sender trust and patterns)

        Args:
            email_subject: Email subject line for context
            email_body: Email body content for analysis
            filename: Attachment filename for pattern matching
            sender_email: Sender email address for contact analysis
            known_assets: Optional list of assets to match against

        Returns:
            Tuple containing:
            - List of (asset_id, confidence_score) tuples sorted by confidence
            - Detailed reasoning dictionary with all memory type contributions

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If memory systems are not properly initialized
        """
        self.logger.info(
            "Starting combined asset identification using all memory types"
        )

        # Validate inputs
        if not email_subject and not email_body and not filename:
            raise ValueError(
                "At least one of email_subject, email_body, or filename must be provided"
            )

        if not sender_email:
            raise ValueError("sender_email is required for contact memory analysis")

        # Initialize reasoning capture with comprehensive structure
        reasoning_details = {
            "method_used": "combined_memory_system",
            "input_context": {
                "email_subject": email_subject,
                "email_body": (
                    email_body[:100] + "..." if len(email_body) > 100 else email_body
                ),
                "filename": filename,
                "sender_email": sender_email,
                "total_assets_available": len(known_assets) if known_assets else 0,
            },
            "memory_contributions": {
                "procedural": {"matches": [], "confidence": 0.0, "weight": 0.0},
                "semantic": {"matches": [], "confidence": 0.0, "weight": 0.0},
                "episodic": {"matches": [], "confidence": 0.0, "weight": 0.0},
                "contact": {"matches": [], "confidence": 0.0, "weight": 0.0},
            },
            "decision_flow": [],
            "final_scores": {},
            "primary_driver": "none",
            "confidence_level": "very_low",
        }

        try:
            # Get assets if not provided
            if known_assets is None:
                known_assets = await self.list_assets()
                reasoning_details["input_context"]["total_assets_available"] = len(
                    known_assets
                )

            if not known_assets:
                self.logger.warning("No assets available for identification")
                reasoning_details["decision_flow"].append(
                    "No assets available for matching"
                )
                return [], reasoning_details

            # Phase 2.1: Integrate all four memory types
            combined_text = f"{email_subject} {email_body} {filename}".lower()
            reasoning_details["decision_flow"].append(
                "Starting multi-memory asset identification"
            )

            # 1. Procedural Memory: Stable matching algorithms
            procedural_results = await self._get_procedural_asset_matches(
                combined_text, known_assets, reasoning_details
            )

            # 2. Semantic Memory: Asset knowledge + human feedback
            semantic_results = await self._get_semantic_asset_matches(
                combined_text, known_assets, reasoning_details
            )

            # 3. Episodic Memory: Past experiences
            episodic_results = await self._get_episodic_asset_matches(
                email_subject,
                email_body,
                filename,
                sender_email,
                known_assets,
                reasoning_details,
            )

            # 4. Contact Memory: Sender trust and patterns
            contact_results = await self._get_contact_asset_matches(
                sender_email, known_assets, reasoning_details
            )

            # Phase 2.1: Implement source combination logic
            final_matches = await self._combine_memory_sources(
                procedural_results,
                semantic_results,
                episodic_results,
                contact_results,
                known_assets,
                reasoning_details,
            )

            # Determine confidence level and primary driver
            self._analyze_decision_confidence(final_matches, reasoning_details)

            self.logger.info(
                f"Combined asset identification complete: {len(final_matches)} matches, "
                f"primary driver: {reasoning_details['primary_driver']}"
            )

            return final_matches, reasoning_details

        except Exception as e:
            self.logger.error(f"Combined asset identification failed: {e}")
            reasoning_details["decision_flow"].append(f"ERROR: {str(e)}")
            reasoning_details["primary_driver"] = "error"
            raise RuntimeError(f"Asset identification failed: {e}") from e

    @log_function()
    async def _get_procedural_asset_matches(
        self,
        combined_text: str,
        known_assets: list[Asset],
        reasoning_details: dict[str, Any],
    ) -> dict[str, float]:
        """
        Get asset matches using procedural memory stable algorithms.

        Uses business rules and stable matching patterns from procedural memory
        to identify potential asset matches based on content analysis.

        Args:
            combined_text: Combined email and filename text for analysis
            known_assets: List of available assets to match against
            reasoning_details: Reasoning dictionary to update with results

        Returns:
            Dictionary mapping asset_id to confidence score

        Raises:
            RuntimeError: If procedural memory operations fail
        """
        self.logger.debug("Getting procedural memory asset matches")

        procedural_matches: dict[str, float] = {}

        try:
            if not self.procedural_memory:
                self.logger.warning("Procedural memory not available")
                reasoning_details["memory_contributions"]["procedural"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return procedural_matches

            # Get asset matching rules from procedural memory
            asset_rules = await self.procedural_memory.get_asset_matching_rules()

            if not asset_rules or not asset_rules.get("rules"):
                self.logger.info("No asset matching rules found in procedural memory")
                reasoning_details["memory_contributions"]["procedural"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "no_rules",
                    }
                )
                return procedural_matches

            self.logger.info(
                f"Applying {len(asset_rules['rules'])} procedural asset matching rules"
            )

            # Apply procedural rules to each asset
            for asset in known_assets:
                max_confidence = 0.0
                matching_rules = []

                for rule in asset_rules["rules"]:
                    try:
                        # Match rule keywords against combined text
                        rule_confidence = 0.0
                        matched_keywords = []

                        keywords = rule.get("matching_keywords", [])
                        for keyword in keywords:
                            if keyword.lower() in combined_text:
                                rule_confidence += 0.2  # Base keyword match score
                                matched_keywords.append(keyword)

                        # Apply regex patterns if available
                        regex_patterns = rule.get("regex_patterns", [])
                        for pattern in regex_patterns:
                            try:
                                # # Standard library imports
                                import re

                                if re.search(pattern, combined_text, re.IGNORECASE):
                                    rule_confidence += (
                                        0.3  # Higher score for regex match
                                    )
                                    matched_keywords.append(f"regex:{pattern[:20]}...")
                            except re.error:
                                self.logger.warning(f"Invalid regex pattern: {pattern}")
                                continue

                        # Asset type boost
                        if (
                            hasattr(asset, "asset_type")
                            and rule.get("asset_type") == asset.asset_type.value
                        ):
                            rule_confidence *= 1.2  # 20% boost for matching asset type

                        # Record rule application
                        if rule_confidence > 0.1:  # Only record meaningful matches
                            matching_rules.append(
                                {
                                    "rule_id": rule.get("rule_id", "unknown"),
                                    "confidence": min(rule_confidence, 1.0),
                                    "matched_keywords": matched_keywords,
                                    "asset_type": rule.get("asset_type", "unknown"),
                                }
                            )
                            max_confidence = max(
                                max_confidence, min(rule_confidence, 1.0)
                            )

                    except Exception as e:
                        self.logger.debug(f"Error applying procedural rule: {e}")
                        continue

                # Store asset match if confidence threshold met
                if max_confidence >= config.low_confidence_threshold:
                    procedural_matches[asset.deal_id] = max_confidence
                    self.logger.debug(
                        f"Procedural match: {asset.deal_name} -> {max_confidence:.3f}"
                    )

            # Update reasoning details
            procedural_confidence = (
                sum(procedural_matches.values()) / len(procedural_matches)
                if procedural_matches
                else 0.0
            )

            reasoning_details["memory_contributions"]["procedural"].update(
                {
                    "matches": [
                        {
                            "asset_id": asset_id,
                            "confidence": confidence,
                            "asset_name": next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            ),
                        }
                        for asset_id, confidence in sorted(
                            procedural_matches.items(), key=lambda x: x[1], reverse=True
                        )[
                            :5
                        ]  # Top 5 matches
                    ],
                    "confidence": procedural_confidence,
                    "weight": (
                        config.procedural_memory_weight
                        if hasattr(config, "procedural_memory_weight")
                        else 0.25
                    ),
                    "rules_applied": len(asset_rules["rules"]),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Procedural memory found {len(procedural_matches)} asset matches "
                f"with average confidence {procedural_confidence:.3f}"
            )

            return procedural_matches

        except Exception as e:
            self.logger.error(f"Procedural memory asset matching failed: {e}")
            reasoning_details["memory_contributions"]["procedural"].update(
                {
                    "matches": [],
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Procedural memory matching failed: {e}") from e

    @log_function()
    async def _get_semantic_asset_matches(
        self,
        combined_text: str,
        known_assets: list[Asset],
        reasoning_details: dict[str, Any],
    ) -> dict[str, float]:
        """
        Get asset matches using semantic memory knowledge and feedback.

        Uses asset knowledge and human feedback stored in semantic memory
        to identify potential asset matches through similarity search.

        Args:
            combined_text: Combined email and filename text for analysis
            known_assets: List of available assets to match against
            reasoning_details: Reasoning dictionary to update with results

        Returns:
            Dictionary mapping asset_id to confidence score

        Raises:
            RuntimeError: If semantic memory operations fail
        """
        self.logger.debug("Getting semantic memory asset matches")

        semantic_matches: dict[str, float] = {}

        try:
            if not self.semantic_memory:
                self.logger.warning("Semantic memory not available")
                reasoning_details["memory_contributions"]["semantic"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return semantic_matches

            # Search for asset knowledge in semantic memory
            asset_knowledge_results = await self.semantic_memory.search_asset_knowledge(
                query_text=combined_text,
                limit=(
                    config.semantic_search_limit
                    if hasattr(config, "semantic_search_limit")
                    else 10
                ),
            )

            human_feedback_results = []
            # Get human feedback for assets
            for asset in known_assets:
                try:
                    feedback = await self.semantic_memory.get_asset_feedback(
                        asset_id=asset.deal_id,
                        context={"combined_text": combined_text[:200]},
                    )
                    if feedback and feedback.get("results"):
                        human_feedback_results.extend(feedback["results"])
                except Exception as e:
                    self.logger.debug(
                        f"No human feedback found for asset {asset.deal_id}: {e}"
                    )
                    continue

            # Combine results from both searches
            all_semantic_results = (
                asset_knowledge_results.get("results", []) + human_feedback_results
            )

            if not all_semantic_results:
                self.logger.info("No semantic memory matches found")
                reasoning_details["memory_contributions"]["semantic"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "no_matches",
                    }
                )
                return semantic_matches

            self.logger.info(
                f"Processing {len(all_semantic_results)} semantic memory results"
            )

            # Process semantic memory results
            asset_scores: dict[str, list[float]] = {}

            for result in all_semantic_results:
                try:
                    # Extract asset information from result
                    asset_id = result.get("metadata", {}).get("asset_id")
                    similarity_score = result.get("score", 0.0)
                    knowledge_type = result.get("metadata", {}).get(
                        "knowledge_type", "unknown"
                    )

                    if (
                        not asset_id
                        or similarity_score < config.semantic_similarity_threshold
                    ):
                        continue

                    # Apply knowledge type weighting
                    weighted_score = similarity_score

                    if knowledge_type == "human_feedback":
                        weighted_score *= 1.3  # Boost human feedback
                    elif knowledge_type == "asset_knowledge":
                        weighted_score *= 1.1  # Slight boost for asset knowledge
                    elif knowledge_type == "classification_feedback":
                        weighted_score *= 1.2  # Boost classification feedback

                    # Apply recency weighting if available
                    timestamp = result.get("metadata", {}).get("timestamp")
                    if timestamp:
                        # # Standard library imports
                        from datetime import UTC, datetime

                        try:
                            # Calculate recency boost (more recent = higher score)
                            if isinstance(timestamp, str):
                                result_time = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                            else:
                                result_time = datetime.fromtimestamp(timestamp, UTC)

                            days_old = (datetime.now(UTC) - result_time).days
                            recency_boost = max(
                                0.1, 1.0 - (days_old / 365.0)
                            )  # Decay over a year
                            weighted_score *= recency_boost
                        except (ValueError, TypeError) as e:
                            self.logger.debug(
                                f"Could not parse timestamp {timestamp}: {e}"
                            )

                    # Store score for this asset
                    if asset_id not in asset_scores:
                        asset_scores[asset_id] = []
                    asset_scores[asset_id].append(min(weighted_score, 1.0))

                except Exception as e:
                    self.logger.debug(f"Error processing semantic result: {e}")
                    continue

            # Calculate final scores for each asset (use max score)
            for asset_id, scores in asset_scores.items():
                if scores:
                    max_score = max(scores)
                    avg_score = sum(scores) / len(scores)
                    # Use weighted combination of max and average
                    final_score = (max_score * 0.7) + (avg_score * 0.3)

                    if final_score >= config.low_confidence_threshold:
                        semantic_matches[asset_id] = final_score

                        asset_name = next(
                            (
                                a.deal_name
                                for a in known_assets
                                if a.deal_id == asset_id
                            ),
                            "Unknown",
                        )
                        self.logger.debug(
                            f"Semantic match: {asset_name} -> {final_score:.3f} "
                            f"(from {len(scores)} signals)"
                        )

            # Update reasoning details
            semantic_confidence = (
                sum(semantic_matches.values()) / len(semantic_matches)
                if semantic_matches
                else 0.0
            )

            reasoning_details["memory_contributions"]["semantic"].update(
                {
                    "matches": [
                        {
                            "asset_id": asset_id,
                            "confidence": confidence,
                            "asset_name": next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            ),
                        }
                        for asset_id, confidence in sorted(
                            semantic_matches.items(), key=lambda x: x[1], reverse=True
                        )[
                            :5
                        ]  # Top 5 matches
                    ],
                    "confidence": semantic_confidence,
                    "weight": (
                        config.semantic_memory_weight
                        if hasattr(config, "semantic_memory_weight")
                        else 0.3
                    ),
                    "knowledge_signals": len(
                        asset_knowledge_results.get("results", [])
                    ),
                    "feedback_signals": len(human_feedback_results),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Semantic memory found {len(semantic_matches)} asset matches "
                f"with average confidence {semantic_confidence:.3f}"
            )

            return semantic_matches

        except Exception as e:
            self.logger.error(f"Semantic memory asset matching failed: {e}")
            reasoning_details["memory_contributions"]["semantic"].update(
                {
                    "matches": [],
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Semantic memory matching failed: {e}") from e

    @log_function()
    async def _get_episodic_asset_matches(
        self,
        email_subject: str,
        email_body: str,
        filename: str,
        sender_email: str,
        known_assets: list[Asset],
        reasoning_details: dict[str, Any],
    ) -> dict[str, float]:
        """
        Get asset matches using episodic memory past experiences.

        Uses past experiences and successful patterns from episodic memory
        to identify potential asset matches based on similar contexts.

        Args:
            email_subject: Email subject line for context matching
            email_body: Email body content for context matching
            filename: Attachment filename for pattern matching
            sender_email: Sender email for pattern matching
            known_assets: List of available assets to match against
            reasoning_details: Reasoning dictionary to update with results

        Returns:
            Dictionary mapping asset_id to confidence score

        Raises:
            RuntimeError: If episodic memory operations fail
        """
        self.logger.debug("Getting episodic memory asset matches")

        episodic_matches: dict[str, float] = {}

        try:
            if not self.episodic_memory:
                self.logger.warning("Episodic memory not available")
                reasoning_details["memory_contributions"]["episodic"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return episodic_matches

            # Search for similar past experiences
            search_queries = [
                f"asset identification {email_subject}",
                f"document processing {filename}",
                f"sender {sender_email}",
                f"email attachment {email_body[:100]}",
            ]

            all_episodic_results = []

            for query in search_queries:
                if not query.strip():
                    continue

                try:
                    results = await self.episodic_memory.search(
                        query_text=query,
                        limit=(
                            config.episodic_search_limit
                            if hasattr(config, "episodic_search_limit")
                            else 5
                        ),
                        memory_type="decision",  # Focus on decision memories
                    )

                    if results and results.get("results"):
                        all_episodic_results.extend(results["results"])

                except Exception as e:
                    self.logger.debug(
                        f"Episodic search failed for query '{query}': {e}"
                    )
                    continue

            if not all_episodic_results:
                self.logger.info("No episodic memory matches found")
                reasoning_details["memory_contributions"]["episodic"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "no_experiences",
                    }
                )
                return episodic_matches

            self.logger.info(
                f"Processing {len(all_episodic_results)} episodic memory results"
            )

            # Process episodic memory results
            asset_experience_scores: dict[str, list[float]] = {}

            for result in all_episodic_results:
                try:
                    # Extract experience information
                    metadata = result.get("metadata", {})
                    similarity_score = result.get("score", 0.0)

                    # Look for asset ID in the experience
                    asset_id = metadata.get("asset_id") or metadata.get(
                        "result_asset_id"
                    )
                    decision_outcome = metadata.get("outcome", "unknown")
                    decision_confidence = metadata.get("confidence", 0.0)

                    if (
                        not asset_id
                        or similarity_score < config.episodic_similarity_threshold
                    ):
                        continue

                    # Weight by decision outcome success
                    outcome_weight = 1.0
                    if decision_outcome == "success":
                        outcome_weight = 1.2
                    elif decision_outcome == "partial_success":
                        outcome_weight = 1.0
                    elif decision_outcome == "failure":
                        outcome_weight = 0.5

                    # Weight by original decision confidence
                    confidence_weight = max(0.3, min(1.0, decision_confidence))

                    # Apply temporal decay (recent experiences more valuable)
                    timestamp = metadata.get("timestamp")
                    temporal_weight = 1.0

                    if timestamp:
                        # # Standard library imports
                        from datetime import UTC, datetime

                        try:
                            if isinstance(timestamp, str):
                                experience_time = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                            else:
                                experience_time = datetime.fromtimestamp(timestamp, UTC)

                            days_old = (datetime.now(UTC) - experience_time).days
                            # More aggressive decay for episodic memories (decay over 6 months)
                            temporal_weight = max(0.2, 1.0 - (days_old / 180.0))
                        except (ValueError, TypeError) as e:
                            self.logger.debug(
                                f"Could not parse timestamp {timestamp}: {e}"
                            )

                    # Calculate final episodic score
                    episodic_score = (
                        similarity_score
                        * outcome_weight
                        * confidence_weight
                        * temporal_weight
                    )

                    # Store score for this asset
                    if asset_id not in asset_experience_scores:
                        asset_experience_scores[asset_id] = []
                    asset_experience_scores[asset_id].append(min(episodic_score, 1.0))

                except Exception as e:
                    self.logger.debug(f"Error processing episodic result: {e}")
                    continue

            # Calculate final scores for each asset
            for asset_id, scores in asset_experience_scores.items():
                if scores and asset_id in [a.deal_id for a in known_assets]:
                    # Use weighted average of experiences, giving more weight to higher scores
                    sorted_scores = sorted(scores, reverse=True)
                    if len(sorted_scores) >= 3:
                        # Weight: 50% best, 30% second best, 20% third best
                        final_score = (
                            sorted_scores[0] * 0.5
                            + sorted_scores[1] * 0.3
                            + sorted_scores[2] * 0.2
                        )
                    elif len(sorted_scores) == 2:
                        final_score = sorted_scores[0] * 0.7 + sorted_scores[1] * 0.3
                    else:
                        final_score = sorted_scores[0]

                    if final_score >= config.low_confidence_threshold:
                        episodic_matches[asset_id] = final_score

                        asset_name = next(
                            (
                                a.deal_name
                                for a in known_assets
                                if a.deal_id == asset_id
                            ),
                            "Unknown",
                        )
                        self.logger.debug(
                            f"Episodic match: {asset_name} -> {final_score:.3f} "
                            f"(from {len(scores)} experiences)"
                        )

            # Update reasoning details
            episodic_confidence = (
                sum(episodic_matches.values()) / len(episodic_matches)
                if episodic_matches
                else 0.0
            )

            reasoning_details["memory_contributions"]["episodic"].update(
                {
                    "matches": [
                        {
                            "asset_id": asset_id,
                            "confidence": confidence,
                            "asset_name": next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            ),
                        }
                        for asset_id, confidence in sorted(
                            episodic_matches.items(), key=lambda x: x[1], reverse=True
                        )[
                            :5
                        ]  # Top 5 matches
                    ],
                    "confidence": episodic_confidence,
                    "weight": (
                        config.episodic_memory_weight
                        if hasattr(config, "episodic_memory_weight")
                        else 0.2
                    ),
                    "experiences_found": len(all_episodic_results),
                    "relevant_experiences": sum(
                        len(scores) for scores in asset_experience_scores.values()
                    ),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Episodic memory found {len(episodic_matches)} asset matches "
                f"with average confidence {episodic_confidence:.3f}"
            )

            return episodic_matches

        except Exception as e:
            self.logger.error(f"Episodic memory asset matching failed: {e}")
            reasoning_details["memory_contributions"]["episodic"].update(
                {
                    "matches": [],
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Episodic memory matching failed: {e}") from e

    @log_function()
    async def _get_contact_asset_matches(
        self,
        sender_email: str,
        known_assets: list[Asset],
        reasoning_details: dict[str, Any],
    ) -> dict[str, float]:
        """
        Get asset matches using contact memory sender trust and patterns.

        Uses sender trust level and historical patterns from contact memory
        to identify potential asset matches based on sender relationships.

        Args:
            sender_email: Sender email address for contact analysis
            known_assets: List of available assets to match against
            reasoning_details: Reasoning dictionary to update with results

        Returns:
            Dictionary mapping asset_id to confidence score

        Raises:
            RuntimeError: If contact memory operations fail
        """
        self.logger.debug("Getting contact memory asset matches")

        contact_matches: dict[str, float] = {}

        try:
            if not self.contact_memory:
                self.logger.warning("Contact memory not available")
                reasoning_details["memory_contributions"]["contact"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return contact_matches

            # Find contact information for sender
            sender_contact = await self.contact_memory.find_contact_by_email(
                sender_email
            )

            if not sender_contact:
                self.logger.info(f"No contact information found for {sender_email}")
                reasoning_details["memory_contributions"]["contact"].update(
                    {
                        "matches": [],
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unknown_sender",
                    }
                )
                return contact_matches

            self.logger.info(f"Found contact information for {sender_email}")

            # Extract sender organization and trust level
            sender_org = getattr(sender_contact, "organization", "") or ""
            sender_trust = getattr(sender_contact, "trust_level", "unknown")
            sender_tags = getattr(sender_contact, "tags", []) or []

            # Base trust score
            trust_scores = {
                "high": 0.8,
                "medium": 0.6,
                "low": 0.3,
                "verified": 0.9,
                "trusted": 0.8,
                "unknown": 0.1,
            }

            base_trust_score = trust_scores.get(sender_trust.lower(), 0.1)

            # Search for historical interactions with this sender
            interaction_results = await self.contact_memory.search_contacts(
                query=f"email interactions {sender_email}",
                limit=(
                    config.contact_search_limit
                    if hasattr(config, "contact_search_limit")
                    else 10
                ),
            )

            # Analyze asset patterns for this sender/organization
            sender_asset_patterns: dict[str, list[float]] = {}

            # Check each asset for sender/organization matches
            for asset in known_assets:
                asset_confidence = 0.0
                matching_factors = []

                # Direct email mapping check (if asset has sender mappings)
                if (
                    hasattr(asset, "sender_emails")
                    and asset.sender_emails
                    and sender_email.lower()
                    in [email.lower() for email in asset.sender_emails]
                ):
                    asset_confidence += 0.7
                    matching_factors.append("direct_email_mapping")

                # Organization matching
                if (
                    sender_org
                    and hasattr(asset, "organization")
                    and asset.organization
                    and sender_org.lower() in asset.organization.lower()
                ):
                    asset_confidence += 0.5
                    matching_factors.append("organization_match")

                # Tags matching (if asset has related tags)
                if sender_tags and hasattr(asset, "tags") and asset.tags:
                    common_tags = {tag.lower() for tag in sender_tags} & {
                        tag.lower() for tag in asset.tags
                    }
                    if common_tags:
                        tag_boost = min(0.3, len(common_tags) * 0.1)
                        asset_confidence += tag_boost
                        matching_factors.append(f"tag_match:{','.join(common_tags)}")

                # Apply trust level weighting
                weighted_confidence = asset_confidence * base_trust_score

                # Boost based on sender interaction frequency
                if interaction_results and interaction_results.get("results"):
                    interaction_count = len(interaction_results["results"])
                    frequency_boost = min(0.2, interaction_count * 0.02)
                    weighted_confidence += frequency_boost
                    matching_factors.append(
                        f"interaction_frequency:{interaction_count}"
                    )

                # Store if above threshold
                if weighted_confidence >= config.low_confidence_threshold:
                    if asset.deal_id not in sender_asset_patterns:
                        sender_asset_patterns[asset.deal_id] = []
                    sender_asset_patterns[asset.deal_id].append(weighted_confidence)

                    self.logger.debug(
                        f"Contact match: {asset.deal_name} -> {weighted_confidence:.3f} "
                        f"(factors: {', '.join(matching_factors)})"
                    )

            # Calculate final contact scores
            for asset_id, scores in sender_asset_patterns.items():
                if scores:
                    # Use maximum score for contact memory (direct mappings are strong)
                    final_score = max(scores)
                    contact_matches[asset_id] = final_score

            # Update reasoning details
            contact_confidence = (
                sum(contact_matches.values()) / len(contact_matches)
                if contact_matches
                else 0.0
            )

            reasoning_details["memory_contributions"]["contact"].update(
                {
                    "matches": [
                        {
                            "asset_id": asset_id,
                            "confidence": confidence,
                            "asset_name": next(
                                (
                                    a.deal_name
                                    for a in known_assets
                                    if a.deal_id == asset_id
                                ),
                                "Unknown",
                            ),
                        }
                        for asset_id, confidence in sorted(
                            contact_matches.items(), key=lambda x: x[1], reverse=True
                        )[
                            :5
                        ]  # Top 5 matches
                    ],
                    "confidence": contact_confidence,
                    "weight": (
                        config.contact_memory_weight
                        if hasattr(config, "contact_memory_weight")
                        else 0.25
                    ),
                    "sender_trust": sender_trust,
                    "sender_organization": sender_org,
                    "interaction_count": (
                        len(interaction_results.get("results", []))
                        if interaction_results
                        else 0
                    ),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Contact memory found {len(contact_matches)} asset matches "
                f"with average confidence {contact_confidence:.3f} "
                f"(sender trust: {sender_trust})"
            )

            return contact_matches

        except Exception as e:
            self.logger.error(f"Contact memory asset matching failed: {e}")
            reasoning_details["memory_contributions"]["contact"].update(
                {
                    "matches": [],
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Contact memory matching failed: {e}") from e

    @log_function()
    async def _combine_memory_sources(
        self,
        procedural_results: dict[str, float],
        semantic_results: dict[str, float],
        episodic_results: dict[str, float],
        contact_results: dict[str, float],
        known_assets: list[Asset],
        reasoning_details: dict[str, Any],
    ) -> list[tuple[str, float]]:
        """
        Combine results from all memory sources with weighted scoring.

        Phase 2.1: Implements source combination logic that weights different
        memory sources appropriately and handles conflicting signals.

        Args:
            procedural_results: Asset matches from procedural memory
            semantic_results: Asset matches from semantic memory
            episodic_results: Asset matches from episodic memory
            contact_results: Asset matches from contact memory
            known_assets: List of available assets
            reasoning_details: Reasoning dictionary to update

        Returns:
            List of (asset_id, final_confidence) tuples sorted by confidence

        Raises:
            RuntimeError: If source combination fails
        """
        self.logger.info("Combining memory source results with weighted scoring")

        try:
            # Get all unique asset IDs from all sources
            all_asset_ids = set()
            all_asset_ids.update(procedural_results.keys())
            all_asset_ids.update(semantic_results.keys())
            all_asset_ids.update(episodic_results.keys())
            all_asset_ids.update(contact_results.keys())

            if not all_asset_ids:
                self.logger.warning("No asset matches found in any memory source")
                reasoning_details["decision_flow"].append(
                    "No matches found in any memory source"
                )
                reasoning_details["final_scores"] = {}
                return []

            # Extract memory weights from reasoning details
            weights = {
                "procedural": reasoning_details["memory_contributions"]["procedural"][
                    "weight"
                ],
                "semantic": reasoning_details["memory_contributions"]["semantic"][
                    "weight"
                ],
                "episodic": reasoning_details["memory_contributions"]["episodic"][
                    "weight"
                ],
                "contact": reasoning_details["memory_contributions"]["contact"][
                    "weight"
                ],
            }

            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}
            else:
                # Fallback to equal weights
                weights = dict.fromkeys(weights, 0.25)

            self.logger.info(f"Using memory weights: {weights}")
            reasoning_details["decision_flow"].append(
                f"Applied memory weights: {weights}"
            )

            # Calculate combined scores
            combined_scores: dict[str, float] = {}
            asset_details: dict[str, dict] = {}

            for asset_id in all_asset_ids:
                # Get scores from each memory source
                scores = {
                    "procedural": procedural_results.get(asset_id, 0.0),
                    "semantic": semantic_results.get(asset_id, 0.0),
                    "episodic": episodic_results.get(asset_id, 0.0),
                    "contact": contact_results.get(asset_id, 0.0),
                }

                # Calculate weighted average
                weighted_score = sum(
                    scores[source] * weights[source] for source in scores
                )

                # Apply source agreement boost
                active_sources = sum(1 for score in scores.values() if score > 0)
                if active_sources >= 2:
                    # Multiple sources agree - boost confidence
                    agreement_boost = min(0.2, (active_sources - 1) * 0.1)
                    weighted_score += agreement_boost

                # Apply conflict penalty for highly disagreeing sources
                if active_sources >= 2:
                    score_variance = (
                        sum(
                            (scores[source] - weighted_score) ** 2
                            for source in scores
                            if scores[source] > 0
                        )
                        / active_sources
                    )

                    if score_variance > 0.2:  # High disagreement
                        conflict_penalty = min(0.15, score_variance * 0.3)
                        weighted_score -= conflict_penalty

                # Ensure score is within bounds
                final_score = max(0.0, min(1.0, weighted_score))

                # Store if above minimum threshold
                if final_score >= config.minimum_combined_confidence:
                    combined_scores[asset_id] = final_score

                    asset_details[asset_id] = {
                        "scores": scores,
                        "weighted_score": weighted_score,
                        "active_sources": active_sources,
                        "final_score": final_score,
                        "asset_name": next(
                            (
                                a.deal_name
                                for a in known_assets
                                if a.deal_id == asset_id
                            ),
                            "Unknown",
                        ),
                    }

            # Sort by final score (descending)
            sorted_matches = sorted(
                combined_scores.items(), key=lambda x: x[1], reverse=True
            )

            # Update reasoning details with final results
            reasoning_details["final_scores"] = {
                asset_id: asset_details[asset_id] for asset_id, _ in sorted_matches
            }

            # Determine primary driver (memory source with highest total contribution)
            source_contributions = {
                "procedural": sum(procedural_results.values()),
                "semantic": sum(semantic_results.values()),
                "episodic": sum(episodic_results.values()),
                "contact": sum(contact_results.values()),
            }

            primary_driver = max(source_contributions.items(), key=lambda x: x[1])[0]
            reasoning_details["primary_driver"] = primary_driver

            reasoning_details["decision_flow"].append(
                f"Combined {len(all_asset_ids)} candidate assets, "
                f"produced {len(sorted_matches)} final matches, "
                f"primary driver: {primary_driver}"
            )

            self.logger.info(
                f"Source combination complete: {len(sorted_matches)} final matches, "
                f"primary driver: {primary_driver}, "
                f"top match: {sorted_matches[0] if sorted_matches else 'none'}"
            )

            return sorted_matches

        except Exception as e:
            self.logger.error(f"Memory source combination failed: {e}")
            reasoning_details["decision_flow"].append(
                f"ERROR in source combination: {str(e)}"
            )
            raise RuntimeError(f"Source combination failed: {e}") from e

    def _analyze_decision_confidence(
        self,
        final_matches: list[tuple[str, float]],
        reasoning_details: dict[str, Any],
    ) -> None:
        """
        Analyze overall decision confidence and update reasoning.

        Determines confidence level based on match quality and agreement.

        Args:
            final_matches: List of (asset_id, confidence) tuples
            reasoning_details: Reasoning dictionary to update
        """
        if not final_matches:
            reasoning_details["confidence_level"] = "very_low"
            reasoning_details["decision_flow"].append(
                "No matches found - very low confidence"
            )
            return

        top_score = final_matches[0][1]
        active_memory_sources = sum(
            1
            for contrib in reasoning_details["memory_contributions"].values()
            if contrib["confidence"] > 0
        )

        # Determine confidence level
        if top_score >= 0.8 and active_memory_sources >= 3:
            confidence_level = "very_high"
        elif top_score >= 0.7 and active_memory_sources >= 2:
            confidence_level = "high"
        elif top_score >= 0.5:
            confidence_level = "medium"
        elif top_score >= 0.3:
            confidence_level = "low"
        else:
            confidence_level = "very_low"

        reasoning_details["confidence_level"] = confidence_level
        reasoning_details["decision_flow"].append(
            f"Decision confidence: {confidence_level} "
            f"(top score: {top_score:.3f}, active sources: {active_memory_sources})"
        )

    @log_function()
    async def classify_document_combined(
        self,
        filename: str,
        subject: str,
        body: str,
        asset_type: str,
        asset_id: str | None = None,
    ) -> tuple[str, float, dict[str, Any]]:
        """
        Enhanced document classification using all four memory types.

        Phase 2.2: Combined Decision Logic implementation that integrates:
        - Procedural memory (stable business rules with asset type filtering)
        - Semantic memory (human feedback + allowed categories for asset type)
        - Episodic memory (past classification experiences)
        - Contact memory (sender patterns and document types)

        Args:
            filename: Document filename for classification
            subject: Email subject line for context
            body: Email body content for analysis
            asset_type: Asset type for constraint filtering
            asset_id: Optional asset ID for enhanced context

        Returns:
            Tuple containing:
            - Predicted document category (string)
            - Classification confidence score (0.0-1.0)
            - Detailed reasoning dictionary with all memory type contributions

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If memory systems are not properly initialized
        """
        self.logger.info(
            "Starting combined document classification using all memory types"
        )

        # Validate inputs
        if not filename and not subject:
            raise ValueError("At least one of filename or subject must be provided")

        if not asset_type:
            raise ValueError("asset_type is required for constraint filtering")

        # Initialize reasoning capture with comprehensive structure
        reasoning_details = {
            "method_used": "combined_memory_classification",
            "input_context": {
                "filename": filename,
                "subject": subject,
                "body": body[:100] + "..." if len(body) > 100 else body,
                "asset_type": asset_type,
                "asset_id": asset_id,
                "document_length": len(body) if body else 0,
            },
            "memory_contributions": {
                "procedural": {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "rules_applied": [],
                },
                "semantic": {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "hints_found": [],
                },
                "episodic": {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "experiences": [],
                },
                "contact": {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "patterns": [],
                },
            },
            "asset_type_constraints": {
                "allowed_categories": [],
                "constraint_applied": False,
                "filtered_out": [],
            },
            "decision_flow": [],
            "category_scores": {},
            "final_category": "",
            "final_confidence": 0.0,
            "primary_driver": "none",
            "confidence_level": "very_low",
        }

        try:
            # Phase 2.2: Get allowed categories for asset type from semantic memory
            allowed_categories = await self._get_asset_type_categories(
                asset_type, reasoning_details
            )

            combined_text = f"{filename} {subject} {body}".lower()
            reasoning_details["decision_flow"].append(
                "Starting multi-memory document classification"
            )

            # 1. Procedural Memory: Apply business rules with asset type filtering
            procedural_result = await self._get_procedural_classification(
                combined_text, asset_type, allowed_categories, reasoning_details
            )

            # 2. Semantic Memory: Get human feedback and hints for this asset type
            semantic_result = await self._get_semantic_classification(
                combined_text,
                asset_type,
                asset_id,
                allowed_categories,
                reasoning_details,
            )

            # 3. Episodic Memory: Find similar classification experiences
            episodic_result = await self._get_episodic_classification(
                filename,
                subject,
                body,
                asset_type,
                allowed_categories,
                reasoning_details,
            )

            # 4. Contact Memory: Apply sender document patterns (if available)
            contact_result = await self._get_contact_classification(
                subject, body, asset_type, allowed_categories, reasoning_details
            )

            # Phase 2.2: Combine results with asset type constraint filtering
            (
                final_category,
                final_confidence,
            ) = await self._combine_classification_results(
                procedural_result,
                semantic_result,
                episodic_result,
                contact_result,
                allowed_categories,
                reasoning_details,
            )

            # Determine confidence level and primary driver
            self._analyze_classification_confidence(
                final_category, final_confidence, reasoning_details
            )

            self.logger.info(
                f"Combined classification complete: {final_category} "
                f"(confidence: {final_confidence:.3f}, "
                f"primary driver: {reasoning_details['primary_driver']})"
            )

            return final_category, final_confidence, reasoning_details

        except Exception as e:
            self.logger.error(f"Combined document classification failed: {e}")
            reasoning_details["decision_flow"].append(f"ERROR: {str(e)}")
            reasoning_details["primary_driver"] = "error"
            raise RuntimeError(f"Document classification failed: {e}") from e

    @log_function()
    async def _get_asset_type_categories(
        self,
        asset_type: str,
        reasoning_details: dict[str, Any],
    ) -> list[str]:
        """
        Get allowed document categories for the specified asset type.

        Enhanced Phase 3.1 implementation that uses multiple semantic memory queries,
        intelligent fallback logic, and better constraint validation to determine
        proper document categories for asset types.

        Args:
            asset_type: Asset type to get categories for
            reasoning_details: Reasoning dictionary to update with enhanced details

        Returns:
            List of allowed category strings for this asset type

        Raises:
            RuntimeError: If semantic memory operations fail
        """
        self.logger.debug(f"🎯 Enhanced asset type category lookup: {asset_type}")

        try:
            if not self.semantic_memory:
                self.logger.warning(
                    "Semantic memory not available for category constraints"
                )
                reasoning_details["asset_type_constraints"].update(
                    {
                        "allowed_categories": [],
                        "constraint_applied": False,
                        "status": "no_semantic_memory",
                        "fallback_used": "none",
                        "sources": [],
                    }
                )
                return []

            # Enhanced multi-query approach for better category discovery
            search_queries = [
                f"asset type {asset_type} document categories allowed types",
                f"{asset_type} investment documents classification categories",
                f"document types {asset_type} portfolio management filing",
                f"categories valid {asset_type} asset document classification",
            ]

            all_categories = set()
            source_details = []

            # Query 1: Direct asset configuration search
            for query in search_queries:
                try:
                    category_results = await self.semantic_memory.search(
                        query=query,
                        limit=config.semantic_search_limit,
                        filter_conditions={
                            "metadata.knowledge_type": "asset_configuration"
                        },
                    )

                    if category_results:
                        for result in category_results:
                            metadata = (
                                result.metadata if hasattr(result, "metadata") else {}
                            )
                            result_asset_type = metadata.get("asset_type", "").lower()

                            # Asset type match with confidence weighting
                            if result_asset_type == asset_type.lower():
                                categories = metadata.get("allowed_categories", [])
                                confidence_boost = 1.0
                            elif (
                                result_asset_type
                                and asset_type.lower() in result_asset_type
                            ):
                                categories = metadata.get("allowed_categories", [])
                                confidence_boost = 0.8
                            else:
                                categories = metadata.get("document_categories", [])
                                confidence_boost = 0.6

                            if isinstance(categories, list):
                                weighted_categories = [
                                    (cat, confidence_boost) for cat in categories
                                ]
                                all_categories.update(
                                    cat for cat, _ in weighted_categories
                                )
                                source_details.append(
                                    {
                                        "query": query[:50] + "...",
                                        "categories": categories,
                                        "asset_type_match": result_asset_type
                                        == asset_type.lower(),
                                        "confidence_boost": confidence_boost,
                                    }
                                )
                            elif isinstance(categories, str):
                                all_categories.add(categories)
                                source_details.append(
                                    {
                                        "query": query[:50] + "...",
                                        "categories": [categories],
                                        "asset_type_match": result_asset_type
                                        == asset_type.lower(),
                                        "confidence_boost": confidence_boost,
                                    }
                                )

                except Exception as e:
                    self.logger.debug(f"Query failed for '{query[:30]}...': {e}")
                    continue

            # Query 2: Look for asset-specific knowledge with categories
            try:
                asset_knowledge = await self.semantic_memory.search(
                    query=f"asset knowledge {asset_type} document types classification",
                    limit=config.semantic_search_limit * 2,
                    filter_conditions={"metadata.asset_type": asset_type},
                )

                if asset_knowledge:
                    for result in asset_knowledge:
                        metadata = (
                            result.metadata if hasattr(result, "metadata") else {}
                        )
                        doc_categories = metadata.get("document_categories", [])
                        business_context = metadata.get("business_context", {})

                        if doc_categories:
                            if isinstance(doc_categories, list):
                                all_categories.update(doc_categories)
                            else:
                                all_categories.add(doc_categories)

                        # Extract categories from business context
                        if isinstance(business_context, dict):
                            context_categories = business_context.get(
                                "typical_documents", []
                            )
                            if context_categories:
                                all_categories.update(context_categories)

                        source_details.append(
                            {
                                "source": "asset_knowledge",
                                "categories": doc_categories,
                                "confidence": "high",
                            }
                        )

            except Exception as e:
                self.logger.debug(f"Asset knowledge query failed: {e}")

            # Convert to sorted list and apply intelligent fallback
            allowed_categories = sorted(all_categories)

            # Enhanced fallback logic based on asset type
            if not allowed_categories:
                self.logger.info(
                    f"No categories found in semantic memory for {asset_type}, using intelligent fallback"
                )

                # Asset type-specific fallback categories
                asset_type_categories = {
                    "commercial_real_estate": [
                        "rent_roll",
                        "financial_statements",
                        "property_photos",
                        "appraisal",
                        "lease_documents",
                        "property_management",
                        "legal_documents",
                        "insurance",
                        "correspondence",
                    ],
                    "private_credit": [
                        "loan_documents",
                        "borrower_financials",
                        "covenant_compliance",
                        "credit_memo",
                        "loan_monitoring",
                        "legal_documents",
                        "tax_documents",
                        "correspondence",
                    ],
                    "private_equity": [
                        "portfolio_reports",
                        "investor_updates",
                        "board_materials",
                        "deal_documents",
                        "valuation_reports",
                        "legal_documents",
                        "tax_documents",
                        "correspondence",
                    ],
                    "infrastructure": [
                        "engineering_reports",
                        "construction_updates",
                        "regulatory_documents",
                        "operations_reports",
                        "legal_documents",
                        "insurance",
                        "correspondence",
                    ],
                }

                allowed_categories = asset_type_categories.get(
                    asset_type.lower(),
                    [
                        "financial_statements",
                        "legal_documents",
                        "tax_documents",
                        "insurance",
                        "correspondence",
                        "unknown",
                    ],
                )

                fallback_used = "asset_type_specific"
                constraint_strength = (
                    config.category_constraint_strength * 0.8
                )  # Reduce strength for fallback
            else:
                fallback_used = "none"
                constraint_strength = config.category_constraint_strength

            # Apply constraint strength weighting
            reasoning_details["asset_type_constraints"].update(
                {
                    "allowed_categories": allowed_categories,
                    "constraint_applied": True,
                    "constraint_strength": constraint_strength,
                    "status": "success",
                    "fallback_used": fallback_used,
                    "sources": source_details[:3],  # Top 3 sources for reasoning
                    "total_sources": len(source_details),
                    "semantic_matches": len(
                        [s for s in source_details if s.get("confidence") == "high"]
                    ),
                }
            )

            self.logger.info(
                f"📋 Asset type categories for {asset_type}: {len(allowed_categories)} categories "
                f"(sources: {len(source_details)}, fallback: {fallback_used})"
            )
            self.logger.debug(
                f"Categories: {', '.join(allowed_categories[:5])}{'...' if len(allowed_categories) > 5 else ''}"
            )

            return allowed_categories

        except Exception as e:
            self.logger.error(f"Failed to get enhanced asset type categories: {e}")
            reasoning_details["asset_type_constraints"].update(
                {
                    "allowed_categories": [],
                    "constraint_applied": False,
                    "constraint_strength": 0.0,
                    "status": f"error: {str(e)}",
                    "fallback_used": "error",
                    "sources": [],
                }
            )
            # Return empty list to disable constraint filtering on error
            return []

    @log_function()
    async def _get_procedural_classification(
        self,
        combined_text: str,
        asset_type: str,
        allowed_categories: list[str],
        reasoning_details: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Get document classification using procedural memory business rules.

        Applies stable business rules with asset type filtering to boost
        matching patterns and reduce non-matching ones.

        Args:
            combined_text: Combined document text for analysis
            asset_type: Asset type for rule filtering
            allowed_categories: List of allowed categories for constraint filtering
            reasoning_details: Reasoning dictionary to update

        Returns:
            Tuple of (predicted_category, confidence_score)

        Raises:
            RuntimeError: If procedural memory operations fail
        """
        self.logger.debug("Getting procedural memory classification")

        try:
            if not self.procedural_memory:
                self.logger.warning("Procedural memory not available")
                reasoning_details["memory_contributions"]["procedural"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return "", 0.0

            # Get classification rules for this asset type
            classification_rules = (
                await self.procedural_memory.get_classification_rules(
                    asset_type=asset_type
                )
            )

            if not classification_rules or not classification_rules.get("rules"):
                self.logger.info("No classification rules found in procedural memory")
                reasoning_details["memory_contributions"]["procedural"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": config.procedural_memory_weight,
                        "rules_applied": [],
                        "status": "no_rules",
                    }
                )
                return "", 0.0

            self.logger.info(
                f"Applying {len(classification_rules['rules'])} procedural classification rules"
            )

            # Score each category based on rule matches
            category_scores: dict[str, float] = {}
            applied_rules = []

            for rule in classification_rules["rules"]:
                try:
                    rule_category = rule.get("category", "").lower()
                    rule_confidence = 0.0
                    matched_patterns = []

                    # Enhanced constraint filtering (Phase 3.1)
                    constraint_applied = False
                    if allowed_categories:
                        category_allowed = rule_category in [
                            c.lower() for c in allowed_categories
                        ]
                        if not category_allowed:
                            # Apply constraint strength to determine if rule should be completely filtered
                            constraint_strength = reasoning_details[
                                "asset_type_constraints"
                            ].get(
                                "constraint_strength",
                                config.category_constraint_strength,
                            )
                            if (
                                constraint_strength
                                >= config.context_confidence_threshold
                            ):
                                # Strong constraint - skip this rule entirely
                                continue
                            else:
                                # Weak constraint - apply penalty but don't skip
                                rule_confidence *= 1.0 - constraint_strength
                                matched_patterns.append(
                                    f"constraint_penalty(x{1.0 - constraint_strength:.2f})"
                                )
                                constraint_applied = True
                        else:
                            # Category is allowed - potential boost for strong constraints
                            constraint_strength = reasoning_details[
                                "asset_type_constraints"
                            ].get(
                                "constraint_strength",
                                config.category_constraint_strength,
                            )
                            if (
                                constraint_strength
                                >= config.context_confidence_threshold
                            ):
                                rule_confidence *= 1.0 + (
                                    constraint_strength * 0.1
                                )  # Small boost for allowed categories
                                matched_patterns.append(
                                    f"constraint_boost(x{1.0 + (constraint_strength * 0.1):.2f})"
                                )
                                constraint_applied = True

                    # Apply keyword patterns
                    keywords = rule.get("keywords", [])
                    for keyword in keywords:
                        if keyword.lower() in combined_text:
                            rule_confidence += 0.3
                            matched_patterns.append(f"keyword:{keyword}")

                    # Apply regex patterns
                    regex_patterns = rule.get("regex_patterns", [])
                    for pattern in regex_patterns:
                        try:
                            # # Standard library imports
                            import re

                            if re.search(pattern, combined_text, re.IGNORECASE):
                                rule_confidence += 0.4
                                matched_patterns.append(f"regex:{pattern[:20]}...")
                        except re.error:
                            self.logger.warning(f"Invalid regex pattern: {pattern}")
                            continue

                    # Enhanced asset type context filtering (Phase 3.1)
                    rule_asset_type = rule.get("asset_type", "").lower()
                    asset_context_applied = False

                    if rule_asset_type == asset_type.lower():
                        # Use config-driven boost factor for matching asset types
                        rule_confidence *= config.asset_type_boost_factor
                        matched_patterns.append(
                            f"asset_type_match(x{config.asset_type_boost_factor})"
                        )
                        asset_context_applied = True
                    elif rule_asset_type and rule_asset_type != asset_type.lower():
                        # Use config-driven penalty factor for non-matching asset types
                        rule_confidence *= config.asset_type_penalty_factor
                        matched_patterns.append(
                            f"asset_type_penalty(x{config.asset_type_penalty_factor})"
                        )
                        asset_context_applied = True
                    elif not rule_asset_type:
                        # Apply general asset context weight for generic rules
                        rule_confidence *= 1.0 + config.asset_context_weight
                        matched_patterns.append(
                            f"general_context(x{1.0 + config.asset_context_weight})"
                        )
                        asset_context_applied = True

                    # Record significant rule applications
                    if rule_confidence > config.low_confidence_threshold:
                        if rule_category not in category_scores:
                            category_scores[rule_category] = 0.0
                        category_scores[rule_category] += rule_confidence

                        applied_rules.append(
                            {
                                "rule_id": rule.get("rule_id", "unknown"),
                                "category": rule_category,
                                "confidence": min(rule_confidence, 1.0),
                                "patterns": matched_patterns,
                                "asset_type_match": rule_asset_type
                                == asset_type.lower(),
                                "asset_context_applied": asset_context_applied,
                                "constraint_applied": constraint_applied,
                                "rule_asset_type": rule_asset_type or "generic",
                                "context_enhancements": {
                                    "asset_type_filtering": asset_context_applied,
                                    "constraint_filtering": constraint_applied,
                                    "pattern_count": len(matched_patterns),
                                },
                            }
                        )

                except Exception as e:
                    self.logger.debug(f"Error applying procedural rule: {e}")
                    continue

            # Determine best category
            best_category = ""
            best_confidence = 0.0

            if category_scores:
                # Normalize scores and find maximum
                max_score = max(category_scores.values())
                if max_score > 0:
                    for category, score in category_scores.items():
                        normalized_score = min(score / max_score, 1.0)
                        if normalized_score > best_confidence:
                            best_category = category
                            best_confidence = normalized_score

            # Enhanced reasoning details with Phase 3.1 context information
            context_metrics = {
                "asset_type_matches": len(
                    [r for r in applied_rules if r.get("asset_type_match", False)]
                ),
                "constraint_applications": len(
                    [r for r in applied_rules if r.get("constraint_applied", False)]
                ),
                "asset_context_enhancements": len(
                    [r for r in applied_rules if r.get("asset_context_applied", False)]
                ),
                "total_rules_evaluated": len(applied_rules),
                "avg_confidence": (
                    sum(r["confidence"] for r in applied_rules) / len(applied_rules)
                    if applied_rules
                    else 0.0
                ),
            }

            reasoning_details["memory_contributions"]["procedural"].update(
                {
                    "category": best_category,
                    "confidence": best_confidence,
                    "weight": config.procedural_memory_weight,
                    "rules_applied": applied_rules[:5],  # Top 5 rules
                    "category_scores": dict(
                        sorted(
                            category_scores.items(), key=lambda x: x[1], reverse=True
                        )[:5]
                    ),
                    "context_metrics": context_metrics,
                    "enhancement_factors": {
                        "asset_type_boost": config.asset_type_boost_factor,
                        "asset_type_penalty": config.asset_type_penalty_factor,
                        "constraint_strength": reasoning_details[
                            "asset_type_constraints"
                        ].get(
                            "constraint_strength", config.category_constraint_strength
                        ),
                        "context_confidence_threshold": config.context_confidence_threshold,
                    },
                    "status": "enhanced_phase_3_1",
                }
            )

            self.logger.info(
                f"Procedural classification: {best_category} "
                f"(confidence: {best_confidence:.3f}, rules: {len(applied_rules)})"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Procedural classification failed: {e}")
            reasoning_details["memory_contributions"]["procedural"].update(
                {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Procedural classification failed: {e}") from e

    @log_function()
    async def _get_semantic_classification(
        self,
        combined_text: str,
        asset_type: str,
        asset_id: str | None,
        allowed_categories: list[str],
        reasoning_details: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Get document classification using semantic memory hints and feedback.

        Uses human feedback and classification hints from semantic memory
        to predict document category based on similar cases.

        Args:
            combined_text: Combined document text for analysis
            asset_type: Asset type for context filtering
            asset_id: Optional asset ID for enhanced context
            allowed_categories: List of allowed categories for constraint filtering
            reasoning_details: Reasoning dictionary to update

        Returns:
            Tuple of (predicted_category, confidence_score)

        Raises:
            RuntimeError: If semantic memory operations fail
        """
        self.logger.debug("Getting semantic memory classification")

        try:
            if not self.semantic_memory:
                self.logger.warning("Semantic memory not available")
                reasoning_details["memory_contributions"]["semantic"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return "", 0.0

            # Get classification hints for this asset type
            hints_result = await self.semantic_memory.get_classification_hints(
                asset_type=asset_type,
                document_context={"text": combined_text[:500], "asset_id": asset_id},
            )

            category_scores: dict[str, float] = {}
            hints_found = []

            if hints_result and hints_result.get("hints"):
                for hint in hints_result["hints"]:
                    hint_category = hint.get("category", "").lower()
                    hint_confidence = hint.get("confidence", 0.0)
                    hint_similarity = hint.get("similarity", 0.0)

                    # Apply constraint filtering
                    if allowed_categories and hint_category not in [
                        c.lower() for c in allowed_categories
                    ]:
                        continue

                    # Weight by similarity and human feedback strength
                    weighted_score = hint_confidence * hint_similarity

                    # Boost human feedback over automatic hints
                    if hint.get("source") == "human_feedback":
                        weighted_score *= 1.4

                    # Boost recent feedback
                    timestamp = hint.get("timestamp")
                    if timestamp:
                        # # Standard library imports
                        from datetime import UTC, datetime

                        try:
                            if isinstance(timestamp, str):
                                hint_time = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                            else:
                                hint_time = datetime.fromtimestamp(timestamp, UTC)

                            days_old = (datetime.now(UTC) - hint_time).days
                            recency_boost = max(
                                0.5, 1.0 - (days_old / 180.0)
                            )  # 6 month decay
                            weighted_score *= recency_boost
                        except (ValueError, TypeError):
                            pass  # Use original score if timestamp parsing fails

                    if hint_category not in category_scores:
                        category_scores[hint_category] = 0.0
                    category_scores[hint_category] += weighted_score

                    hints_found.append(
                        {
                            "category": hint_category,
                            "confidence": hint_confidence,
                            "similarity": hint_similarity,
                            "source": hint.get("source", "unknown"),
                            "weighted_score": weighted_score,
                        }
                    )

            # Search for similar document classification experiences
            similar_docs = await self.semantic_memory.search(
                query_text=f"document classification {asset_type} {combined_text[:200]}",
                limit=config.semantic_search_limit,
                filter_metadata={"knowledge_type": "classification_feedback"},
            )

            if similar_docs and similar_docs.get("results"):
                for result in similar_docs["results"]:
                    metadata = result.get("metadata", {})
                    doc_category = metadata.get("category", "").lower()
                    similarity_score = result.get("score", 0.0)

                    # Apply constraint filtering
                    if allowed_categories and doc_category not in [
                        c.lower() for c in allowed_categories
                    ]:
                        continue

                    # Weight by similarity and feedback quality
                    feedback_confidence = metadata.get("confidence", 0.5)
                    weighted_score = (
                        similarity_score * feedback_confidence * 0.8
                    )  # Lower weight than direct hints

                    if doc_category not in category_scores:
                        category_scores[doc_category] = 0.0
                    category_scores[doc_category] += weighted_score

            # Determine best category
            best_category = ""
            best_confidence = 0.0

            if category_scores:
                max_score = max(category_scores.values())
                if max_score > 0:
                    for category, score in category_scores.items():
                        normalized_score = min(score / max_score, 1.0)
                        if normalized_score > best_confidence:
                            best_category = category
                            best_confidence = normalized_score

            # Update reasoning details
            reasoning_details["memory_contributions"]["semantic"].update(
                {
                    "category": best_category,
                    "confidence": best_confidence,
                    "weight": config.semantic_memory_weight,
                    "hints_found": hints_found[:5],  # Top 5 hints
                    "category_scores": dict(
                        sorted(
                            category_scores.items(), key=lambda x: x[1], reverse=True
                        )[:5]
                    ),
                    "total_hints": len(hints_found),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Semantic classification: {best_category} "
                f"(confidence: {best_confidence:.3f}, hints: {len(hints_found)})"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Semantic classification failed: {e}")
            reasoning_details["memory_contributions"]["semantic"].update(
                {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Semantic classification failed: {e}") from e

    @log_function()
    async def _get_episodic_classification(
        self,
        filename: str,
        subject: str,
        body: str,
        asset_type: str,
        allowed_categories: list[str],
        reasoning_details: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Get document classification using episodic memory experiences.

        Uses past classification experiences and successful patterns
        from episodic memory to predict document category.

        Args:
            filename: Document filename for pattern matching
            subject: Email subject for context matching
            body: Email body for content matching
            asset_type: Asset type for context filtering
            allowed_categories: List of allowed categories for constraint filtering
            reasoning_details: Reasoning dictionary to update

        Returns:
            Tuple of (predicted_category, confidence_score)

        Raises:
            RuntimeError: If episodic memory operations fail
        """
        self.logger.debug("Getting episodic memory classification")

        try:
            if not self.episodic_memory:
                self.logger.warning("Episodic memory not available")
                reasoning_details["memory_contributions"]["episodic"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return "", 0.0

            # Search for similar classification experiences
            search_queries = [
                f"document classification {asset_type} {filename}",
                f"category decision {subject}",
                f"classification result {body[:100]}",
            ]

            all_experiences = []

            for query in search_queries:
                if not query.strip():
                    continue

                try:
                    results = await self.episodic_memory.search(
                        query_text=query,
                        limit=config.episodic_search_limit,
                        memory_type="decision",
                    )

                    if results and results.get("results"):
                        all_experiences.extend(results["results"])

                except Exception as e:
                    self.logger.debug(
                        f"Episodic search failed for query '{query}': {e}"
                    )
                    continue

            if not all_experiences:
                self.logger.info("No episodic classification experiences found")
                reasoning_details["memory_contributions"]["episodic"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": config.episodic_memory_weight,
                        "experiences": [],
                        "status": "no_experiences",
                    }
                )
                return "", 0.0

            self.logger.info(
                f"Processing {len(all_experiences)} episodic classification experiences"
            )

            category_scores: dict[str, list[float]] = {}
            relevant_experiences = []

            for experience in all_experiences:
                try:
                    metadata = experience.get("metadata", {})
                    similarity_score = experience.get("score", 0.0)

                    # Extract classification information
                    result_category = metadata.get("result_category") or metadata.get(
                        "category", ""
                    )
                    result_category = result_category.lower()

                    decision_outcome = metadata.get("outcome", "unknown")
                    decision_confidence = metadata.get("confidence", 0.0)
                    experience_asset_type = metadata.get("asset_type", "")

                    if (
                        not result_category
                        or similarity_score < config.episodic_similarity_threshold
                    ):
                        continue

                    # Apply constraint filtering
                    if allowed_categories and result_category not in [
                        c.lower() for c in allowed_categories
                    ]:
                        continue

                    # Weight by outcome success
                    outcome_weights = {
                        "success": 1.2,
                        "partial_success": 1.0,
                        "human_corrected": 0.8,
                        "failure": 0.3,
                        "unknown": 0.5,
                    }
                    outcome_weight = outcome_weights.get(decision_outcome, 0.5)

                    # Asset type relevance boost
                    asset_relevance = 1.0
                    if experience_asset_type.lower() == asset_type.lower():
                        asset_relevance = 1.3
                    elif (
                        experience_asset_type
                        and experience_asset_type.lower() != asset_type.lower()
                    ):
                        asset_relevance = 0.7

                    # Apply temporal decay
                    timestamp = metadata.get("timestamp")
                    temporal_weight = 1.0

                    if timestamp:
                        # # Standard library imports
                        from datetime import UTC, datetime

                        try:
                            if isinstance(timestamp, str):
                                exp_time = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                            else:
                                exp_time = datetime.fromtimestamp(timestamp, UTC)

                            days_old = (datetime.now(UTC) - exp_time).days
                            temporal_weight = max(
                                0.3, 1.0 - (days_old / 365.0)
                            )  # Decay over 1 year
                        except (ValueError, TypeError):
                            pass

                    # Calculate final experience score
                    experience_score = (
                        similarity_score
                        * outcome_weight
                        * asset_relevance
                        * temporal_weight
                        * decision_confidence
                    )

                    if result_category not in category_scores:
                        category_scores[result_category] = []
                    category_scores[result_category].append(experience_score)

                    relevant_experiences.append(
                        {
                            "category": result_category,
                            "outcome": decision_outcome,
                            "confidence": decision_confidence,
                            "similarity": similarity_score,
                            "experience_score": experience_score,
                            "asset_type_match": experience_asset_type.lower()
                            == asset_type.lower(),
                        }
                    )

                except Exception as e:
                    self.logger.debug(f"Error processing episodic experience: {e}")
                    continue

            # Calculate final category scores
            best_category = ""
            best_confidence = 0.0

            for category, scores in category_scores.items():
                if scores:
                    # Use weighted average with bias toward higher scores
                    sorted_scores = sorted(scores, reverse=True)
                    if len(sorted_scores) >= 3:
                        weighted_avg = (
                            sorted_scores[0] * 0.5
                            + sorted_scores[1] * 0.3
                            + sorted_scores[2] * 0.2
                        )
                    elif len(sorted_scores) == 2:
                        weighted_avg = sorted_scores[0] * 0.7 + sorted_scores[1] * 0.3
                    else:
                        weighted_avg = sorted_scores[0]

                    normalized_score = min(weighted_avg, 1.0)
                    if normalized_score > best_confidence:
                        best_category = category
                        best_confidence = normalized_score

            # Update reasoning details
            reasoning_details["memory_contributions"]["episodic"].update(
                {
                    "category": best_category,
                    "confidence": best_confidence,
                    "weight": config.episodic_memory_weight,
                    "experiences": relevant_experiences[:5],  # Top 5 experiences
                    "category_scores": {
                        cat: max(scores)
                        for cat, scores in sorted(
                            category_scores.items(),
                            key=lambda x: max(x[1]),
                            reverse=True,
                        )[:5]
                    },
                    "total_experiences": len(relevant_experiences),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Episodic classification: {best_category} "
                f"(confidence: {best_confidence:.3f}, experiences: {len(relevant_experiences)})"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Episodic classification failed: {e}")
            reasoning_details["memory_contributions"]["episodic"].update(
                {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Episodic classification failed: {e}") from e

    @log_function()
    async def _get_contact_classification(
        self,
        subject: str,
        body: str,
        asset_type: str,
        allowed_categories: list[str],
        reasoning_details: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Get document classification using contact memory patterns.

        Uses sender patterns and document type associations from contact
        memory to predict document category based on organizational patterns.

        Args:
            subject: Email subject for sender pattern matching
            body: Email body for content pattern matching
            asset_type: Asset type for context filtering
            allowed_categories: List of allowed categories for constraint filtering
            reasoning_details: Reasoning dictionary to update

        Returns:
            Tuple of (predicted_category, confidence_score)

        Raises:
            RuntimeError: If contact memory operations fail
        """
        self.logger.debug("Getting contact memory classification")

        try:
            if not self.contact_memory:
                self.logger.warning("Contact memory not available")
                reasoning_details["memory_contributions"]["contact"].update(
                    {
                        "category": "",
                        "confidence": 0.0,
                        "weight": 0.0,
                        "status": "unavailable",
                    }
                )
                return "", 0.0

            # Extract sender email from subject/body if available
            sender_email = ""
            # # Standard library imports
            import re

            # Look for email patterns in subject and body
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            email_matches = re.findall(email_pattern, f"{subject} {body}")

            if email_matches:
                sender_email = email_matches[0]  # Use first found email

            category_scores: dict[str, float] = {}
            contact_patterns = []

            if sender_email:
                # Find contact information for sender
                contact_info = await self.contact_memory.find_contact_by_email(
                    sender_email
                )

                if contact_info:
                    # Use contact organization patterns
                    org = getattr(contact_info, "organization", "") or ""
                    tags = getattr(contact_info, "tags", []) or []

                    # Organizational document patterns
                    org_patterns = {
                        "legal": ["contract", "agreement"],
                        "accounting": ["invoice", "statement"],
                        "consulting": ["report", "proposal"],
                        "vendor": ["invoice", "proposal"],
                        "client": ["correspondence", "report"],
                    }

                    for pattern_type, categories in org_patterns.items():
                        if pattern_type in org.lower() or pattern_type in [
                            tag.lower() for tag in tags
                        ]:
                            for category in categories:
                                if not allowed_categories or category in [
                                    c.lower() for c in allowed_categories
                                ]:
                                    if category not in category_scores:
                                        category_scores[category] = 0.0
                                    category_scores[category] += 0.6

                                    contact_patterns.append(
                                        {
                                            "pattern_type": pattern_type,
                                            "category": category,
                                            "confidence": 0.6,
                                            "source": "organization_pattern",
                                        }
                                    )

            # Subject line document type indicators
            subject_patterns = {
                "invoice": ["invoice", "bill", "payment", "charge"],
                "contract": ["contract", "agreement", "terms", "signed"],
                "report": ["report", "analysis", "summary", "findings"],
                "correspondence": ["re:", "fwd:", "regarding", "follow up"],
                "proposal": ["proposal", "quote", "estimate", "bid"],
                "statement": ["statement", "summary", "account"],
            }

            subject_lower = subject.lower()
            for category, keywords in subject_patterns.items():
                if not allowed_categories or category in [
                    c.lower() for c in allowed_categories
                ]:
                    for keyword in keywords:
                        if keyword in subject_lower:
                            if category not in category_scores:
                                category_scores[category] = 0.0
                            category_scores[category] += 0.4

                            contact_patterns.append(
                                {
                                    "pattern_type": "subject_indicator",
                                    "category": category,
                                    "confidence": 0.4,
                                    "keyword": keyword,
                                    "source": "subject_pattern",
                                }
                            )

            # Body content document type indicators
            body_patterns = {
                "contract": ["hereby agree", "terms and conditions", "legal binding"],
                "invoice": ["amount due", "payment terms", "invoice number"],
                "report": ["executive summary", "findings", "recommendations"],
                "correspondence": ["thank you", "please find", "attached"],
            }

            body_lower = body.lower()
            for category, phrases in body_patterns.items():
                if not allowed_categories or category in [
                    c.lower() for c in allowed_categories
                ]:
                    for phrase in phrases:
                        if phrase in body_lower:
                            if category not in category_scores:
                                category_scores[category] = 0.0
                            category_scores[category] += 0.3

                            contact_patterns.append(
                                {
                                    "pattern_type": "body_indicator",
                                    "category": category,
                                    "confidence": 0.3,
                                    "phrase": phrase,
                                    "source": "body_pattern",
                                }
                            )

            # Determine best category
            best_category = ""
            best_confidence = 0.0

            if category_scores:
                max_score = max(category_scores.values())
                if max_score > 0:
                    for category, score in category_scores.items():
                        normalized_score = min(score / max_score, 1.0)
                        if normalized_score > best_confidence:
                            best_category = category
                            best_confidence = normalized_score

            # Update reasoning details
            reasoning_details["memory_contributions"]["contact"].update(
                {
                    "category": best_category,
                    "confidence": best_confidence,
                    "weight": config.contact_memory_weight,
                    "patterns": contact_patterns[:5],  # Top 5 patterns
                    "category_scores": dict(
                        sorted(
                            category_scores.items(), key=lambda x: x[1], reverse=True
                        )[:5]
                    ),
                    "sender_found": bool(sender_email),
                    "total_patterns": len(contact_patterns),
                    "status": "success",
                }
            )

            self.logger.info(
                f"Contact classification: {best_category} "
                f"(confidence: {best_confidence:.3f}, patterns: {len(contact_patterns)})"
            )

            return best_category, best_confidence

        except Exception as e:
            self.logger.error(f"Contact classification failed: {e}")
            reasoning_details["memory_contributions"]["contact"].update(
                {
                    "category": "",
                    "confidence": 0.0,
                    "weight": 0.0,
                    "status": f"error: {str(e)}",
                }
            )
            raise RuntimeError(f"Contact classification failed: {e}") from e

    @log_function()
    async def _combine_classification_results(
        self,
        procedural_result: tuple[str, float],
        semantic_result: tuple[str, float],
        episodic_result: tuple[str, float],
        contact_result: tuple[str, float],
        allowed_categories: list[str],
        reasoning_details: dict[str, Any],
    ) -> tuple[str, float]:
        """
        Combine classification results from all memory sources.

        Phase 2.2: Implements advanced result combination with asset type
        constraint filtering and weighted scoring across all memory types.

        Args:
            procedural_result: Tuple of (category, confidence) from procedural memory
            semantic_result: Tuple of (category, confidence) from semantic memory
            episodic_result: Tuple of (category, confidence) from episodic memory
            contact_result: Tuple of (category, confidence) from contact memory
            allowed_categories: List of allowed categories for constraint filtering
            reasoning_details: Reasoning dictionary to update

        Returns:
            Tuple of (final_category, final_confidence)

        Raises:
            RuntimeError: If result combination fails
        """
        self.logger.info("Combining classification results with weighted scoring")

        try:
            # Extract individual results
            proc_category, proc_confidence = procedural_result
            sem_category, sem_confidence = semantic_result
            epi_category, epi_confidence = episodic_result
            contact_category, contact_confidence = contact_result

            # Get memory weights from reasoning details
            weights = {
                "procedural": reasoning_details["memory_contributions"]["procedural"][
                    "weight"
                ],
                "semantic": reasoning_details["memory_contributions"]["semantic"][
                    "weight"
                ],
                "episodic": reasoning_details["memory_contributions"]["episodic"][
                    "weight"
                ],
                "contact": reasoning_details["memory_contributions"]["contact"][
                    "weight"
                ],
            }

            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}
            else:
                weights = dict.fromkeys(weights, 0.25)

            self.logger.info(f"Using classification weights: {weights}")
            reasoning_details["decision_flow"].append(
                f"Applied classification weights: {weights}"
            )

            # Collect all unique categories
            all_categories = set()
            category_votes = {}

            # Add categories with their weighted confidence scores
            if proc_category and proc_confidence > 0:
                all_categories.add(proc_category)
                category_votes[proc_category] = category_votes.get(proc_category, 0) + (
                    proc_confidence * weights["procedural"]
                )

            if sem_category and sem_confidence > 0:
                all_categories.add(sem_category)
                category_votes[sem_category] = category_votes.get(sem_category, 0) + (
                    sem_confidence * weights["semantic"]
                )

            if epi_category and epi_confidence > 0:
                all_categories.add(epi_category)
                category_votes[epi_category] = category_votes.get(epi_category, 0) + (
                    epi_confidence * weights["episodic"]
                )

            if contact_category and contact_confidence > 0:
                all_categories.add(contact_category)
                category_votes[contact_category] = category_votes.get(
                    contact_category, 0
                ) + (contact_confidence * weights["contact"])

            if not category_votes:
                self.logger.warning("No classification results from any memory source")
                reasoning_details["decision_flow"].append(
                    "No categories predicted by any memory source"
                )
                reasoning_details["final_category"] = "other"
                reasoning_details["final_confidence"] = 0.0
                return "other", 0.0

            # Apply asset type constraint filtering
            filtered_out = []
            if allowed_categories:
                for category in list(category_votes):
                    if category not in [c.lower() for c in allowed_categories]:
                        score = category_votes.pop(category)
                        filtered_out.append({"category": category, "score": score})

                reasoning_details["asset_type_constraints"][
                    "filtered_out"
                ] = filtered_out

                if not category_votes:
                    self.logger.warning(
                        "All predicted categories filtered out by asset type constraints"
                    )
                    reasoning_details["decision_flow"].append(
                        "All categories filtered by asset type constraints"
                    )
                    # Fallback to most common allowed category or "other"
                    fallback_category = (
                        allowed_categories[0] if allowed_categories else "other"
                    )
                    reasoning_details["final_category"] = fallback_category
                    reasoning_details["final_confidence"] = 0.1
                    return fallback_category, 0.1

            # Apply source agreement boost
            source_agreement = {}
            for category in category_votes:
                agreement_count = 0
                if category == proc_category and proc_confidence > 0:
                    agreement_count += 1
                if category == sem_category and sem_confidence > 0:
                    agreement_count += 1
                if category == epi_category and epi_confidence > 0:
                    agreement_count += 1
                if category == contact_category and contact_confidence > 0:
                    agreement_count += 1

                source_agreement[category] = agreement_count

                # Boost for multiple source agreement
                if agreement_count >= 2:
                    agreement_boost = min(0.3, (agreement_count - 1) * 0.15)
                    category_votes[category] += agreement_boost

            # Find the best category
            best_category = max(category_votes.items(), key=lambda x: x[1])
            final_category = best_category[0]
            final_confidence = min(best_category[1], 1.0)

            # Determine primary driver
            source_contributions = {
                "procedural": (
                    proc_confidence * weights["procedural"]
                    if proc_category == final_category
                    else 0
                ),
                "semantic": (
                    sem_confidence * weights["semantic"]
                    if sem_category == final_category
                    else 0
                ),
                "episodic": (
                    epi_confidence * weights["episodic"]
                    if epi_category == final_category
                    else 0
                ),
                "contact": (
                    contact_confidence * weights["contact"]
                    if contact_category == final_category
                    else 0
                ),
            }

            primary_driver = max(source_contributions.items(), key=lambda x: x[1])[0]
            reasoning_details["primary_driver"] = primary_driver

            # Update final reasoning details
            reasoning_details.update(
                {
                    "category_scores": dict(
                        sorted(category_votes.items(), key=lambda x: x[1], reverse=True)
                    ),
                    "source_agreement": source_agreement,
                    "final_category": final_category,
                    "final_confidence": final_confidence,
                }
            )

            reasoning_details["decision_flow"].append(
                f"Combined {len(all_categories)} candidate categories, "
                f"final decision: {final_category} (confidence: {final_confidence:.3f}), "
                f"primary driver: {primary_driver}, "
                f"source agreement: {source_agreement.get(final_category, 0)} sources"
            )

            self.logger.info(
                f"Classification combination complete: {final_category} "
                f"(confidence: {final_confidence:.3f}, primary driver: {primary_driver})"
            )

            return final_category, final_confidence

        except Exception as e:
            self.logger.error(f"Classification result combination failed: {e}")
            reasoning_details["decision_flow"].append(
                f"ERROR in result combination: {str(e)}"
            )
            raise RuntimeError(f"Result combination failed: {e}") from e

    def _analyze_classification_confidence(
        self,
        final_category: str,
        final_confidence: float,
        reasoning_details: dict[str, Any],
    ) -> None:
        """
        Analyze overall classification confidence and update reasoning.

        Determines confidence level based on score quality and source agreement.

        Args:
            final_category: Final predicted category
            final_confidence: Final confidence score
            reasoning_details: Reasoning dictionary to update
        """
        if not final_category or final_category == "other":
            reasoning_details["confidence_level"] = "very_low"
            reasoning_details["decision_flow"].append(
                "Unknown category - very low confidence"
            )
            return

        # Count active memory sources that contributed
        active_sources = sum(
            1
            for contrib in reasoning_details["memory_contributions"].values()
            if contrib["confidence"] > 0
        )

        # Check source agreement
        source_agreement = reasoning_details.get("source_agreement", {}).get(
            final_category, 0
        )

        # Determine confidence level
        if final_confidence >= 0.8 and source_agreement >= 3:
            confidence_level = "very_high"
        elif final_confidence >= 0.7 and source_agreement >= 2:
            confidence_level = "high"
        elif final_confidence >= 0.5 and active_sources >= 2:
            confidence_level = "medium"
        elif final_confidence >= 0.3:
            confidence_level = "low"
        else:
            confidence_level = "very_low"

        reasoning_details["confidence_level"] = confidence_level
        reasoning_details["decision_flow"].append(
            f"Classification confidence: {confidence_level} "
            f"(score: {final_confidence:.3f}, agreement: {source_agreement} sources, "
            f"active sources: {active_sources})"
        )

    # ========================================================================================
    # Phase 3.2: Multi-Source Context Clues Implementation
    # ========================================================================================

    @log_function()
    async def create_unified_context(
        self,
        sender_email: str,
        email_subject: str,
        email_body: str,
        filename: str,
    ) -> UnifiedContext:
        """
        Create unified context object from all available sources.

        Phase 3.2 implementation that extracts and combines context clues from
        sender, subject, body, and filename sources with confidence scoring
        and decision auditing capabilities.

        Args:
            sender_email: Email sender address for contact context
            email_subject: Email subject line for parsing
            email_body: Email body text for analysis
            filename: Attachment filename for parsing

        Returns:
            UnifiedContext object with all context sources combined

        Raises:
            RuntimeError: If context creation fails
        """
        self.logger.info("🔍 Creating unified context from all sources")

        try:
            # Extract context from each source
            sender_context = await self._extract_sender_context(sender_email)
            subject_context = await self._extract_subject_context(email_subject)
            body_context = await self._extract_body_context(email_body)
            filename_context = await self._extract_filename_context(filename)

            # Combine and analyze all context clues
            all_clues = (
                sender_context + subject_context + body_context + filename_context
            )

            # Calculate context agreement and conflicts
            context_agreement, context_conflicts = self._analyze_context_agreement(
                all_clues
            )

            # Extract primary hints
            primary_asset_hints = self._extract_primary_asset_hints(all_clues)
            primary_document_hints = self._extract_primary_document_hints(all_clues)

            # Calculate combined confidence
            combined_confidence = self._calculate_combined_confidence(
                all_clues, context_agreement
            )

            # Create detailed reasoning
            reasoning_details = {
                "source_counts": {
                    "sender": len(sender_context),
                    "subject": len(subject_context),
                    "body": len(body_context),
                    "filename": len(filename_context),
                },
                "total_clues": len(all_clues),
                "confidence_distribution": self._analyze_confidence_distribution(
                    all_clues
                ),
                "context_weights": {
                    "sender": config.sender_context_weight,
                    "subject": config.subject_context_weight,
                    "body": config.body_context_weight,
                    "filename": config.filename_context_weight,
                },
                "extraction_status": "phase_3_2_complete",
            }

            unified_context = UnifiedContext(
                sender_context=sender_context,
                subject_context=subject_context,
                body_context=body_context,
                filename_context=filename_context,
                combined_confidence=combined_confidence,
                context_agreement=context_agreement,
                context_conflicts=context_conflicts,
                primary_asset_hints=primary_asset_hints,
                primary_document_hints=primary_document_hints,
                reasoning_details=reasoning_details,
            )

            self.logger.info(
                f"📊 Unified context created: {len(all_clues)} total clues, "
                f"agreement: {context_agreement:.3f}, confidence: {combined_confidence:.3f}"
            )

            return unified_context

        except Exception as e:
            self.logger.error(f"Failed to create unified context: {e}")
            raise RuntimeError(f"Unified context creation failed: {e}") from e

    @log_function()
    async def _extract_sender_context(self, sender_email: str) -> list[ContextClue]:
        """
        Extract context clues from email sender information.

        Uses contact memory integration to extract organizational patterns,
        sender trust, and historical document patterns.

        Args:
            sender_email: Email address of the sender

        Returns:
            List of context clues from sender analysis

        Raises:
            RuntimeError: If sender context extraction fails
        """
        self.logger.debug(f"Extracting sender context from: {sender_email}")

        context_clues = []

        try:
            if not sender_email or not sender_email.strip():
                return context_clues

            sender_email = sender_email.strip().lower()

            # Extract domain information
            if "@" in sender_email:
                domain = sender_email.split("@")[1]

                # Common organizational domain patterns
                org_patterns = {
                    "law": ["law", "legal", "attorney", "counsel"],
                    "accounting": ["cpa", "accounting", "audit", "tax"],
                    "consulting": ["consulting", "advisory", "strategy"],
                    "investment": ["capital", "investment", "partners", "fund"],
                    "property": ["property", "real", "estate", "realty"],
                    "construction": ["construction", "building", "development"],
                }

                for org_type, keywords in org_patterns.items():
                    if any(keyword in domain for keyword in keywords):
                        context_clues.append(
                            ContextClue(
                                source="sender",
                                clue_type="organization",
                                value=org_type,
                                confidence=config.sender_context_weight * 0.8,
                                metadata={"domain": domain, "pattern_match": keywords},
                            )
                        )

                # Extract organization name from domain
                if "." in domain:
                    org_name = domain.split(".")[0]
                    context_clues.append(
                        ContextClue(
                            source="sender",
                            clue_type="organization",
                            value=org_name,
                            confidence=config.sender_context_weight * 0.6,
                            metadata={"domain": domain, "extracted_name": org_name},
                        )
                    )

            # Contact memory integration
            if self.contact_memory:
                try:
                    contact_info = await self.contact_memory.find_contact_by_email(
                        sender_email
                    )
                    if contact_info:
                        # Organization context
                        if (
                            hasattr(contact_info, "organization")
                            and contact_info.organization
                        ):
                            context_clues.append(
                                ContextClue(
                                    source="sender",
                                    clue_type="organization",
                                    value=contact_info.organization,
                                    confidence=config.sender_context_weight * 1.0,
                                    metadata={
                                        "source": "contact_memory",
                                        "verified": True,
                                    },
                                )
                            )

                        # Tags and categories
                        if hasattr(contact_info, "tags") and contact_info.tags:
                            for tag in contact_info.tags[:3]:  # Top 3 tags
                                context_clues.append(
                                    ContextClue(
                                        source="sender",
                                        clue_type="document_type",
                                        value=tag,
                                        confidence=config.sender_context_weight * 0.7,
                                        metadata={"source": "contact_tags", "tag": tag},
                                    )
                                )

                except Exception as e:
                    self.logger.debug(
                        f"Contact memory lookup failed for {sender_email}: {e}"
                    )

            self.logger.debug(f"Extracted {len(context_clues)} sender context clues")
            return context_clues

        except Exception as e:
            self.logger.error(f"Sender context extraction failed: {e}")
            raise RuntimeError(f"Sender context extraction failed: {e}") from e

    @log_function()
    async def _extract_subject_context(self, email_subject: str) -> list[ContextClue]:
        """
        Extract context clues from email subject line.

        Parses subject for asset identifiers, document type hints,
        and contextual descriptions using pattern matching.

        Args:
            email_subject: Email subject line text

        Returns:
            List of context clues from subject analysis

        Raises:
            RuntimeError: If subject context extraction fails
        """
        self.logger.debug(f"Extracting subject context from: {email_subject[:50]}...")

        context_clues = []

        try:
            if not email_subject or not email_subject.strip():
                return context_clues

            subject_lower = email_subject.strip().lower()

            # Asset identifier patterns
            # # Standard library imports
            import re

            asset_patterns = {
                "property_address": r"\b\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd)\b",
                "fund_name": r"\b\w+\s+(fund|capital|partners|investment)\s+(i{1,3}|iv|v|vi{1,3}|[1-9])\b",
                "deal_code": r"\b[A-Z]{2,4}-?\d{2,4}\b",
                "project_name": r"\b(project|development|property)\s+\w+\b",
            }

            for pattern_type, regex in asset_patterns.items():
                matches = re.findall(regex, subject_lower, re.IGNORECASE)
                for match in matches[:2]:  # Limit to first 2 matches per type
                    match_text = " ".join(match) if isinstance(match, tuple) else match
                    context_clues.append(
                        ContextClue(
                            source="subject",
                            clue_type="asset_identifier",
                            value=match_text,
                            confidence=config.subject_context_weight * 0.9,
                            metadata={
                                "pattern_type": pattern_type,
                                "regex_match": True,
                            },
                        )
                    )

            # Document type indicators
            doc_type_patterns = {
                "financial_statements": [
                    "financial",
                    "statement",
                    "financials",
                    "p&l",
                    "income",
                ],
                "rent_roll": ["rent", "roll", "rental", "tenant"],
                "legal_documents": ["contract", "agreement", "legal", "amendment"],
                "appraisal": ["appraisal", "valuation", "assessed", "value"],
                "correspondence": ["re:", "fwd:", "follow up", "update", "regarding"],
                "report": ["report", "analysis", "summary", "findings"],
                "invoice": ["invoice", "bill", "payment", "charge"],
                "proposal": ["proposal", "quote", "estimate", "bid"],
            }

            for doc_type, keywords in doc_type_patterns.items():
                for keyword in keywords:
                    if keyword in subject_lower:
                        context_clues.append(
                            ContextClue(
                                source="subject",
                                clue_type="document_type",
                                value=doc_type,
                                confidence=config.subject_context_weight * 0.8,
                                metadata={
                                    "keyword_match": keyword,
                                    "pattern_based": True,
                                },
                            )
                        )
                        break  # Only add one clue per document type

            # Month/quarter indicators
            time_patterns = {
                "monthly": [
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                ],
                "quarterly": ["q1", "q2", "q3", "q4", "quarter"],
                "annual": ["annual", "yearly", "year end", "2023", "2024", "2025"],
            }

            for time_type, indicators in time_patterns.items():
                for indicator in indicators:
                    if indicator in subject_lower:
                        context_clues.append(
                            ContextClue(
                                source="subject",
                                clue_type="document_type",
                                value=f"{time_type}_report",
                                confidence=config.subject_context_weight * 0.6,
                                metadata={
                                    "time_indicator": indicator,
                                    "frequency": time_type,
                                },
                            )
                        )
                        break

            self.logger.debug(f"Extracted {len(context_clues)} subject context clues")
            return context_clues

        except Exception as e:
            self.logger.error(f"Subject context extraction failed: {e}")
            raise RuntimeError(f"Subject context extraction failed: {e}") from e

    @log_function()
    async def _extract_body_context(self, email_body: str) -> list[ContextClue]:
        """
        Extract context clues from email body text.

        Analyzes body content for contextual descriptions, asset references,
        and document type indicators using text analysis.

        Args:
            email_body: Email body text content

        Returns:
            List of context clues from body analysis

        Raises:
            RuntimeError: If body context extraction fails
        """
        self.logger.debug(f"Extracting body context from {len(email_body)} characters")

        context_clues = []

        try:
            if not email_body or not email_body.strip():
                return context_clues

            body_lower = email_body.strip().lower()

            # Limit analysis to first 1000 characters for performance
            analysis_text = body_lower[:1000]

            # Asset type indicators
            asset_type_patterns = {
                "commercial_real_estate": [
                    "property",
                    "real estate",
                    "commercial",
                    "retail",
                    "office",
                    "warehouse",
                ],
                "private_credit": ["loan", "credit", "debt", "lending", "borrower"],
                "private_equity": ["portfolio", "investment", "equity", "acquisition"],
                "infrastructure": [
                    "infrastructure",
                    "utilities",
                    "transportation",
                    "energy",
                ],
            }

            for asset_type, keywords in asset_type_patterns.items():
                for keyword in keywords:
                    if keyword in analysis_text:
                        context_clues.append(
                            ContextClue(
                                source="body",
                                clue_type="asset_identifier",
                                value=asset_type,
                                confidence=config.body_context_weight * 0.7,
                                metadata={
                                    "keyword_match": keyword,
                                    "asset_type_hint": True,
                                },
                            )
                        )
                        break  # One clue per asset type

            # Document content indicators
            content_patterns = {
                "financial_statements": [
                    "revenue",
                    "expenses",
                    "profit",
                    "loss",
                    "ebitda",
                    "cash flow",
                ],
                "legal_documents": [
                    "hereby",
                    "agreement",
                    "parties",
                    "terms",
                    "conditions",
                ],
                "correspondence": [
                    "please",
                    "thank you",
                    "attached",
                    "find",
                    "regards",
                ],
                "report": [
                    "executive summary",
                    "conclusion",
                    "recommendations",
                    "findings",
                ],
                "invoice": ["amount due", "payment terms", "invoice number", "total"],
            }

            for doc_type, indicators in content_patterns.items():
                matches = sum(
                    1 for indicator in indicators if indicator in analysis_text
                )
                if matches >= 2:  # Require at least 2 indicators
                    context_clues.append(
                        ContextClue(
                            source="body",
                            clue_type="document_type",
                            value=doc_type,
                            confidence=config.body_context_weight
                            * min(matches * 0.3, 0.9),
                            metadata={
                                "indicator_count": matches,
                                "content_analysis": True,
                            },
                        )
                    )

            # Attachment references
            attachment_refs = ["attached", "attachment", "please find", "enclosed"]
            attachment_mentions = sum(
                1 for ref in attachment_refs if ref in analysis_text
            )

            if attachment_mentions > 0:
                context_clues.append(
                    ContextClue(
                        source="body",
                        clue_type="document_type",
                        value="attachment_referenced",
                        confidence=config.body_context_weight * 0.5,
                        metadata={
                            "reference_count": attachment_mentions,
                            "has_attachments": True,
                        },
                    )
                )

            self.logger.debug(f"Extracted {len(context_clues)} body context clues")
            return context_clues

        except Exception as e:
            self.logger.error(f"Body context extraction failed: {e}")
            raise RuntimeError(f"Body context extraction failed: {e}") from e

    @log_function()
    async def _extract_filename_context(self, filename: str) -> list[ContextClue]:
        """
        Extract context clues from attachment filename.

        Parses filename for naming conventions, document type hints,
        and structural patterns common in business documents.

        Args:
            filename: Attachment filename with extension

        Returns:
            List of context clues from filename analysis

        Raises:
            RuntimeError: If filename context extraction fails
        """
        self.logger.debug(f"Extracting filename context from: {filename}")

        context_clues = []

        try:
            if not filename or not filename.strip():
                return context_clues

            filename_clean = filename.strip().lower()

            # Remove file extension for analysis
            name_without_ext = filename_clean
            if "." in filename_clean:
                name_without_ext = filename_clean.rsplit(".", 1)[0]

            # Document type from filename patterns
            filename_patterns = {
                "financial_statements": [
                    "financial",
                    "p&l",
                    "income",
                    "statement",
                    "balance",
                ],
                "rent_roll": ["rent", "roll", "rental", "tenant"],
                "appraisal": ["appraisal", "valuation", "bpo", "assessment"],
                "legal_documents": ["contract", "agreement", "lease", "amendment"],
                "invoice": ["invoice", "bill", "receipt"],
                "report": ["report", "analysis", "summary"],
                "correspondence": ["letter", "email", "memo"],
                "property_photos": ["photo", "image", "picture", "jpg", "jpeg", "png"],
            }

            for doc_type, patterns in filename_patterns.items():
                for pattern in patterns:
                    if pattern in name_without_ext:
                        context_clues.append(
                            ContextClue(
                                source="filename",
                                clue_type="document_type",
                                value=doc_type,
                                confidence=config.filename_context_weight * 0.9,
                                metadata={
                                    "pattern_match": pattern,
                                    "filename_based": True,
                                },
                            )
                        )
                        break  # One clue per document type

            # Date patterns in filename
            # # Standard library imports
            import re

            date_patterns = [
                r"\d{4}[-_]\d{1,2}[-_]\d{1,2}",  # YYYY-MM-DD
                r"\d{1,2}[-_]\d{1,2}[-_]\d{4}",  # MM-DD-YYYY
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",  # Month names
                r"q[1-4]",  # Quarter indicators
            ]

            for pattern in date_patterns:
                if re.search(pattern, name_without_ext):
                    context_clues.append(
                        ContextClue(
                            source="filename",
                            clue_type="document_type",
                            value="dated_document",
                            confidence=config.filename_context_weight * 0.6,
                            metadata={
                                "date_pattern": pattern,
                                "temporal_reference": True,
                            },
                        )
                    )
                    break  # One date clue per filename

            # Version indicators
            version_patterns = [
                "v1",
                "v2",
                "v3",
                "version",
                "draft",
                "final",
                "revised",
            ]
            for version in version_patterns:
                if version in name_without_ext:
                    context_clues.append(
                        ContextClue(
                            source="filename",
                            clue_type="document_type",
                            value="versioned_document",
                            confidence=config.filename_context_weight * 0.5,
                            metadata={
                                "version_indicator": version,
                                "document_revision": True,
                            },
                        )
                    )
                    break

            # File extension context
            if "." in filename_clean:
                extension = filename_clean.rsplit(".", 1)[1]
                ext_types = {
                    "pdf": "document",
                    "xlsx": "spreadsheet",
                    "docx": "word_document",
                    "jpg": "image",
                    "png": "image",
                    "txt": "text",
                }

                if extension in ext_types:
                    context_clues.append(
                        ContextClue(
                            source="filename",
                            clue_type="document_type",
                            value=ext_types[extension],
                            confidence=config.filename_context_weight * 0.7,
                            metadata={"file_extension": extension, "format_hint": True},
                        )
                    )

            self.logger.debug(f"Extracted {len(context_clues)} filename context clues")
            return context_clues

        except Exception as e:
            self.logger.error(f"Filename context extraction failed: {e}")
            raise RuntimeError(f"Filename context extraction failed: {e}") from e

    # ========================================================================================
    # Phase 3.2: Context Analysis and Combination Helper Methods
    # ========================================================================================

    def _analyze_context_agreement(
        self, all_clues: list[ContextClue]
    ) -> tuple[float, list[dict[str, Any]]]:
        """
        Analyze agreement between context sources and identify conflicts.

        Calculates how well different context sources agree with each other
        and identifies areas of conflict for decision auditing.

        Args:
            all_clues: List of all context clues from all sources

        Returns:
            Tuple of (agreement_score, conflict_list)
        """
        if not all_clues:
            return 0.0, []

        # Group clues by type
        clues_by_type = {}
        for clue in all_clues:
            if clue.clue_type not in clues_by_type:
                clues_by_type[clue.clue_type] = []
            clues_by_type[clue.clue_type].append(clue)

        total_agreements = 0
        total_comparisons = 0
        conflicts = []

        # Analyze agreement within each clue type
        for clue_type, clues in clues_by_type.items():
            if len(clues) < 2:
                continue

            # Count value agreements
            value_counts = {}
            sources_per_value = {}

            for clue in clues:
                value = clue.value.lower()
                if value not in value_counts:
                    value_counts[value] = 0
                    sources_per_value[value] = set()
                value_counts[value] += 1
                sources_per_value[value].add(clue.source)

            # Calculate agreements and conflicts
            for i, clue1 in enumerate(clues):
                for clue2 in clues[i + 1 :]:
                    total_comparisons += 1

                    if clue1.value.lower() == clue2.value.lower():
                        # Agreement - weight by confidence
                        agreement_strength = (clue1.confidence + clue2.confidence) / 2
                        total_agreements += agreement_strength
                    else:
                        # Conflict - record for analysis
                        conflict_strength = abs(clue1.confidence - clue2.confidence)
                        if conflict_strength > config.context_conflict_penalty:
                            conflicts.append(
                                {
                                    "clue_type": clue_type,
                                    "conflicting_values": [clue1.value, clue2.value],
                                    "sources": [clue1.source, clue2.source],
                                    "confidences": [clue1.confidence, clue2.confidence],
                                    "conflict_strength": conflict_strength,
                                }
                            )

        # Calculate overall agreement score
        if total_comparisons > 0:
            agreement_score = total_agreements / total_comparisons

            # Apply agreement bonus
            if agreement_score > config.unified_context_threshold:
                agreement_score = min(
                    1.0, agreement_score + config.context_agreement_bonus
                )

            # Apply conflict penalty
            if conflicts:
                penalty = min(len(conflicts) * config.context_conflict_penalty, 0.5)
                agreement_score = max(0.0, agreement_score - penalty)
        else:
            agreement_score = 0.5  # Neutral score when no comparisons possible

        return agreement_score, conflicts

    def _extract_primary_asset_hints(self, all_clues: list[ContextClue]) -> list[str]:
        """
        Extract primary asset hints from all context clues.

        Identifies the most likely asset identifiers across all sources
        based on confidence and source agreement.

        Args:
            all_clues: List of all context clues from all sources

        Returns:
            List of primary asset hint strings
        """
        asset_clues = [
            clue for clue in all_clues if clue.clue_type == "asset_identifier"
        ]

        if not asset_clues:
            return []

        # Score asset hints by confidence and source diversity
        hint_scores = {}
        hint_sources = {}

        for clue in asset_clues:
            hint = clue.value.lower()
            if hint not in hint_scores:
                hint_scores[hint] = 0.0
                hint_sources[hint] = set()

            hint_scores[hint] += clue.confidence
            hint_sources[hint].add(clue.source)

        # Boost hints that appear in multiple sources
        for hint in hint_scores:
            source_count = len(hint_sources[hint])
            if source_count > 1:
                hint_scores[hint] *= (
                    1.0 + (source_count - 1) * 0.2
                )  # 20% boost per additional source

        # Return top asset hints sorted by score
        sorted_hints = sorted(hint_scores.items(), key=lambda x: x[1], reverse=True)
        return [hint for hint, _ in sorted_hints[:3]]  # Top 3 asset hints

    def _extract_primary_document_hints(
        self, all_clues: list[ContextClue]
    ) -> list[str]:
        """
        Extract primary document type hints from all context clues.

        Identifies the most likely document types across all sources
        based on confidence and source agreement.

        Args:
            all_clues: List of all context clues from all sources

        Returns:
            List of primary document hint strings
        """
        doc_clues = [clue for clue in all_clues if clue.clue_type == "document_type"]

        if not doc_clues:
            return []

        # Score document hints by confidence and source diversity
        hint_scores = {}
        hint_sources = {}

        for clue in doc_clues:
            hint = clue.value.lower()
            if hint not in hint_scores:
                hint_scores[hint] = 0.0
                hint_sources[hint] = set()

            hint_scores[hint] += clue.confidence
            hint_sources[hint].add(clue.source)

        # Boost hints that appear in multiple sources
        for hint in hint_scores:
            source_count = len(hint_sources[hint])
            if source_count > 1:
                hint_scores[hint] *= (
                    1.0 + (source_count - 1) * 0.3
                )  # 30% boost per additional source

        # Return top document hints sorted by score
        sorted_hints = sorted(hint_scores.items(), key=lambda x: x[1], reverse=True)
        return [hint for hint, _ in sorted_hints[:3]]  # Top 3 document hints

    def _calculate_combined_confidence(
        self, all_clues: list[ContextClue], context_agreement: float
    ) -> float:
        """
        Calculate combined confidence score for unified context.

        Combines individual clue confidences with context agreement
        and source diversity to produce overall context confidence.

        Args:
            all_clues: List of all context clues from all sources
            context_agreement: Agreement score between sources

        Returns:
            Combined confidence score (0.0 to 1.0)
        """
        if not all_clues:
            return 0.0

        # Calculate weighted average confidence by source
        source_confidences = {}
        source_counts = {}

        for clue in all_clues:
            source = clue.source
            if source not in source_confidences:
                source_confidences[source] = 0.0
                source_counts[source] = 0

            source_confidences[source] += clue.confidence
            source_counts[source] += 1

        # Get average confidence per source
        source_weights = {
            "sender": config.sender_context_weight,
            "subject": config.subject_context_weight,
            "body": config.body_context_weight,
            "filename": config.filename_context_weight,
        }

        weighted_confidence = 0.0
        total_weight = 0.0

        for source, total_confidence in source_confidences.items():
            if source_counts[source] > 0:
                avg_confidence = total_confidence / source_counts[source]
                weight = source_weights.get(source, 0.25)
                weighted_confidence += avg_confidence * weight
                total_weight += weight

        base_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0

        # Apply context agreement boost
        agreement_boost = context_agreement * 0.2  # Up to 20% boost for high agreement
        base_confidence += agreement_boost

        # Apply source diversity boost
        unique_sources = len({clue.source for clue in all_clues})
        diversity_boost = min(
            unique_sources * 0.05, 0.15
        )  # Up to 15% boost for all 4 sources
        base_confidence += diversity_boost

        return min(base_confidence, 1.0)

    def _analyze_confidence_distribution(
        self, all_clues: list[ContextClue]
    ) -> dict[str, Any]:
        """
        Analyze confidence distribution across context clues.

        Provides statistical analysis of confidence scores for
        reasoning and decision auditing.

        Args:
            all_clues: List of all context clues from all sources

        Returns:
            Dictionary with confidence distribution statistics
        """
        if not all_clues:
            return {
                "total_clues": 0,
                "avg_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "confidence_ranges": {},
            }

        confidences = [clue.confidence for clue in all_clues]

        # Basic statistics
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        # Confidence ranges
        ranges = {
            "very_high": sum(1 for c in confidences if c >= 0.8),
            "high": sum(1 for c in confidences if 0.6 <= c < 0.8),
            "medium": sum(1 for c in confidences if 0.4 <= c < 0.6),
            "low": sum(1 for c in confidences if 0.2 <= c < 0.4),
            "very_low": sum(1 for c in confidences if c < 0.2),
        }

        # Per-source analysis
        source_stats = {}
        for source in ["sender", "subject", "body", "filename"]:
            source_clues = [clue for clue in all_clues if clue.source == source]
            if source_clues:
                source_confidences = [clue.confidence for clue in source_clues]
                source_stats[source] = {
                    "count": len(source_clues),
                    "avg_confidence": sum(source_confidences) / len(source_confidences),
                    "max_confidence": max(source_confidences),
                }
            else:
                source_stats[source] = {
                    "count": 0,
                    "avg_confidence": 0.0,
                    "max_confidence": 0.0,
                }

        return {
            "total_clues": len(all_clues),
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "confidence_ranges": ranges,
            "source_statistics": source_stats,
        }

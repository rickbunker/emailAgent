"""
Asset Document E-Mail Ingestion Agent

An email-driven document processing and filing agent for private market assets.
Handles automatic extraction, classification, and organization of email attachments with
complete logging, type safety, and production-grade error handling.

Features:
    - Multi-phase document processing pipeline
    - Complete virus scanning with ClamAV integration
    - asset classification for private market investments
    - Qdrant vector database integration for storage
    - Sender-asset relationship mapping with confidence scoring
    - Duplicate detection via SHA256 hashing
    - Complete logging and monitoring

Phase 1 Implementation: ✅ COMPLETE
    - Attachment extraction from emails
    - SHA256 hashing and duplicate detection
    - ClamAV antivirus integration
    - File type validation

Phase 2 Implementation: ✅ COMPLETE
    - Qdrant collection setup and management
    - Asset definition and storage
    - Sender-Asset mapping system
    - Contact integration

Phase 3 Implementation: ✅ COMPLETE
    - Document classification by type
    - AI-powered content analysis
    - Asset identification from email content
    - Confidence-based routing decisions

Architecture:
    The agent operates through a multi-stage pipeline:
    1. File validation (type, size, virus scanning)
    2. Asset identification and sender mapping
    3. Document classification and routing
    4. Storage and indexing in Qdrant vector database

Asset Types Supported:
    - Commercial Real Estate
    - Private Credit
    - Private Equity
    - Infrastructure

Document Categories:
    25+ specialized document types across all asset classes with
    pattern-based classification and confidence scoring.

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
# Suppress HuggingFace tokenizers forking warning before any imports
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# # Standard library imports
import asyncio
import contextlib
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
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
    PointIdsList,
    PointStruct,
    VectorParams,
)

# Local imports
from ..utils.config import config
from ..utils.logging_system import get_logger, log_function

# Initialize logger
logger = get_logger(__name__)

# Memory imports (imported here to avoid circular imports)
try:
    from ..memory.episodic import EpisodicMemory, EpisodicMemoryType
except ImportError:
    EpisodicMemory = None
    EpisodicMemoryType = None

# Optional dependencies with graceful degradation
try:
    # # Third-party imports
    import clamd

    logger.info("ClamAV Python library loaded successfully")
except ImportError:
    clamd = None

try:
    # # Third-party imports
    from Levenshtein import distance as levenshtein_distance

    logger.info("Levenshtein library loaded successfully")
except ImportError:
    levenshtein_distance = None

try:
    # Qdrant already imported above
    logger.info("Qdrant client library loaded successfully")
except ImportError:
    QdrantClient = None

# Import email interface
try:
    from ..email_interface.base import Email, EmailAttachment

    logger.info("Email interface loaded successfully")
except ImportError:
    Email = None
    EmailAttachment = None


class ProcessingStatus(Enum):
    """
    Document processing status enumeration.

    Represents the various states a document can be in during the
    multi-phase processing pipeline from initial validation through
    final storage and classification.
    """

    PENDING = "pending"  # Awaiting processing
    PROCESSING = "processing"  # Currently being processed
    SUCCESS = "success"  # Successfully processed
    QUARANTINED = "quarantined"  # Isolated due to security concerns
    DUPLICATE = "duplicate"  # Identified as duplicate content
    INVALID_TYPE = "invalid_type"  # File type not supported
    AV_SCAN_FAILED = "av_scan_failed"  # Antivirus scan failed or detected threat
    ERROR = "error"  # Processing error occurred


class AssetType(Enum):
    """Private market asset types"""

    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    PRIVATE_CREDIT = "private_credit"
    PRIVATE_EQUITY = "private_equity"
    INFRASTRUCTURE = "infrastructure"


class DocumentCategory(Enum):
    """Document classification categories"""

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
    """Confidence levels for routing decisions"""

    HIGH = "high"  # ≥ 85% - Auto-process
    MEDIUM = "medium"  # ≥ 65% - Process with confirmation
    LOW = "low"  # ≥ 40% - Save uncategorized
    VERY_LOW = "very_low"  # < 40% - Human review required


@dataclass
class ProcessingResult:
    """Result of document processing"""

    status: ProcessingStatus
    file_hash: str | None = None
    file_path: Path | None = None
    confidence: float = 0.0
    error_message: str | None = None
    quarantine_reason: str | None = None
    duplicate_of: str | None = None
    metadata: dict[str, Any] = None

    # Phase 3: Document Classification
    document_category: DocumentCategory | None = None
    confidence_level: ConfidenceLevel | None = None
    matched_asset_id: str | None = None
    asset_confidence: float = 0.0
    classification_metadata: dict[str, Any] = None


@dataclass
class AssetDocumentConfig:
    """Configuration for asset document types"""

    allowed_extensions: list[str]
    max_file_size_mb: int
    quarantine_days: int
    version_retention_count: int


@dataclass
class Asset:
    """Asset definition for private market investments"""

    deal_id: str  # UUID
    deal_name: str  # Short name
    asset_name: str  # Full descriptive name
    asset_type: AssetType
    folder_path: str  # File system path
    identifiers: list[str]  # Alternative names/identifiers
    created_date: datetime
    last_updated: datetime
    metadata: dict[str, Any] = None


@dataclass
class AssetSenderMapping:
    """Many-to-many relationship between assets and senders"""

    mapping_id: str  # UUID
    asset_id: str  # Asset deal_id
    sender_email: str
    confidence: float  # 0.0 to 1.0
    document_types: list[str]  # Expected document categories
    created_date: datetime
    last_activity: datetime
    email_count: int = 0
    metadata: dict[str, Any] = None


@dataclass
class UnknownSender:
    """Tracking for unknown senders with timeout management"""

    sender_email: str
    first_seen: datetime
    last_seen: datetime
    email_count: int
    pending_documents: list[str]  # File hashes
    timeout_hours: int = 48
    escalated: bool = False
    metadata: dict[str, Any] = None


class AssetDocumentAgent:
    """
    Asset Document E-Mail Ingestion Agent for processing email attachments
    and organizing them by private market asset classification.

    Phase 1: File validation, hashing, and antivirus scanning
    Phase 2: Asset management, sender mapping, and Qdrant integration
    """

    # Asset type configurations
    ASSET_CONFIGS = {
        AssetType.COMMERCIAL_REAL_ESTATE: AssetDocumentConfig(
            allowed_extensions=[
                ".pdf",
                ".xlsx",
                ".xls",
                ".jpg",
                ".png",
                ".doc",
                ".docx",
            ],
            max_file_size_mb=50,
            quarantine_days=30,
            version_retention_count=10,
        ),
        AssetType.PRIVATE_CREDIT: AssetDocumentConfig(
            allowed_extensions=[".pdf", ".xlsx", ".xls", ".doc", ".docx"],
            max_file_size_mb=25,
            quarantine_days=30,
            version_retention_count=10,
        ),
        AssetType.PRIVATE_EQUITY: AssetDocumentConfig(
            allowed_extensions=[".pdf", ".xlsx", ".xls", ".pptx", ".doc", ".docx"],
            max_file_size_mb=100,
            quarantine_days=30,
            version_retention_count=10,
        ),
        AssetType.INFRASTRUCTURE: AssetDocumentConfig(
            allowed_extensions=[".pdf", ".xlsx", ".xls", ".dwg", ".jpg", ".png"],
            max_file_size_mb=75,
            quarantine_days=30,
            version_retention_count=10,
        ),
    }

    # Qdrant collection names
    COLLECTIONS = {
        "assets": "asset_management_assets",
        "asset_sender_mappings": "asset_management_sender_mappings",
        "processed_documents": "asset_management_processed_documents",
        "unknown_senders": "asset_management_unknown_senders",
    }

    def __init__(
        self,
        qdrant_client: QdrantClient | None = None,
        base_assets_path: str = "./assets",
        clamav_socket: str | None = None,
    ) -> None:
        """
        Initialize the Asset Document Agent.

        Sets up the document processing pipeline with vector database
        integration, antivirus scanning, and complete logging.

        Args:
            qdrant_client: Connected Qdrant client instance for vector storage
            base_assets_path: Base directory for storing asset documents
            clamav_socket: ClamAV socket path (None for auto-detection)

        Raises:
            OSError: If base assets path cannot be created
            RuntimeError: If critical dependencies are missing
        """
        self.logger = get_logger(f"{__name__}.AssetDocumentAgent")
        self.logger.info("Initializing Asset Document Agent")

        # Core components
        self.qdrant = qdrant_client
        self.base_assets_path = Path(base_assets_path)

        # Create base directory
        try:
            self.base_assets_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Asset storage path initialized: {self.base_assets_path}")
        except OSError as e:
            self.logger.error(f"Failed to create assets directory: {e}")
            raise

        # Initialize ClamAV
        self.clamscan_path: str | None = None
        self._init_clamav(clamav_socket)

        # Processing statistics
        self.stats: dict[str, int] = {
            "processed": 0,
            "quarantined": 0,
            "duplicates": 0,
            "errors": 0,
        }

        # Performance metrics
        self.processing_times: list[float] = []
        self.classification_cache: dict[str, tuple[DocumentCategory, float]] = {}

        self.logger.info("Asset Document Agent initialized successfully")

    @log_function()
    def _init_clamav(self, socket_path: str | None = None) -> None:
        """
        Initialize ClamAV antivirus scanning capabilities.

        Attempts to locate the clamscan executable in common installation paths
        and validates its availability for virus scanning operations.

        Args:
            socket_path: ClamAV daemon socket path (currently unused, reserved for future)

        Note:
            Currently uses command-line clamscan rather than daemon for better
            compatibility across different deployment environments.
        """
        logger.info("Initializing ClamAV antivirus integration")

        # Common ClamAV installation paths
        clamscan_paths = [
            "/opt/homebrew/bin/clamscan",  # macOS Homebrew
            "/usr/bin/clamscan",  # Linux
            "/usr/local/bin/clamscan",  # Other Unix systems
            "C:\\Program Files\\ClamAV\\clamscan.exe",  # Windows
        ]

        self.clamscan_path = None

        # Method 1: Try to find clamscan using which/where command
        try:
            which_cmd = "where" if os.name == "nt" else "which"
            result = subprocess.run(
                [which_cmd, "clamscan"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self.clamscan_path = result.stdout.strip()
                logger.info(f"Found clamscan via {which_cmd}: {self.clamscan_path}")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.debug(f"which/where command failed: {e}")

        # Method 2: Check common installation paths
        for path in clamscan_paths:
            if Path(path).exists():
                self.clamscan_path = path
                logger.info(f"Found clamscan at standard path: {self.clamscan_path}")
                return

        # Method 3: Use shutil.which as final fallback
        self.clamscan_path = shutil.which("clamscan")
        if self.clamscan_path:
            logger.info(f"Found clamscan via shutil.which: {self.clamscan_path}")
        else:
            logger.warning("ClamAV clamscan not found - antivirus scanning disabled")
            logger.info(
                "Install ClamAV: brew install clamav (macOS) or apt-get install clamav (Ubuntu)"
            )

        # Validate clamscan functionality if found
        if self.clamscan_path:
            self._validate_clamscan()

    @log_function()
    def _validate_clamscan(self) -> bool:
        """
        Validate ClamAV clamscan functionality.

        Tests the clamscan executable to ensure it's working properly
        and has access to updated virus definitions.

        Returns:
            True if clamscan is functional, False otherwise
        """
        if not self.clamscan_path:
            return False

        try:
            # Test clamscan with version check
            result = subprocess.run(
                [self.clamscan_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                version_info = result.stdout.strip()
                logger.info(f"ClamAV validation successful: {version_info}")
                return True
            else:
                logger.error(f"ClamAV validation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"ClamAV validation error: {e}")
            return False

    @log_function()
    def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content.

        Generates a unique identifier for file content to enable
        duplicate detection and content verification.

        Args:
            file_content: Raw bytes of the file

        Returns:
            Hexadecimal SHA256 hash string

        Raises:
            ValueError: If file_content is empty or None
        """
        if not file_content:
            raise ValueError("File content cannot be empty or None")

        file_hash = hashlib.sha256(file_content).hexdigest()
        logger.debug(f"Calculated SHA256 hash: {file_hash[:16]}...")
        return file_hash

    @log_function()
    def validate_file_type(
        self, filename: str, asset_type: AssetType | None = None
    ) -> bool:
        """
        Validate file type against allowed extensions.

        Checks if the file extension is permitted for the specified asset type
        or against all asset types if none specified.

        Args:
            filename: Name of the file to validate
            asset_type: Specific asset type to check against (if None, checks all types)

        Returns:
            True if file type is allowed, False otherwise

        Raises:
            ValueError: If filename is empty or None
        """
        if not filename:
            raise ValueError("Filename cannot be empty or None")

        file_extension = Path(filename).suffix.lower()
        logger.debug(f"Validating file type: {filename} (extension: {file_extension})")

        if asset_type:
            config = self.ASSET_CONFIGS[asset_type]
            is_valid = file_extension in config.allowed_extensions
            logger.debug(f"File type validation for {asset_type.value}: {is_valid}")
            return is_valid
        else:
            # Check against all asset types
            all_allowed: set[str] = set()
            for config in self.ASSET_CONFIGS.values():
                all_allowed.update(config.allowed_extensions)
            is_valid = file_extension in all_allowed
            logger.debug(f"File type validation against all asset types: {is_valid}")
            return is_valid

    def validate_file_size(
        self, file_size: int, asset_type: AssetType | None = None
    ) -> bool:
        """
        Validate file size against limits.

        Args:
            file_size: Size in bytes
            asset_type: Asset type to check against (if None, uses maximum)
        """
        if asset_type:
            config = self.ASSET_CONFIGS[asset_type]
            max_size = config.max_file_size_mb * 1024 * 1024
        else:
            # Use maximum allowed size across all asset types
            max_size = (
                max(config.max_file_size_mb for config in self.ASSET_CONFIGS.values())
                * 1024
                * 1024
            )

        return file_size <= max_size

    async def scan_file_antivirus(
        self, file_content: bytes, filename: str
    ) -> tuple[bool, str | None]:
        """
        Scan file content with ClamAV using command-line clamscan.

        Returns:
            (is_clean, threat_name)
        """
        if not self.clamscan_path:
            logger.warning("ClamAV not available – skipping scan for %s", filename)
            return True, None

        # Save file content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        try:
            # Run clamscan asynchronously on the file
            process = await asyncio.create_subprocess_exec(
                self.clamscan_path,
                "--stdout",
                "--no-summary",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=30  # 30 second timeout
            )

            # Decode bytes to string
            stdout = stdout.decode("utf-8") if stdout else ""
            stderr = stderr.decode("utf-8") if stderr else ""

            # Check if virus was found
            if "Infected files: 1" in stdout or process.returncode == 1:
                # Extract virus name from output
                for line in stdout.splitlines():
                    if temp_path in line and ": " in line:
                        threat_name = line.split(": ")[1].strip()
                        if threat_name.upper() != "OK":
                            logger.warning(
                                "Virus detected in %s: %s", filename, threat_name
                            )
                            return False, threat_name

                # If we can't extract the specific threat name
                logger.warning("Virus detected in %s: Unknown threat", filename)
                return False, "Unknown virus detected"

            elif process.returncode == 0:
                # File is clean
                return True, None

            else:
                # Some other error occurred
                logger.warning("ClamAV scan error for %s: %s", filename, stderr.strip())
                return False, f"Scan error: {stderr.strip()}"

        except TimeoutError:
            logger.warning("ClamAV scan timeout for %s", filename)
            return False, "Scan timeout"
        except Exception as e:
            logger.error("Antivirus scan failed for %s: %s", filename, e)
            return False, f"Scan error: {str(e)}"
        finally:
            # Clean up the temporary file
            with contextlib.suppress(Exception):
                Path(temp_path).unlink()

    async def process_single_attachment(
        self, attachment_data: dict[str, Any], email_data: dict[str, Any]
    ) -> ProcessingResult:
        """
        Process a single email attachment through Phase 1 pipeline.

        Args:
            attachment_data: Dict with 'filename' and 'content' keys
            email_data: Dict with email metadata

        Returns:
            ProcessingResult with status and metadata
        """
        filename = attachment_data.get("filename", "unknown_attachment")
        content = attachment_data.get("content", b"")

        logger.info("Processing attachment %s", filename)

        try:
            # Step 1: Basic content validation
            if not content:
                return ProcessingResult(
                    status=ProcessingStatus.ERROR,
                    error_message="No file content available",
                )

            # Step 2: CRITICAL SECURITY - Antivirus scan FIRST
            # Scan for viruses regardless of file type to catch threats
            is_clean, threat_name = await self.scan_file_antivirus(content, filename)
            if not is_clean:
                logger.warning(
                    "🦠 VIRUS DETECTED - File quarantined %s: %s", filename, threat_name
                )

                # Calculate hash for quarantined files for tracking
                file_hash = self.calculate_file_hash(content)

                return ProcessingResult(
                    status=ProcessingStatus.QUARANTINED,
                    file_hash=file_hash,
                    quarantine_reason=threat_name,
                )

            # Step 3: File type validation (after virus scan)
            if not self.validate_file_type(filename):
                logger.warning(
                    "Invalid file type for %s: %s", filename, Path(filename).suffix
                )
                return ProcessingResult(
                    status=ProcessingStatus.INVALID_TYPE,
                    error_message=f"File type {Path(filename).suffix} not allowed",
                )

            # Step 4: File size validation
            file_size = len(content)
            if not self.validate_file_size(file_size):
                logger.warning(
                    "File too large for %s: %.1f MB",
                    filename,
                    file_size / (1024 * 1024),
                )
                return ProcessingResult(
                    status=ProcessingStatus.INVALID_TYPE,
                    error_message=f"File size {file_size / (1024*1024):.1f} MB exceeds limit",
                )

            # Step 5: Calculate SHA256 hash (for clean, valid files)
            file_hash = self.calculate_file_hash(content)
            logger.debug("SHA256(%s) = %s", filename, file_hash[:16])

            # Step 6: Check for duplicates (Phase 2)
            duplicate_id = await self.check_duplicate(file_hash)
            if duplicate_id:
                logger.info(
                    "Duplicate detected for %s (original: %s)", filename, duplicate_id
                )
                return ProcessingResult(
                    status=ProcessingStatus.DUPLICATE,
                    file_hash=file_hash,
                    duplicate_of=duplicate_id,
                )

            logger.info("File %s passed all Phase 1 validation checks", filename)

            # Prepare metadata for future phases
            metadata = {
                "filename": filename,
                "file_size": file_size,
                "sender_email": email_data.get("sender_email"),
                "sender_name": email_data.get("sender_name"),
                "email_subject": email_data.get("subject"),
                "email_date": email_data.get("date"),
                "processing_date": datetime.now(UTC).isoformat(),
                "file_extension": Path(filename).suffix.lower(),
                "validation_passed": True,
            }

            return ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                file_hash=file_hash,
                confidence=1.0,  # Full confidence for validation
                metadata=metadata,
            )

        except Exception as e:
            logger.error("Processing error for %s: %s", filename, e)
            return ProcessingResult(status=ProcessingStatus.ERROR, error_message=str(e))

    def get_processing_stats(self) -> dict[str, Any]:
        """Get current processing statistics."""
        total = sum(self.stats.values())

        return {
            "total_processed": total,
            "successful": self.stats["processed"],
            "quarantined": self.stats["quarantined"],
            "duplicates": self.stats["duplicates"],
            "errors": self.stats["errors"],
            "success_rate": (
                (self.stats["processed"] / total * 100) if total > 0 else 0.0
            ),
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform agent health check."""
        health = {
            "clamscan_path": self.clamscan_path is not None,
            "base_path_writable": False,
            "asset_configs_loaded": True,
        }

        try:
            # Check file system
            test_file = self.base_assets_path / ".health_check"
            test_file.touch()
            test_file.unlink()
            health["base_path_writable"] = True
        except Exception:
            pass

        return health

    # ================================
    # PHASE 2: Asset & Sender Management
    # ================================

    async def initialize_collections(self) -> bool:
        """Initialize Qdrant collections for asset management."""
        if not self.qdrant:
            logger.warning(
                "Qdrant client not provided - skipping collection initialization"
            )
            return False

        try:
            # Assets collection with vector embeddings for semantic search
            if not await self._collection_exists(self.COLLECTIONS["assets"]):
                await self._create_collection(
                    self.COLLECTIONS["assets"],
                    vector_size=384,  # sentence-transformers dimension
                    description="Asset definitions with semantic embeddings",
                )
                logger.info("Created assets collection: %s", self.COLLECTIONS["assets"])

            # Asset-Sender mappings (no vectors needed)
            if not await self._collection_exists(
                self.COLLECTIONS["asset_sender_mappings"]
            ):
                await self._create_collection(
                    self.COLLECTIONS["asset_sender_mappings"],
                    vector_size=1,  # Minimal vector for Qdrant requirement
                    description="Many-to-many asset-sender relationships",
                )
                logger.info("Created asset-sender mappings collection")

            # Processed documents (no vectors needed)
            if not await self._collection_exists(
                self.COLLECTIONS["processed_documents"]
            ):
                await self._create_collection(
                    self.COLLECTIONS["processed_documents"],
                    vector_size=1,  # Minimal vector
                    description="Processed document metadata and file hashes",
                )
                logger.info("Created processed documents collection")

            # Unknown senders (no vectors needed)
            if not await self._collection_exists(self.COLLECTIONS["unknown_senders"]):
                await self._create_collection(
                    self.COLLECTIONS["unknown_senders"],
                    vector_size=1,  # Minimal vector
                    description="Unknown sender tracking and timeout management",
                )
                logger.info("Created unknown senders collection")

            logger.info("All Qdrant collections initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize Qdrant collections: %s", e)
            return False

    async def _collection_exists(self, collection_name: str) -> bool:
        """Check if a Qdrant collection exists."""
        try:
            collections = self.qdrant.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception:
            return False

    async def _create_collection(
        self, collection_name: str, vector_size: int, description: str
    ) -> None:
        """Create a Qdrant collection."""
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    @log_function()
    async def create_asset(
        self,
        deal_name: str,
        asset_name: str,
        asset_type: AssetType,
        identifiers: list[str] = None,
    ) -> str:
        """
        Create a new asset definition.

        Args:
            deal_name: Short name for the asset
            asset_name: Full descriptive name
            asset_type: Type of private market asset
            identifiers: Alternative names/identifiers

        Returns:
            Asset deal_id (UUID)
        """
        deal_id = str(uuid.uuid4())
        folder_path = f"./assets/{deal_id}_{deal_name.replace(' ', '_')}"

        asset = Asset(
            deal_id=deal_id,
            deal_name=deal_name,
            asset_name=asset_name,
            asset_type=asset_type,
            folder_path=folder_path,
            identifiers=identifiers or [],
            created_date=datetime.now(UTC),
            last_updated=datetime.now(UTC),
        )

        if self.qdrant:
            try:
                # Store asset in Qdrant (with dummy vector for now)
                dummy_vector = [0.0] * 384  # Will be replaced with semantic embeddings

                point = PointStruct(
                    id=deal_id,
                    vector=dummy_vector,
                    payload={
                        "deal_id": deal_id,
                        "deal_name": deal_name,
                        "asset_name": asset_name,
                        "asset_type": asset_type.value,
                        "folder_path": folder_path,
                        "identifiers": identifiers or [],
                        "created_date": asset.created_date.isoformat(),
                        "last_updated": asset.last_updated.isoformat(),
                    },
                )

                self.qdrant.upsert(
                    collection_name=self.COLLECTIONS["assets"], points=[point]
                )

                logger.info("Created asset: %s (%s)", deal_name, deal_id)

            except Exception as e:
                logger.error("Failed to store asset in Qdrant: %s", e)

        # Create folder structure
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        return deal_id

    async def get_asset(self, deal_id: str) -> Asset | None:
        """Retrieve asset by deal_id."""
        if not self.qdrant:
            return None

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["assets"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="deal_id", match=MatchValue(value=deal_id))
                    ]
                ),
                limit=1,
            )

            if search_result[0]:
                payload = search_result[0][0].payload

                # Safely parse datetime fields with fallback
                def safe_parse_datetime(date_str: str) -> datetime:
                    try:
                        return datetime.fromisoformat(date_str)
                    except (ValueError, TypeError):
                        # Fallback to current time if parsing fails
                        logger.warning(
                            f"Failed to parse datetime '{date_str}', using current time"
                        )
                        return datetime.now(UTC)

                return Asset(
                    deal_id=payload["deal_id"],
                    deal_name=payload["deal_name"],
                    asset_name=payload["asset_name"],
                    asset_type=AssetType(payload["asset_type"]),
                    folder_path=payload["folder_path"],
                    identifiers=payload["identifiers"],
                    created_date=safe_parse_datetime(payload["created_date"]),
                    last_updated=safe_parse_datetime(payload["last_updated"]),
                )

            return None

        except Exception as e:
            logger.error("Failed to retrieve asset: %s", e)
            return None

    async def list_assets(self) -> list[Asset]:
        """List all assets."""
        assets = []

        if not self.qdrant:
            return assets

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["assets"],
                limit=100,  # Adjust as needed
            )

            # Safe datetime parsing function
            def safe_parse_datetime(date_str: str) -> datetime:
                try:
                    return datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    # Fallback to current time if parsing fails
                    logger.warning(
                        f"Failed to parse datetime '{date_str}', using current time"
                    )
                    return datetime.now(UTC)

            for point in search_result[0]:
                payload = point.payload
                asset = Asset(
                    deal_id=payload["deal_id"],
                    deal_name=payload["deal_name"],
                    asset_name=payload["asset_name"],
                    asset_type=AssetType(payload["asset_type"]),
                    folder_path=payload["folder_path"],
                    identifiers=payload["identifiers"],
                    created_date=safe_parse_datetime(payload["created_date"]),
                    last_updated=safe_parse_datetime(payload["last_updated"]),
                )
                assets.append(asset)

        except Exception as e:
            logger.error("Failed to list assets: %s", e)

        return assets

    async def update_asset(
        self,
        deal_id: str,
        deal_name: str | None = None,
        asset_name: str | None = None,
        asset_type: AssetType | None = None,
        identifiers: list[str] | None = None,
    ) -> bool:
        """
        Update an existing asset definition.

        Args:
            deal_id: Asset deal_id to update
            deal_name: New short name for the asset (optional)
            asset_name: New full descriptive name (optional)
            asset_type: New asset type (optional)
            identifiers: New alternative names/identifiers (optional)

        Returns:
            True if update successful, False otherwise
        """
        if not self.qdrant:
            logger.error("Qdrant client not available for asset update")
            return False

        try:
            # First, get the current asset
            current_asset = await self.get_asset(deal_id)
            if not current_asset:
                logger.error("Asset not found for update: %s", deal_id)
                return False

            # Update only the fields that were provided
            updated_deal_name = (
                deal_name if deal_name is not None else current_asset.deal_name
            )
            updated_asset_name = (
                asset_name if asset_name is not None else current_asset.asset_name
            )
            updated_asset_type = (
                asset_type if asset_type is not None else current_asset.asset_type
            )
            updated_identifiers = (
                identifiers if identifiers is not None else current_asset.identifiers
            )

            # Clean up identifiers - remove quotes if they exist
            if updated_identifiers:
                cleaned_identifiers = []
                for identifier in updated_identifiers:
                    # Remove surrounding quotes if they exist
                    cleaned = identifier.strip()
                    if (
                        cleaned.startswith('"')
                        and cleaned.endswith('"')
                        or cleaned.startswith("'")
                        and cleaned.endswith("'")
                    ):
                        cleaned = cleaned[1:-1]
                    cleaned_identifiers.append(cleaned)
                updated_identifiers = cleaned_identifiers

            # Update folder path if deal name changed
            updated_folder_path = current_asset.folder_path
            if deal_name is not None and deal_name != current_asset.deal_name:
                updated_folder_path = (
                    f"./assets/{deal_id}_{updated_deal_name.replace(' ', '_')}"
                )

            # Create updated asset object
            updated_asset = Asset(
                deal_id=deal_id,
                deal_name=updated_deal_name,
                asset_name=updated_asset_name,
                asset_type=updated_asset_type,
                folder_path=updated_folder_path,
                identifiers=updated_identifiers,
                created_date=current_asset.created_date,
                last_updated=datetime.now(UTC),
            )

            # Update in Qdrant
            dummy_vector = [0.0] * 384  # Will be replaced with semantic embeddings

            point = PointStruct(
                id=deal_id,
                vector=dummy_vector,
                payload={
                    "deal_id": deal_id,
                    "deal_name": updated_deal_name,
                    "asset_name": updated_asset_name,
                    "asset_type": updated_asset_type.value,
                    "folder_path": updated_folder_path,
                    "identifiers": updated_identifiers,
                    "created_date": current_asset.created_date.isoformat(),
                    "last_updated": updated_asset.last_updated.isoformat(),
                },
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["assets"], points=[point]
            )

            # Rename folder if deal name changed
            if updated_folder_path != current_asset.folder_path:
                old_path = Path(current_asset.folder_path)
                new_path = Path(updated_folder_path)
                if old_path.exists():
                    try:
                        old_path.rename(new_path)
                        logger.info("Renamed asset folder: %s → %s", old_path, new_path)
                    except OSError as e:
                        logger.warning("Failed to rename asset folder: %s", e)
                        # Create new folder if rename failed
                        new_path.mkdir(parents=True, exist_ok=True)

            logger.info("Updated asset: %s (%s)", updated_deal_name, deal_id)
            return True

        except Exception as e:
            logger.error("Failed to update asset %s: %s", deal_id, e)
            return False

    async def create_asset_sender_mapping(
        self,
        asset_id: str,
        sender_email: str,
        confidence: float,
        document_types: list[str] = None,
    ) -> str:
        """
        Create asset-sender mapping.

        Args:
            asset_id: Asset deal_id
            sender_email: Email address of sender
            confidence: Confidence level (0.0 to 1.0)
            document_types: Expected document categories

        Returns:
            Mapping ID (UUID)
        """
        mapping_id = str(uuid.uuid4())

        mapping = AssetSenderMapping(
            mapping_id=mapping_id,
            asset_id=asset_id,
            sender_email=sender_email.lower(),
            confidence=confidence,
            document_types=document_types or [],
            created_date=datetime.now(UTC),
            last_activity=datetime.now(UTC),
        )

        if self.qdrant:
            try:
                # Store mapping in Qdrant
                dummy_vector = [0.0]  # Minimal vector

                point = PointStruct(
                    id=mapping_id,
                    vector=dummy_vector,
                    payload={
                        "mapping_id": mapping_id,
                        "asset_id": asset_id,
                        "sender_email": sender_email.lower(),
                        "confidence": confidence,
                        "document_types": document_types or [],
                        "created_date": mapping.created_date.isoformat(),
                        "last_activity": mapping.last_activity.isoformat(),
                        "email_count": 0,
                    },
                )

                self.qdrant.upsert(
                    collection_name=self.COLLECTIONS["asset_sender_mappings"],
                    points=[point],
                )

                logger.info(
                    "Created asset-sender mapping: %s → %s", sender_email, asset_id
                )

            except Exception as e:
                logger.error("Failed to store mapping in Qdrant: %s", e)

        return mapping_id

    async def update_asset_sender_mapping(
        self,
        mapping_id: str,
        asset_id: str | None = None,
        sender_email: str | None = None,
        confidence: float | None = None,
        document_types: list[str] | None = None,
    ) -> bool:
        """
        Update an existing asset-sender mapping.

        Args:
            mapping_id: Mapping ID to update
            asset_id: New asset deal_id (optional)
            sender_email: New email address (optional)
            confidence: New confidence level (optional)
            document_types: New document types (optional)

        Returns:
            True if update successful, False otherwise
        """
        if not self.qdrant:
            logger.error("Qdrant client not available for mapping update")
            return False

        try:
            # First, get the current mapping
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="mapping_id", match=MatchValue(value=mapping_id)
                        )
                    ]
                ),
                limit=1,
            )

            if not search_result[0]:
                logger.error("Sender mapping not found for update: %s", mapping_id)
                return False

            current_mapping = search_result[0][0].payload

            # Update only the fields that were provided
            updated_asset_id = (
                asset_id if asset_id is not None else current_mapping["asset_id"]
            )
            updated_sender_email = (
                sender_email.lower()
                if sender_email is not None
                else current_mapping["sender_email"]
            )
            updated_confidence = (
                confidence if confidence is not None else current_mapping["confidence"]
            )
            updated_document_types = (
                document_types
                if document_types is not None
                else current_mapping.get("document_types", [])
            )

            # Update in Qdrant
            dummy_vector = [0.0]  # Minimal vector

            point = PointStruct(
                id=mapping_id,
                vector=dummy_vector,
                payload={
                    "mapping_id": mapping_id,
                    "asset_id": updated_asset_id,
                    "sender_email": updated_sender_email,
                    "confidence": updated_confidence,
                    "document_types": updated_document_types,
                    "created_date": current_mapping["created_date"],
                    "last_activity": datetime.now(UTC).isoformat(),
                    "email_count": current_mapping.get("email_count", 0),
                },
            )

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                points=[point],
            )

            logger.info(
                "Updated asset-sender mapping: %s (%s -> %s)",
                mapping_id[:8],
                updated_sender_email,
                updated_asset_id,
            )
            return True

        except Exception as e:
            logger.error("Failed to update sender mapping %s: %s", mapping_id, e)
            return False

    async def get_sender_assets(self, sender_email: str) -> list[dict[str, Any]]:
        """Get all assets associated with a sender."""
        self.logger.info(f"👤 SENDER KNOWLEDGE CHECK: '{sender_email}'")

        assets: list[dict[str, Any]] = []

        if not self.qdrant:
            self.logger.warning(
                "❌ Qdrant client not available - cannot check sender mappings"
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

            if search_result[0]:  # Points found
                points_found: int = len(search_result[0])
                self.logger.info(f"🔍 Found {points_found} sender mapping(s) in Qdrant")

                for point in search_result[0]:
                    mapping_data: dict[str, Any] = {
                        "asset_id": point.payload.get("asset_id"),
                        "confidence": point.payload.get("confidence", 0.0),
                        "created_at": point.payload.get("created_at"),
                        "point_id": point.id,
                    }
                    assets.append(mapping_data)
                    self.logger.debug(
                        f"   📋 Mapping: {mapping_data['asset_id']} (confidence: {mapping_data['confidence']:.3f})"
                    )
            else:
                self.logger.info("❌ No sender mappings found for this email address")

        except Exception as e:
            self.logger.error(f"❌ Error checking sender mappings: {e}")
            # Don't re-raise - gracefully degrade

        total_assets: int = len(assets)
        if total_assets > 0:
            self.logger.info(
                f"✅ SENDER KNOWLEDGE RESULT: {total_assets} associated asset(s)"
            )
            # Show top 3 for logging
            for i, asset_data in enumerate(assets[:3]):
                self.logger.info(
                    f"   {i+1}. Asset: {asset_data['asset_id']} -> confidence: {asset_data['confidence']:.3f}"
                )
        else:
            self.logger.info(
                "❓ SENDER KNOWLEDGE RESULT: Unknown sender - no associated assets"
            )

        return assets

    async def list_asset_sender_mappings(self) -> list[dict[str, Any]]:
        """List all asset-sender mappings."""
        mappings = []

        if not self.qdrant:
            return mappings

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"], limit=100
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

        except Exception as e:
            logger.error("Failed to list sender mappings: %s", e)

        return mappings

    async def delete_asset_sender_mapping(self, mapping_id: str) -> bool:
        """Delete an asset-sender mapping by mapping_id."""
        if not self.qdrant:
            logger.error("Qdrant client not available for deletion")
            return False

        logger.info("Attempting to delete sender mapping: %s", mapping_id)

        try:
            # First verify the mapping exists
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="mapping_id", match=MatchValue(value=mapping_id)
                        )
                    ]
                ),
                limit=1,
            )

            if not search_result[0]:
                logger.error("Sender mapping not found in database: %s", mapping_id)
                return False

            logger.debug("Found mapping to delete: %s", mapping_id)

            # Delete by point ID (which should be the mapping_id)
            delete_result = self.qdrant.delete(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                points_selector=PointIdsList(points=[mapping_id]),
            )

            logger.info("Delete operation completed for mapping: %s", mapping_id)
            logger.debug("Delete result: %s", delete_result)

            # Verify deletion
            verify_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["asset_sender_mappings"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="mapping_id", match=MatchValue(value=mapping_id)
                        )
                    ]
                ),
                limit=1,
            )

            if not verify_result[0]:
                logger.info(
                    "Confirmed: Sender mapping successfully deleted: %s", mapping_id
                )
                return True
            else:
                logger.error(
                    "Deletion verification failed - mapping still exists: %s",
                    mapping_id,
                )
                return False

        except Exception as e:
            logger.error("Failed to delete sender mapping %s: %s", mapping_id, e)
            # # Standard library imports
            import traceback

            logger.error("Full error traceback: %s", traceback.format_exc())
            return False

    async def check_duplicate(self, file_hash: str) -> str | None:
        """
        Check if file hash already exists in processed documents.

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

            if search_result[0]:  # Found duplicate
                return search_result[0][0].payload.get("document_id")

            return None

        except Exception as e:
            logger.warning("Error checking for duplicates: %s", e)
            return None

    async def store_processed_document(
        self, file_hash: str, processing_result: ProcessingResult, asset_id: str = None
    ) -> str:
        """Store processed document metadata."""
        document_id = str(uuid.uuid4())

        if not self.qdrant:
            return document_id

        try:
            dummy_vector = [0.0]  # Minimal vector

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

            point = PointStruct(id=document_id, vector=dummy_vector, payload=payload)

            self.qdrant.upsert(
                collection_name=self.COLLECTIONS["processed_documents"], points=[point]
            )

            logger.info("📊 Document metadata stored: %s...", document_id[:8])

            return document_id

        except Exception as e:
            logger.error("Failed to store processed document: %s", e)
            return None

    async def get_processed_document(self, document_id: str) -> dict[str, Any] | None:
        """
        Retrieve processed document metadata by document ID.

        Args:
            document_id: Document ID to retrieve

        Returns:
            Document metadata dictionary if found, None otherwise
        """
        if not self.qdrant:
            return None

        try:
            search_result = self.qdrant.scroll(
                collection_name=self.COLLECTIONS["processed_documents"],
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1,
            )

            if search_result[0]:
                return search_result[0][0].payload

            return None

        except Exception as e:
            logger.error("Failed to retrieve processed document %s: %s", document_id, e)
            return None

    # ================================
    # PHASE 3: Document Classification
    # ================================

    # Document classification patterns by asset type
    CLASSIFICATION_PATTERNS = {
        AssetType.COMMERCIAL_REAL_ESTATE: {
            DocumentCategory.RENT_ROLL: [
                r"rent.*roll",
                r"rental.*income",
                r"tenant.*list",
                r"occupancy.*report",
                r"lease.*schedule",
                r"rental.*schedule",
            ],
            DocumentCategory.FINANCIAL_STATEMENTS: [
                r"financial.*statement",
                r"income.*statement",
                r"balance.*sheet",
                r"cash.*flow",
                r"profit.*loss",
                r"p.*l.*statement",
            ],
            DocumentCategory.PROPERTY_PHOTOS: [
                r"photo",
                r"image",
                r"picture",
                r"exterior",
                r"interior",
                r"amenity",
            ],
            DocumentCategory.APPRAISAL: [
                r"appraisal",
                r"valuation",
                r"market.*value",
                r"property.*value",
            ],
            DocumentCategory.LEASE_DOCUMENTS: [
                r"lease.*agreement",
                r"lease.*contract",
                r"tenancy.*agreement",
                r"rental.*agreement",
                r"lease.*amendment",
            ],
            DocumentCategory.PROPERTY_MANAGEMENT: [
                r"management.*report",
                r"maintenance.*report",
                r"inspection.*report",
                r"property.*condition",
                r"capex",
                r"capital.*expenditure",
            ],
        },
        AssetType.PRIVATE_CREDIT: {
            DocumentCategory.LOAN_DOCUMENTS: [
                r"loan.*agreement",
                r"credit.*agreement",
                r"facility.*agreement",
                r"promissory.*note",
                r"security.*agreement",
                r"loan.*documents?",  # NEW: "loan document" or "loan documents"
                r"loan.*docs?",  # NEW: "loan doc" or "loan docs"
                r"loan.*papers?",  # NEW: "loan paper" or "loan papers"
                r"loan.*file",  # NEW: "loan file"
                r"credit.*document",  # NEW: "credit document"
                r".*loan.*td.*",  # NEW: Trust Deed/Term Document patterns
                r"trust.*deed",  # NEW: "trust deed"
                r"term.*document",  # NEW: "term document"
            ],
            DocumentCategory.BORROWER_FINANCIALS: [
                r"borrower.*financial",
                r"financial.*statement",
                r"credit.*memo",
                r"financial.*performance",
                r"quarterly.*report",
            ],
            DocumentCategory.COVENANT_COMPLIANCE: [
                r"covenant.*compliance",
                r"compliance.*certificate",
                r"covenant.*test",
                r"financial.*covenant",
                r"compliance.*report",
            ],
            DocumentCategory.CREDIT_MEMO: [
                r"credit.*memo",
                r"investment.*memo",
                r"credit.*analysis",
                r"risk.*assessment",
                r"underwriting.*memo",
            ],
            DocumentCategory.LOAN_MONITORING: [
                r"monitoring.*report",
                r"portfolio.*report",
                r"loan.*performance",
                r"payment.*history",
                r"default.*report",
            ],
        },
        AssetType.PRIVATE_EQUITY: {
            DocumentCategory.PORTFOLIO_REPORTS: [
                r"portfolio.*report",
                r"portfolio.*update",
                r"company.*update",
                r"performance.*report",
                r"investment.*update",
            ],
            DocumentCategory.INVESTOR_UPDATES: [
                r"investor.*update",
                r"investor.*letter",
                r"quarterly.*update",
                r"annual.*report",
                r"fund.*update",
            ],
            DocumentCategory.BOARD_MATERIALS: [
                r"board.*material",
                r"board.*deck",
                r"board.*presentation",
                r"board.*meeting",
                r"director.*report",
            ],
            DocumentCategory.DEAL_DOCUMENTS: [
                r"purchase.*agreement",
                r"merger.*agreement",
                r"acquisition",
                r"transaction.*document",
                r"closing.*document",
            ],
            DocumentCategory.VALUATION_REPORTS: [
                r"valuation.*report",
                r"valuation.*analysis",
                r"fair.*value",
                r"mark.*to.*market",
                r"portfolio.*valuation",
            ],
        },
        AssetType.INFRASTRUCTURE: {
            DocumentCategory.ENGINEERING_REPORTS: [
                r"engineering.*report",
                r"technical.*report",
                r"design.*document",
                r"structural.*report",
                r"environmental.*study",
            ],
            DocumentCategory.CONSTRUCTION_UPDATES: [
                r"construction.*update",
                r"progress.*report",
                r"milestone.*report",
                r"construction.*status",
                r"build.*progress",
            ],
            DocumentCategory.REGULATORY_DOCUMENTS: [
                r"permit",
                r"license",
                r"regulatory.*approval",
                r"compliance.*document",
                r"environmental.*clearance",
                r"zoning.*approval",
            ],
            DocumentCategory.OPERATIONS_REPORTS: [
                r"operations.*report",
                r"performance.*metrics",
                r"utilization.*report",
                r"maintenance.*log",
                r"operations.*update",
            ],
        },
    }

    # Asset name patterns for fuzzy matching
    ASSET_KEYWORDS = {
        "commercial_real_estate": [
            "property",
            "building",
            "office",
            "retail",
            "warehouse",
            "industrial",
            "commercial",
            "plaza",
            "center",
            "tower",
            "complex",
            "development",
        ],
        "private_credit": [
            "loan",
            "credit",
            "facility",
            "debt",
            "financing",
            "bridge",
            "term",
            "revolving",
            "senior",
            "subordinate",
            "mezzanine",
        ],
        "private_equity": [
            "equity",
            "investment",
            "portfolio",
            "fund",
            "acquisition",
            "buyout",
            "growth",
            "venture",
            "capital",
            "holdings",
        ],
        "infrastructure": [
            "infrastructure",
            "utility",
            "energy",
            "transportation",
            "telecom",
            "power",
            "water",
            "gas",
            "pipeline",
            "renewable",
            "solar",
            "wind",
        ],
    }

    @log_function()
    async def classify_document(
        self,
        filename: str,
        email_subject: str,
        email_body: str = "",
        asset_type: AssetType | None = None,
        sender_email: str = "",
    ) -> tuple[DocumentCategory, float]:
        """
        Classify document using pattern matching and episodic memory.

        Args:
            filename: Name of the document file
            email_subject: Subject line of the email
            email_body: Body content of the email
            asset_type: Known asset type for targeted classification
            sender_email: Email address of sender for episodic memory lookup

        Returns:
            Tuple of (DocumentCategory, confidence_score)
        """
        self.logger.info("📋 DOCUMENT CLASSIFICATION ANALYSIS START")
        self.logger.info(f"📄 Filename: '{filename}'")
        self.logger.info(f"📧 Email Subject: '{email_subject}'")
        self.logger.info(
            f"📝 Email Body: '{email_body[:100]}{'...' if len(email_body) > 100 else ''}'"
        )
        self.logger.info(
            f"🏢 Asset Type Context: {asset_type.value if asset_type else 'None'}"
        )
        self.logger.info(f"👤 Sender: '{sender_email}'")

        combined_text: str = f"{filename} {email_subject} {email_body}".lower()
        self.logger.info(f"🔤 Combined classification text: '{combined_text}'")

        # Step 1: Try episodic memory classification first
        self.logger.info("🧠 Step 1: Checking episodic memory for patterns...")
        (
            episodic_category,
            episodic_confidence,
        ) = await self._classify_from_episodic_memory(
            filename, email_subject, email_body, sender_email
        )

        if episodic_confidence > 0.5:
            self.logger.info(
                f"✅ EPISODIC MEMORY CLASSIFICATION: {episodic_category.value} (confidence: {episodic_confidence:.3f})"
            )
            self.logger.info("🏁 DOCUMENT CLASSIFICATION COMPLETE (episodic memory)")
            return episodic_category, episodic_confidence
        else:
            self.logger.info(
                f"❌ Episodic memory classification insufficient: {episodic_category.value} (confidence: {episodic_confidence:.3f})"
            )

        # Step 2: Pattern-based classification
        self.logger.info("🔍 Step 2: Performing pattern-based classification...")

        best_category: DocumentCategory = DocumentCategory.UNKNOWN
        best_confidence: float = 0.0

        # If we have asset type context, focus on those patterns first
        if asset_type and asset_type in self.CLASSIFICATION_PATTERNS:
            self.logger.info(f"🎯 Focusing on {asset_type.value} document patterns")
            patterns_to_check: dict[AssetType, dict[DocumentCategory, list[str]]] = {
                asset_type: self.CLASSIFICATION_PATTERNS[asset_type]
            }
        else:
            self.logger.info("🌐 Checking all asset type patterns")
            patterns_to_check = self.CLASSIFICATION_PATTERNS

        for checking_asset_type, categories in patterns_to_check.items():
            self.logger.debug(f"📊 Checking {checking_asset_type.value} patterns...")

            for category, patterns in categories.items():
                category_confidence: float = 0.0
                matches_found: list[str] = []

                self.logger.debug(f"   🔍 Testing category: {category.value}")
                self.logger.debug(f"   📝 Patterns: {patterns}")

                for pattern in patterns:
                    try:
                        if re.search(pattern, combined_text, re.IGNORECASE):
                            # Weight longer, more specific patterns higher
                            pattern_weight: float = min(len(pattern) / 20.0, 1.0)
                            category_confidence += pattern_weight
                            matches_found.append(pattern)
                            self.logger.debug(
                                f"     ✅ Pattern match: '{pattern}' -> weight: {pattern_weight:.3f}"
                            )
                    except re.error as e:
                        self.logger.warning(f"Invalid regex pattern '{pattern}': {e}")

                # Normalize confidence (cap at 1.0)
                category_confidence = min(category_confidence, 1.0)

                if matches_found:
                    self.logger.info(
                        f"   🎯 Category {category.value}: {len(matches_found)} pattern(s) matched -> confidence: {category_confidence:.3f}"
                    )
                    for match in matches_found:
                        self.logger.debug(f"     - '{match}'")
                else:
                    self.logger.debug(
                        f"   ❌ Category {category.value}: no patterns matched"
                    )

                if category_confidence > best_confidence:
                    old_best: str = f"{best_category.value} ({best_confidence:.3f})"
                    best_category = category
                    best_confidence = category_confidence
                    self.logger.info(
                        f"   🏆 NEW BEST: {category.value} ({category_confidence:.3f}) - was {old_best}"
                    )

        # Step 3: Apply confidence adjustments
        self.logger.info("⚖️ Step 3: Applying confidence adjustments...")

        # Filename-specific boosts
        filename_lower: str = filename.lower()
        original_confidence: float = best_confidence

        if any(
            keyword in filename_lower for keyword in ["report", "statement", "summary"]
        ):
            boost: float = 0.1
            best_confidence = min(best_confidence + boost, 1.0)
            self.logger.info(
                f"   📄 Filename keyword boost: +{boost} -> {best_confidence:.3f}"
            )

        if filename_lower.endswith((".pdf", ".doc", ".docx")):
            boost = 0.05
            best_confidence = min(best_confidence + boost, 1.0)
            self.logger.info(
                f"   📎 Document format boost: +{boost} -> {best_confidence:.3f}"
            )

        # Email subject relevance
        if (
            email_subject
            and len(email_subject) > 10
            and any(
                keyword in email_subject.lower()
                for keyword in ["urgent", "important", "quarterly", "monthly"]
            )
        ):
            boost = 0.05
            best_confidence = min(best_confidence + boost, 1.0)
            self.logger.info(
                f"   📧 Subject relevance boost: +{boost} -> {best_confidence:.3f}"
            )

        if best_confidence != original_confidence:
            self.logger.info(
                f"   📈 Total confidence adjustment: {original_confidence:.3f} -> {best_confidence:.3f}"
            )

        # Final result
        self.logger.info("🏁 DOCUMENT CLASSIFICATION COMPLETE (pattern-based)")
        self.logger.info(f"📋 Final Classification: {best_category.value}")
        self.logger.info(f"📊 Final Confidence: {best_confidence:.3f}")

        if best_confidence < 0.3:
            self.logger.warning(
                "⚠️ Low classification confidence - document may need human review"
            )
        elif best_confidence > 0.8:
            self.logger.info("✨ High classification confidence - reliable result")

        return best_category, best_confidence

    async def _classify_from_episodic_memory(
        self, filename: str, email_subject: str, email_body: str, sender_email: str
    ) -> tuple[DocumentCategory, float]:
        """
        Attempt document classification using episodic memory.

        Args:
            filename: Document filename
            email_subject: Email subject line
            email_body: Email body content
            sender_email: Sender's email address

        Returns:
            Tuple of (DocumentCategory, confidence_score)
        """
        self.logger.info("🧠 EPISODIC MEMORY CLASSIFICATION START")
        self.logger.info(f"📄 Filename: '{filename}'")
        self.logger.info(f"📧 Subject: '{email_subject}'")
        self.logger.info(f"👤 Sender: '{sender_email}'")

        try:
            from ..memory.episodic import EpisodicMemory

            # Check if episodic memory is available
            episodic_memory: EpisodicMemory = EpisodicMemory()

            # Get collection info to see what's available
            try:
                collection_info: dict[
                    str, Any
                ] = await episodic_memory.get_collection_info()
                self.logger.info(
                    f"📊 Episodic memory collection: {collection_info.get('points_count', 0)} memories available"
                )
            except Exception as e:
                self.logger.warning(
                    f"Cannot access episodic memory collection info: {e}"
                )
                self.logger.info("🔍 Proceeding with memory search anyway...")

            search_text: str = (
                f"filename:{filename} subject:{email_subject} sender:{sender_email}"
            )
            self.logger.info(f"🔍 Episodic memory search query: '{search_text}'")

            # Search for similar classification patterns
            memories: list[Any] = await episodic_memory.search(
                query=search_text, limit=5
            )

            self.logger.info(f"📋 Found {len(memories)} relevant memories")

            if not memories:
                self.logger.info("❌ No relevant episodic memories found")
                return DocumentCategory.UNKNOWN, 0.0

            # Analyze memories for classification patterns
            category_votes: dict[DocumentCategory, float] = {}
            total_relevance: float = 0.0

            for i, memory in enumerate(memories):
                self.logger.debug(f"🔍 Memory {i+1}: ID {memory.memory_id}")
                self.logger.debug(f"   📊 Similarity: {memory.similarity:.3f}")

                metadata: Any = memory.metadata

                # Extract classification from memory
                doc_category: DocumentCategory | None = None
                memory_relevance: float = 0.0

                # Check for document type in metadata
                if isinstance(metadata, dict):
                    if "document_category" in metadata:
                        try:
                            doc_category = DocumentCategory(
                                metadata["document_category"]
                            )
                            memory_relevance += 0.5
                            self.logger.debug(
                                f"   📋 Found document_category in metadata: {doc_category.value}"
                            )
                        except ValueError:
                            self.logger.debug(
                                f"   ⚠️ Invalid document_category in metadata: {metadata['document_category']}"
                            )

                    # Check for correction type
                    if metadata.get("feedback_type") == "correction":
                        memory_relevance += 0.3
                        self.logger.debug(
                            "   ✅ Memory is from human correction -> +0.3 relevance"
                        )

                # Filename similarity boost
                memory_filename: str = (
                    metadata.get("filename", "") if isinstance(metadata, dict) else ""
                )
                if memory_filename and filename:
                    if memory_filename.lower() == filename.lower():
                        memory_relevance += 0.4
                        self.logger.debug("   📄 Exact filename match -> +0.4 relevance")
                    elif any(
                        word in filename.lower()
                        for word in memory_filename.lower().split()
                        if len(word) > 3
                    ):
                        memory_relevance += 0.2
                        self.logger.debug(
                            "   📄 Partial filename match -> +0.2 relevance"
                        )

                # Sender domain similarity
                memory_domain: str = (
                    metadata.get("sender_domain", "")
                    if isinstance(metadata, dict)
                    else ""
                )
                sender_domain: str = (
                    sender_email.split("@")[1] if "@" in sender_email else ""
                )

                if memory_domain and sender_domain:
                    if memory_domain.lower() == sender_domain.lower():
                        memory_relevance += 0.4  # Strong domain match
                        self.logger.debug(
                            f"   🌐 Exact domain match ({sender_domain}) -> +0.4 relevance"
                        )
                    elif any(
                        part in sender_domain.lower()
                        for part in memory_domain.lower().split(".")
                        if len(part) > 3
                    ):
                        memory_relevance += 0.2  # Partial domain match
                        self.logger.debug("   🌐 Partial domain match -> +0.2 relevance")

                # Apply similarity weighting
                weighted_relevance: float = memory_relevance * memory.similarity
                self.logger.info(
                    f"   📊 Memory relevance: {memory_relevance:.3f} × similarity({memory.similarity:.3f}) = {weighted_relevance:.3f}"
                )

                if doc_category and weighted_relevance > 0.1:
                    if doc_category not in category_votes:
                        category_votes[doc_category] = 0.0
                    category_votes[doc_category] += weighted_relevance
                    total_relevance += weighted_relevance
                    self.logger.info(
                        f"   ✅ Vote for {doc_category.value}: +{weighted_relevance:.3f}"
                    )
                else:
                    self.logger.debug(
                        f"   ❌ Memory not useful: category={doc_category}, relevance={weighted_relevance:.3f}"
                    )

            # Determine best category
            if not category_votes:
                self.logger.info(
                    "❌ No useful classification votes from episodic memory"
                )
                return DocumentCategory.UNKNOWN, 0.0

            self.logger.info("🗳️ Episodic memory voting results:")
            for category, votes in sorted(
                category_votes.items(), key=lambda x: x[1], reverse=True
            ):
                percentage: float = (
                    (votes / total_relevance) * 100 if total_relevance > 0 else 0
                )
                self.logger.info(
                    f"   {category.value}: {votes:.3f} ({percentage:.1f}%)"
                )

            # Get the category with the most votes
            best_category: DocumentCategory = max(
                category_votes.keys(), key=lambda x: category_votes[x]
            )
            best_confidence: float = category_votes[best_category]

            # Normalize confidence based on total relevance and number of memories
            num_matches: int = len([m for m in memories if m.similarity > 0.5])
            normalized_confidence: float = min(
                best_confidence / max(total_relevance, 1.0), 1.0
            )

            # Boost confidence if multiple high-quality memories agree
            if num_matches > 1:
                normalized_confidence = min(normalized_confidence * 1.2, 1.0)
                self.logger.info(
                    f"   🚀 Multiple memory boost: {num_matches} memories -> +20% confidence"
                )

            self.logger.info(f"🏆 EPISODIC MEMORY RESULT: {best_category.value}")
            self.logger.info(
                f"📊 Raw confidence: {best_confidence:.3f}, Normalized: {normalized_confidence:.3f}"
            )

            self.logger.info(
                f"Episodic memory classification: {best_category.value} "
                f"(confidence: {normalized_confidence:.2f}, {num_matches} patterns matched)"
            )

            return best_category, normalized_confidence

        except Exception as e:
            self.logger.warning(f"Failed to classify from episodic memory: {e}")
            self.logger.debug(f"Episodic memory error details: {e}", exc_info=True)
            return DocumentCategory.UNKNOWN, 0.0

    def identify_asset_from_content(
        self,
        email_subject: str,
        email_body: str = "",
        filename: str = "",
        known_assets: list[Asset] | None = None,
    ) -> list[tuple[str, float]]:
        """
        Identify potential assets mentioned in email content using fuzzy matching.

        Args:
            email_subject: Email subject line
            email_body: Email body content
            filename: Attachment filename
            known_assets: List of known assets to match against

        Returns:
            List of (asset_id, confidence_score) tuples, sorted by confidence
        """
        self.logger.info("🔍 ASSET MATCHING ANALYSIS START")
        self.logger.info(f"📧 Email Subject: '{email_subject}'")
        self.logger.info(f"📄 Filename: '{filename}'")
        self.logger.info(
            f"📝 Email Body: '{email_body[:100]}{'...' if len(email_body) > 100 else ''}'"
        )

        if not known_assets or not levenshtein_distance:
            self.logger.info(
                "❌ No assets available or Levenshtein not loaded - returning empty matches"
            )
            return []

        # Combine text for analysis
        combined_text: str = f"{email_subject} {email_body} {filename}".lower()
        self.logger.info(f"🔤 Combined search text: '{combined_text}'")
        self.logger.info(f"📊 Analyzing against {len(known_assets)} known assets")

        asset_matches: list[tuple[str, float]] = []

        for asset in known_assets:
            self.logger.debug(
                f"🏢 Checking asset: {asset.deal_name} (ID: {asset.deal_id})"
            )
            max_confidence: float = 0.0

            # Check all asset identifiers
            all_identifiers: list[str] = [
                asset.deal_name,
                asset.asset_name,
            ] + asset.identifiers
            self.logger.debug(f"   🏷️ Identifiers to check: {all_identifiers}")

            for identifier in all_identifiers:
                if not identifier:
                    continue

                identifier_lower: str = identifier.lower()
                self.logger.debug(f"   🔍 Testing identifier: '{identifier_lower}'")

                # Exact match (highest confidence)
                if identifier_lower in combined_text:
                    confidence: float = 0.95
                    max_confidence = max(max_confidence, confidence)
                    self.logger.info(
                        f"   ✅ EXACT MATCH: '{identifier_lower}' found in text -> confidence: {confidence}"
                    )
                    continue

                # Fuzzy matching with Levenshtein distance
                words: list[str] = combined_text.split()
                for word_group_size in [3, 2, 1]:  # Check phrases of different lengths
                    for i in range(len(words) - word_group_size + 1):
                        phrase: str = " ".join(words[i : i + word_group_size])

                        if len(phrase) < 3:  # Skip very short phrases
                            continue

                        # Calculate similarity
                        distance: int = levenshtein_distance(identifier_lower, phrase)
                        max_len: int = max(len(identifier_lower), len(phrase))

                        if max_len > 0:
                            similarity: float = 1 - (distance / max_len)

                            # Threshold for fuzzy matches
                            if similarity >= 0.8:
                                confidence = (
                                    similarity * 0.9
                                )  # Slightly lower than exact match
                                max_confidence = max(max_confidence, confidence)
                                self.logger.info(
                                    f"   🎯 FUZZY MATCH: '{identifier_lower}' ~= '{phrase}' (similarity: {similarity:.3f}) -> confidence: {confidence:.3f}"
                                )

            # Add partial word matching for specific keywords
            asset_type_keywords: list[str] = self.ASSET_KEYWORDS.get(
                asset.asset_type.value, []
            )
            if asset_type_keywords:
                self.logger.debug(
                    f"   🔑 Checking asset type keywords: {asset_type_keywords}"
                )
                keyword_matches: int = sum(
                    1 for keyword in asset_type_keywords if keyword in combined_text
                )

                if keyword_matches > 0:
                    keyword_boost: float = min(keyword_matches * 0.1, 0.3)
                    old_confidence: float = max_confidence
                    max_confidence = min(max_confidence + keyword_boost, 1.0)
                    self.logger.info(
                        f"   🚀 KEYWORD BOOST: {keyword_matches} keywords matched -> boost: +{keyword_boost:.3f} (confidence: {old_confidence:.3f} -> {max_confidence:.3f})"
                    )

            if max_confidence > 0.5:  # Only include reasonable matches
                asset_matches.append((asset.deal_id, max_confidence))
                self.logger.info(
                    f"   ⭐ ASSET QUALIFIED: {asset.deal_name} -> final confidence: {max_confidence:.3f}"
                )
            else:
                self.logger.debug(
                    f"   ❌ Asset rejected: {asset.deal_name} -> confidence too low: {max_confidence:.3f}"
                )

        # Sort by confidence (highest first)
        asset_matches.sort(key=lambda x: x[1], reverse=True)

        self.logger.info("🏁 ASSET MATCHING ANALYSIS COMPLETE")
        if asset_matches:
            self.logger.info(f"📈 Found {len(asset_matches)} qualifying asset matches:")
            for i, (asset_id, confidence) in enumerate(asset_matches[:3]):  # Show top 3
                asset: Asset | None = next(
                    (a for a in known_assets if a.deal_id == asset_id), None
                )
                asset_name: str = asset.deal_name if asset else "Unknown"
                self.logger.info(f"   {i+1}. {asset_name} -> {confidence:.3f}")
        else:
            self.logger.info("❌ No qualifying asset matches found")

        return asset_matches

    def determine_confidence_level(
        self, document_confidence: float, asset_confidence: float, sender_known: bool
    ) -> ConfidenceLevel:
        """
        Determine overall confidence level for routing decisions.

        Args:
            document_confidence: Confidence in document classification (0.0-1.0)
            asset_confidence: Confidence in asset identification (0.0-1.0)
            sender_known: Whether sender is in asset-sender mappings

        Returns:
            ConfidenceLevel for routing decision
        """
        self.logger.info("⚖️ OVERALL CONFIDENCE CALCULATION START")
        self.logger.info(
            f"📋 Document Classification Confidence: {document_confidence:.3f}"
        )
        self.logger.info(f"🏢 Asset Identification Confidence: {asset_confidence:.3f}")
        self.logger.info(f"👤 Known Sender Boost: {sender_known}")

        # Calculate composite confidence
        base_confidence: float = (document_confidence + asset_confidence) / 2
        self.logger.info(f"📊 Base Confidence (average): {base_confidence:.3f}")

        # Apply sender knowledge boost
        if sender_known:
            boost_amount: float = 0.1
            composite_confidence: float = min(base_confidence + boost_amount, 1.0)
            self.logger.info(
                f"🚀 Sender knowledge boost: +{boost_amount:.3f} -> {composite_confidence:.3f}"
            )
        else:
            composite_confidence = base_confidence
            self.logger.info("❌ No sender knowledge boost available")

        # Determine routing level
        # Use a derived high confidence threshold (e.g., 0.85)
        high_confidence_threshold = 0.85
        medium_confidence_threshold = config.low_confidence_threshold

        if composite_confidence >= high_confidence_threshold:
            result_level: ConfidenceLevel = ConfidenceLevel.HIGH
            self.logger.info(
                f"✅ HIGH CONFIDENCE: {composite_confidence:.3f} >= {high_confidence_threshold}"
            )
        elif composite_confidence >= medium_confidence_threshold:
            result_level = ConfidenceLevel.MEDIUM
            self.logger.info(
                f"⚠️ MEDIUM CONFIDENCE: {composite_confidence:.3f} >= {medium_confidence_threshold}"
            )
        else:
            result_level = ConfidenceLevel.LOW
            self.logger.info(
                f"❌ LOW CONFIDENCE: {composite_confidence:.3f} < {medium_confidence_threshold}"
            )

        # Routing implications
        if result_level == ConfidenceLevel.HIGH:
            self.logger.info("🎯 ROUTING: Direct to asset folder (automatic processing)")
        elif result_level == ConfidenceLevel.MEDIUM:
            self.logger.info("👀 ROUTING: Send for human review (medium confidence)")
        else:
            self.logger.info(
                "🔍 ROUTING: Send for human review (low confidence - requires attention)"
            )

        self.logger.info("🏁 OVERALL CONFIDENCE CALCULATION COMPLETE")
        self.logger.info(
            f"📊 Final Routing Decision: {result_level.value} ({composite_confidence:.3f})"
        )

        return result_level

    @log_function()
    async def enhanced_process_attachment(
        self, attachment_data: dict[str, Any], email_data: dict[str, Any]
    ) -> ProcessingResult:
        """
        Enhanced attachment processing with Phase 3 classification and intelligence.

        Args:
            attachment_data: Dict with 'filename' and 'content' keys
            email_data: Dict with email metadata

        Returns:
            ProcessingResult with classification and asset matching
        """
        # Start with Phase 1 & 2 processing
        result = await self.process_single_attachment(attachment_data, email_data)

        # Handle duplicates - return immediately without any processing
        if result.status == ProcessingStatus.DUPLICATE:
            self.logger.info(
                f"🔄 Duplicate detected: {attachment_data.get('filename', 'unknown')} - completely discarding"
            )
            return result

        # For non-SUCCESS status (except duplicates), return as-is
        if result.status != ProcessingStatus.SUCCESS:
            return result

        # Phase 3: Add document classification and asset identification
        filename = attachment_data.get("filename", "")
        email_subject = email_data.get("subject", "")
        email_body = email_data.get("body", "")
        sender_email = email_data.get("sender_email", "")

        self.logger.info("🧠 Phase 3: Analyzing content and identifying assets...")

        # Step 1: Asset Identification (do this first to get context for classification)
        known_assets = await self.list_assets()
        asset_matches = self.identify_asset_from_content(
            email_subject, email_body, filename, known_assets
        )

        matched_asset_id = None
        asset_confidence = 0.0
        potential_asset_type = None

        if asset_matches:
            matched_asset_id, asset_confidence = asset_matches[0]  # Best match
            asset = await self.get_asset(matched_asset_id)
            if asset:
                potential_asset_type = asset.asset_type
                asset_name = asset.deal_name
                self.logger.info(
                    "🎯 Best asset match: %s (confidence: %.2f)",
                    asset_name,
                    asset_confidence,
                )
                self.logger.debug(
                    f"Using asset type {potential_asset_type.value} for classification context"
                )
            else:
                self.logger.warning(f"Asset not found for ID: {matched_asset_id}")
        else:
            self.logger.info("❓ No asset matches found")

        # Step 2: Document Classification (using asset type context if available)
        document_category, doc_confidence = await self.classify_document(
            filename, email_subject, email_body, potential_asset_type, sender_email
        )

        self.logger.info(
            "📋 Document classified as: %s (confidence: %.2f)",
            document_category.value,
            doc_confidence,
        )

        # Step 3: Check if sender is known
        sender_assets = await self.get_sender_assets(sender_email)
        sender_known = len(sender_assets) > 0

        if sender_known:
            self.logger.info(
                "👤 Known sender: %d asset(s) associated", len(sender_assets)
            )
            # If sender has assets but we didn't match content, use sender's highest confidence asset
            if not matched_asset_id and sender_assets:
                best_sender_asset = max(sender_assets, key=lambda x: x["confidence"])
                matched_asset_id = best_sender_asset["asset_id"]
                asset_confidence = (
                    best_sender_asset["confidence"] * 0.8
                )  # Slightly reduce confidence
                self.logger.info(
                    "🔗 Using sender's primary asset: %s...", matched_asset_id[:8]
                )

                # Update asset type context if we got it from sender
                if not potential_asset_type:
                    sender_asset = await self.get_asset(matched_asset_id)
                    if sender_asset:
                        potential_asset_type = sender_asset.asset_type
                        # Re-classify with sender asset context
                        (
                            document_category,
                            doc_confidence,
                        ) = await self.classify_document(
                            filename,
                            email_subject,
                            email_body,
                            potential_asset_type,
                            sender_email,
                        )
                        self.logger.info(
                            "📋 Re-classified with sender asset context: %s (confidence: %.2f)",
                            document_category.value,
                            doc_confidence,
                        )
        else:
            self.logger.info("❓ Unknown sender: %s", sender_email)

        # Step 4: Determine overall confidence level
        confidence_level = self.determine_confidence_level(
            doc_confidence, asset_confidence, sender_known
        )

        confidence_icons = {
            ConfidenceLevel.HIGH: "🟢",
            ConfidenceLevel.MEDIUM: "🟡",
            ConfidenceLevel.LOW: "🟠",
            ConfidenceLevel.VERY_LOW: "🔴",
        }

        icon = confidence_icons[confidence_level]
        self.logger.info("%s Overall confidence: %s", icon, confidence_level.value)

        # Step 5: Update result with Phase 3 data
        result.document_category = document_category
        result.confidence_level = confidence_level
        result.matched_asset_id = matched_asset_id
        result.asset_confidence = asset_confidence
        result.classification_metadata = {
            "document_confidence": doc_confidence,
            "asset_confidence": asset_confidence,
            "sender_known": sender_known,
            "asset_matches": asset_matches[:3],  # Top 3 matches
            "sender_asset_count": len(sender_assets),
        }

        # DECISION SUMMARY LOG
        self.logger.info("=" * 80)
        self.logger.info("📊 PROCESSING DECISION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"📄 File: {filename}")
        self.logger.info(f"📧 From: {sender_email}")
        self.logger.info(f"📝 Subject: {email_subject}")
        self.logger.info("-" * 40)
        self.logger.info("🏢 ASSET MATCHING:")
        if matched_asset_id:
            asset = await self.get_asset(matched_asset_id)
            asset_name = asset.deal_name if asset else "Unknown"
            self.logger.info(f"   ✅ Matched Asset: {asset_name}")
            self.logger.info(f"   📊 Asset Confidence: {asset_confidence:.3f}")
        else:
            self.logger.info("   ❌ No Asset Match")
        self.logger.info("-" * 40)
        self.logger.info("📋 DOCUMENT CLASSIFICATION:")
        self.logger.info(f"   📂 Category: {document_category.value}")
        self.logger.info(f"   📊 Classification Confidence: {doc_confidence:.3f}")
        self.logger.info("-" * 40)
        self.logger.info("👤 SENDER KNOWLEDGE:")
        self.logger.info(f"   🔍 Sender Known: {sender_known}")
        if sender_known:
            self.logger.info(f"   📊 Associated Assets: {len(sender_assets)}")
        self.logger.info("-" * 40)
        self.logger.info(f"{icon} FINAL DECISION:")
        self.logger.info(f"   📏 Confidence Level: {confidence_level.value.upper()}")
        if matched_asset_id:
            self.logger.info(
                f"   📂 Will save to: {asset_name if 'asset_name' in locals() else 'Asset folder'}"
            )
        else:
            self.logger.info("   📂 Will save to: General review folder")

        # Show routing decision
        if confidence_level == ConfidenceLevel.HIGH:
            self.logger.info("   🎬 Action: AUTO-PROCESS (confidence ≥ 85%)")
        elif confidence_level == ConfidenceLevel.MEDIUM:
            self.logger.info(
                "   🎬 Action: PROCESS WITH CONFIRMATION (confidence ≥ 65%)"
            )
        elif confidence_level == ConfidenceLevel.LOW:
            self.logger.info("   🎬 Action: SAVE UNCATEGORIZED (confidence ≥ 40%)")
        else:
            self.logger.info("   🎬 Action: HUMAN REVIEW REQUIRED (confidence < 40%)")

        self.logger.info("=" * 80)

        return result

    @log_function()
    async def save_attachment_to_asset_folder(
        self,
        attachment_content: bytes,
        filename: str,
        processing_result: ProcessingResult,
        asset_id: str | None = None,
    ) -> Path | None:
        """
        Save processed attachment to the appropriate asset folder.

        Uses the asset's defined folder_path from the asset setup to ensure
        consistent file organization. Creates document category subfolders
        within the asset's designated path.

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
                # High/Medium confidence: Save to specific asset folder using asset's folder_path
                asset = await self.get_asset(asset_id)
                if asset:
                    # Use the asset's predefined folder path
                    asset_base_folder = Path(asset.folder_path)

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
                            f"Saving to asset folder with category: {asset.deal_name}/{processing_result.document_category.value}"
                        )
                    else:
                        target_folder = asset_base_folder / "uncategorized"
                        self.logger.info(
                            f"Saving to asset folder (uncategorized): {asset.deal_name}/uncategorized"
                        )
                else:
                    self.logger.warning(f"Asset not found for ID: {asset_id}")
                    # Fallback to generic uncategorized folder
                    target_folder = (
                        self.base_assets_path / "uncategorized" / "unknown_asset"
                    )

            elif asset_id and processing_result.confidence_level == ConfidenceLevel.LOW:
                # Low confidence with asset match: Save to asset's review subfolder
                asset = await self.get_asset(asset_id)
                if asset:
                    asset_base_folder = Path(asset.folder_path)
                    target_folder = asset_base_folder / "needs_review"
                    self.logger.info(
                        f"Saving to asset review folder: {asset.deal_name}/needs_review"
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

            self.logger.info(f"💾 File saved to: {file_path}")

            # Update processing result with file path
            processing_result.file_path = file_path

            return file_path

        except Exception as e:
            self.logger.error(f"Failed to save attachment {filename}: {e}")
            return None

    async def process_and_save_attachment(
        self,
        attachment_data: dict[str, Any],
        email_data: dict[str, Any],
        save_to_disk: bool = True,
    ) -> ProcessingResult:
        """
        Complete attachment processing pipeline including file saving.

        This is the main entry point for processing email attachments with
        full validation, classification, asset matching, and file saving.

        Args:
            attachment_data: Dict with 'filename' and 'content' keys
            email_data: Dict with email metadata
            save_to_disk: Whether to save processed files to disk

        Returns:
            ProcessingResult with complete processing information
        """
        # Step 1: Enhanced processing (validation + classification)
        result = await self.enhanced_process_attachment(attachment_data, email_data)

        # Step 2: Handle duplicates - DO NOT SAVE TO DISK
        if result.status == ProcessingStatus.DUPLICATE:
            self.logger.info(
                f"🔄 Duplicate detected: {attachment_data.get('filename', 'unknown')} - skipping file save"
            )
            return result

        # Step 3: Save to disk if successful and requested
        if save_to_disk and result.status == ProcessingStatus.SUCCESS:
            content = attachment_data.get("content", b"")
            filename = attachment_data.get("filename", "unknown_attachment")

            if content:
                file_path = await self.save_attachment_to_asset_folder(
                    content, filename, result, result.matched_asset_id
                )

                if file_path:
                    self.logger.info("💾 Saved to: %s", file_path)

                    # Store document metadata in Qdrant
                    if self.qdrant and result.file_hash:
                        document_id = await self.store_processed_document(
                            result.file_hash, result, result.matched_asset_id
                        )
                        self.logger.info(
                            "📊 Document metadata stored: %s...", document_id[:8]
                        )
                else:
                    self.logger.warning("❌ Failed to save file to disk")

        return result

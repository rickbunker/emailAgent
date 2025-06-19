"""
Document processing pipeline.

This module orchestrates the complete document processing workflow:
1. Security validation (AV scan, file type checks)
2. Asset identification
3. Document classification
4. File storage
5. Episodic learning

It brings together all the modular components to provide a clean,
maintainable processing pipeline.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.asset_management.classification.document_classifier import DocumentClassifier
from src.asset_management.core.data_models import (
    Asset,
    AssetType,
    ClassificationContext,
    IdentificationContext,
    ProcessingResult,
    ProcessingStatus,
)
from src.asset_management.core.exceptions import (
    AssetNotFoundError,
    ProcessingError,
    SecurityError,
)
from src.asset_management.identification.asset_identifier import AssetIdentifier
from src.asset_management.memory_integration.episodic_learner import (
    EpisodicLearner,
    Outcome,
)
from src.asset_management.utils.security import SecurityService
from src.asset_management.utils.storage import StorageService
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.utils.config import config
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class DocumentProcessor:
    """
    Main document processing orchestrator.

    This class brings together all the components to process documents:
    - Security validation
    - Asset identification
    - Document classification
    - File storage
    - Learning from outcomes

    It maintains a clean separation of concerns by delegating to
    specialized services for each step.
    """

    def __init__(
        self,
        asset_identifier: Optional[AssetIdentifier] = None,
        document_classifier: Optional[DocumentClassifier] = None,
        episodic_learner: Optional[EpisodicLearner] = None,
        security_service: Optional[SecurityService] = None,
        storage_service: Optional[StorageService] = None,
        semantic_memory: Optional[SemanticMemory] = None,
        episodic_memory: Optional[EpisodicMemory] = None,
    ):
        """
        Initialize the document processor.

        Args:
            asset_identifier: Service for identifying assets
            document_classifier: Service for classifying documents
            episodic_learner: Service for learning from outcomes
            security_service: Service for security validation
            storage_service: Service for file storage
            semantic_memory: Semantic memory instance
            episodic_memory: Episodic memory instance
        """
        # Initialize memory systems if not provided
        self.semantic_memory = semantic_memory or self._create_semantic_memory()
        self.episodic_memory = episodic_memory or self._create_episodic_memory()

        # Initialize services
        self.asset_identifier = asset_identifier or AssetIdentifier()
        self.document_classifier = document_classifier or DocumentClassifier(
            semantic_memory=self.semantic_memory
        )
        self.episodic_learner = episodic_learner or EpisodicLearner(
            episodic_memory=self.episodic_memory
        )
        self.security = security_service or SecurityService()
        self.storage = storage_service or StorageService()

        logger.info("Document processor initialized")

    def _create_semantic_memory(self) -> SemanticMemory:
        """Create semantic memory instance."""
        return SemanticMemory(
            max_items=getattr(config, "semantic_memory_max_items", 50000),
            qdrant_url=getattr(config, "qdrant_url", "http://localhost:6333"),
            embedding_model=getattr(config, "embedding_model", "all-MiniLM-L6-v2"),
        )

    def _create_episodic_memory(self) -> EpisodicMemory:
        """Create episodic memory instance."""
        from qdrant_client import QdrantClient

        client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        return EpisodicMemory(
            qdrant_client=client,
            collection_name="episodic",
            max_items=getattr(config, "episodic_memory_max_items", 100000),
        )

    @log_function()
    async def process_attachment(
        self,
        attachment_data: dict[str, Any],
        email_data: dict[str, Any],
        known_assets: list[Asset],
    ) -> ProcessingResult:
        """
        Process a single attachment through the complete pipeline.

        This is the main entry point that orchestrates:
        1. Security validation
        2. Asset identification
        3. Document classification
        4. File storage
        5. Learning from the outcome

        Args:
            attachment_data: Attachment information including content
            email_data: Email context information
            known_assets: List of available assets

        Returns:
            ProcessingResult with complete processing information

        Raises:
            ProcessingError: If processing fails
            SecurityError: If security validation fails
        """
        logger.info(
            f"Processing attachment: {attachment_data.get('filename', 'unknown')}"
        )

        try:
            # Step 1: Security validation
            security_result = await self._validate_security(attachment_data)
            if security_result.status != ProcessingStatus.SUCCESS:
                return security_result

            # Step 2: Asset identification
            identification_context = IdentificationContext(
                filename=attachment_data.get("filename", ""),
                sender_email=email_data.get("sender_email"),
                email_subject=email_data.get("subject"),
                email_body=email_data.get("body"),
                metadata={
                    "email_date": email_data.get("date"),
                    "email_id": email_data.get("id"),
                },
            )

            asset_match = await self.asset_identifier.identify_asset(
                identification_context, known_assets
            )

            # Record identification decision for learning
            identification_decision_id = None
            if self.episodic_learner:
                identification_decision_id = (
                    await self.episodic_learner.record_identification_decision(
                        identification_context, asset_match
                    )
                )

            # Step 3: Document classification (if asset identified)
            category_match = None
            classification_decision_id = None

            if asset_match:
                # Get the asset details
                matched_asset = next(
                    (a for a in known_assets if a.deal_id == asset_match.asset_id), None
                )

                if matched_asset:
                    classification_context = ClassificationContext(
                        filename=attachment_data.get("filename", ""),
                        asset_type=matched_asset.asset_type,
                        asset_id=asset_match.asset_id,
                        email_subject=email_data.get("subject"),
                        email_body=email_data.get("body"),
                    )

                    category_match = await self.document_classifier.classify_document(
                        classification_context
                    )

                    # Record classification decision
                    if self.episodic_learner:
                        classification_decision_id = (
                            await self.episodic_learner.record_classification_decision(
                                classification_context, category_match
                            )
                        )

            # Step 4: Store the file
            storage_result = await self._store_file(
                attachment_data, asset_match, category_match, security_result.file_hash
            )

            # Step 5: Build final result
            result = ProcessingResult(
                status=ProcessingStatus.SUCCESS,
                file_hash=security_result.file_hash,
                file_path=storage_result.get("file_path"),
                confidence=asset_match.confidence if asset_match else 0.0,
                matched_asset_id=asset_match.asset_id if asset_match else None,
                asset_confidence=asset_match.confidence if asset_match else 0.0,
                document_category=category_match.category if category_match else None,
                confidence_level=(
                    category_match.confidence_level if category_match else None
                ),
                metadata={
                    "identification_decision_id": identification_decision_id,
                    "classification_decision_id": classification_decision_id,
                    "asset_match_details": (
                        asset_match.match_details if asset_match else None
                    ),
                    "category_match_details": (
                        category_match.match_details if category_match else None
                    ),
                    "processing_timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(
                f"Processing complete: {attachment_data.get('filename')} "
                f"-> {asset_match.asset_name if asset_match else 'No asset'} "
                f"({category_match.category.value if category_match else 'No category'})"
            )

            return result

        except SecurityError as e:
            logger.error(f"Security validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise ProcessingError(
                f"Failed to process attachment {attachment_data.get('filename')}",
                details={"error": str(e)},
            )

    async def _validate_security(
        self, attachment_data: dict[str, Any]
    ) -> ProcessingResult:
        """
        Validate security aspects of the attachment.

        Args:
            attachment_data: Attachment data including content

        Returns:
            ProcessingResult with security validation status
        """
        filename = attachment_data.get("filename", "")
        content = attachment_data.get("content", b"")

        # Validate file type
        if not await self.security.validate_file_type(filename):
            return ProcessingResult(
                status=ProcessingStatus.INVALID_TYPE,
                error_message=f"Invalid file type: {filename}",
            )

        # Validate file size
        if not await self.security.validate_file_size(content):
            return ProcessingResult(
                status=ProcessingStatus.ERROR,
                error_message=f"File too large: {filename}",
            )

        # Calculate file hash
        file_hash = await self.security.calculate_file_hash(content)

        # Check for duplicates
        if await self.storage.check_duplicate(file_hash):
            return ProcessingResult(
                status=ProcessingStatus.DUPLICATE,
                file_hash=file_hash,
                duplicate_of=file_hash,
            )

        # AV scan
        av_result = await self.security.scan_file_antivirus(content, filename)
        if not av_result.get("clean", False):
            return ProcessingResult(
                status=ProcessingStatus.AV_SCAN_FAILED,
                quarantine_reason=av_result.get("reason", "Virus detected"),
            )

        return ProcessingResult.success_result(file_hash)

    async def _store_file(
        self,
        attachment_data: dict[str, Any],
        asset_match: Optional[Any],
        category_match: Optional[Any],
        file_hash: str,
    ) -> dict[str, Any]:
        """
        Store the file in the appropriate location.

        Args:
            attachment_data: Attachment data
            asset_match: Asset identification result
            category_match: Document classification result
            file_hash: File hash for deduplication

        Returns:
            Storage result with file path
        """
        filename = attachment_data.get("filename", "unknown")
        content = attachment_data.get("content", b"")

        # Determine storage path
        if asset_match and category_match:
            # Store in asset/category folder
            result = await self.storage.save_to_asset_folder(
                content=content,
                filename=filename,
                asset_id=asset_match.asset_id,
                category=category_match.category.value,
                file_hash=file_hash,
            )
        elif asset_match:
            # Store in asset/uncategorized folder
            result = await self.storage.save_to_asset_folder(
                content=content,
                filename=filename,
                asset_id=asset_match.asset_id,
                category="uncategorized",
                file_hash=file_hash,
            )
        else:
            # Store in unmatched folder
            result = await self.storage.save_to_unmatched_folder(
                content=content, filename=filename, file_hash=file_hash
            )

        return result

    @log_function()
    async def record_human_feedback(
        self,
        decision_id: str,
        correct_result: dict[str, Any],
        feedback_type: str = "human_correction",
    ) -> None:
        """
        Record human feedback about a processing decision.

        This allows the system to learn from corrections and improve
        future processing accuracy.

        Args:
            decision_id: The decision ID to provide feedback for
            correct_result: The correct result according to human review
            feedback_type: Type of feedback (default: human_correction)
        """
        if not self.episodic_learner:
            logger.warning("No episodic learner available for feedback recording")
            return

        outcome = Outcome(
            success=False,  # Human correction means original was wrong
            feedback_type=feedback_type,
            correct_result=correct_result,
        )

        await self.episodic_learner.record_outcome(decision_id, outcome)

        logger.info(f"Recorded human feedback for decision: {decision_id}")

    async def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        stats = {
            "security_enabled": True,
            "learning_enabled": self.episodic_learner is not None,
            "storage_type": "asset_folder_based",
        }

        if self.episodic_learner:
            learning_stats = await self.episodic_learner.get_learning_stats()
            stats["learning_stats"] = learning_stats

        return stats

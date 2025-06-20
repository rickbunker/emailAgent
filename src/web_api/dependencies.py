"""
Dependency injection and service management for the API.

This module handles initialization of services and provides
dependency functions for FastAPI routes.
"""

# # Standard library imports
from typing import Optional, Dict, Any
from functools import lru_cache

# # Third-party imports
from qdrant_client import QdrantClient
from jinja2 import Environment, FileSystemLoader, select_autoescape

# # Local application imports
from src.asset_management import (
    AssetIdentifier,
    DocumentClassifier,
    SenderMappingService,
)
from src.asset_management.processing.document_processor import DocumentProcessor
from src.asset_management.services.asset_service import AssetService
from src.asset_management.utils.storage import StorageService
from src.memory.semantic import SemanticMemory
from src.memory.episodic import EpisodicMemory
from src.memory.procedural import ProceduralMemory
from src.memory.contact import ContactMemory
from src.utils.config import config
from src.utils.logging_system import get_logger

logger = get_logger(__name__)

# Global service instances
asset_service: Optional[AssetService] = None
document_processor: Optional[DocumentProcessor] = None
asset_identifier: Optional[AssetIdentifier] = None
document_classifier: Optional[DocumentClassifier] = None
sender_mapping_service: Optional[SenderMappingService] = None
storage_service: Optional[StorageService] = None
qdrant_client: Optional[QdrantClient] = None

# Global memory system instances
semantic_memory: Optional[SemanticMemory] = None
episodic_memory: Optional[EpisodicMemory] = None
procedural_memory: Optional[ProceduralMemory] = None
contact_memory: Optional[ContactMemory] = None


async def initialize_services() -> None:
    """
    Initialize all services at application startup.

    This function sets up all the services needed by the API,
    including database connections and memory systems.
    """
    global asset_service, document_processor, asset_identifier
    global document_classifier, sender_mapping_service, storage_service
    global qdrant_client
    global semantic_memory, episodic_memory, procedural_memory, contact_memory

    try:
        # Initialize Qdrant client
        try:
            qdrant_client = QdrantClient(
                host=config.qdrant_host, port=config.qdrant_port
            )
            logger.info("Connected to Qdrant vector database")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            logger.warning("Running without vector storage - some features limited")
            qdrant_client = None

        # Initialize memory systems
        try:
            # Get Qdrant URL
            qdrant_url = f"http://{config.qdrant_host}:{config.qdrant_port}"

            semantic_memory = SemanticMemory(qdrant_url=qdrant_url)
            episodic_memory = EpisodicMemory(qdrant_url=qdrant_url)
            # ProceduralMemory requires qdrant_client parameter
            procedural_memory = (
                ProceduralMemory(qdrant_client=qdrant_client) if qdrant_client else None
            )
            contact_memory = ContactMemory(qdrant_url=qdrant_url)

            # Only procedural memory has initialize_collections method
            # Other memory types initialize collections automatically when needed
            if procedural_memory:
                await procedural_memory.initialize_collections()

            logger.info("✅ Memory systems initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize memory systems: {e}")
            # Initialize with None to allow API to start but memory features will be limited
            semantic_memory = None
            episodic_memory = None
            procedural_memory = None
            contact_memory = None

        # Initialize services
        asset_service = AssetService(
            qdrant_client=qdrant_client, base_assets_path=config.assets_base_path
        )

        # Initialize collection if we have Qdrant
        if qdrant_client:
            await asset_service.initialize_collection()

        # Initialize other services
        asset_identifier = AssetIdentifier()
        document_classifier = DocumentClassifier()
        sender_mapping_service = SenderMappingService()
        storage_service = StorageService()

        # Initialize document processor with components
        document_processor = DocumentProcessor(
            asset_identifier=asset_identifier,
            document_classifier=document_classifier,
            storage_service=storage_service,
        )

        logger.info("✅ All services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


async def cleanup_services() -> None:
    """
    Cleanup services at application shutdown.

    This function properly closes connections and cleans up resources.
    """
    global qdrant_client

    try:
        # Close Qdrant connection
        if qdrant_client:
            # Qdrant client doesn't have explicit close, but we can set to None
            qdrant_client = None
            logger.info("Closed Qdrant connection")

        logger.info("✅ All services cleaned up successfully")

    except Exception as e:
        logger.error(f"Error during service cleanup: {e}")


# Dependency functions for FastAPI routes


async def get_asset_service() -> AssetService:
    """
    Dependency function to get the asset service.

    Returns:
        The initialized asset service instance

    Raises:
        RuntimeError: If service is not initialized
    """
    if not asset_service:
        raise RuntimeError("Asset service not initialized")
    return asset_service


async def get_document_processor() -> DocumentProcessor:
    """
    Dependency function to get the document processor.

    Returns:
        The initialized document processor instance

    Raises:
        RuntimeError: If service is not initialized
    """
    if not document_processor:
        raise RuntimeError("Document processor not initialized")
    return document_processor


async def get_sender_mapping_service() -> SenderMappingService:
    """
    Dependency function to get the sender mapping service.

    Returns:
        The initialized sender mapping service instance

    Raises:
        RuntimeError: If service is not initialized
    """
    if not sender_mapping_service:
        raise RuntimeError("Sender mapping service not initialized")
    return sender_mapping_service


async def get_storage_service() -> StorageService:
    """
    Dependency function to get the storage service.

    Returns:
        The initialized storage service instance

    Raises:
        RuntimeError: If service is not initialized
    """
    if not storage_service:
        raise RuntimeError("Storage service not initialized")
    return storage_service


async def get_qdrant_client() -> Optional[QdrantClient]:
    """
    Dependency function to get the Qdrant client.

    Returns:
        The Qdrant client if available, None otherwise
    """
    return qdrant_client


def get_memory_systems() -> Dict[str, Any]:
    """
    Dependency function to get all memory systems.

    Returns:
        Dictionary mapping memory system names to instances

    Raises:
        RuntimeError: If memory systems are not initialized
    """
    memory_systems = {}

    # Debug logging to understand what's happening
    logger.debug(
        f"Memory system status: semantic={semantic_memory is not None}, "
        f"episodic={episodic_memory is not None}, "
        f"procedural={procedural_memory is not None}, "
        f"contact={contact_memory is not None}"
    )

    if semantic_memory:
        memory_systems["semantic"] = semantic_memory
    if episodic_memory:
        memory_systems["episodic"] = episodic_memory
    if procedural_memory:
        memory_systems["procedural"] = procedural_memory
    if contact_memory:
        memory_systems["contact"] = contact_memory

    if not memory_systems:
        # Try to re-initialize if they're None
        logger.warning(
            "Memory systems appear to be None, attempting re-initialization..."
        )
        try:
            # Create simple instances for testing
            qdrant_url = f"http://{config.qdrant_host}:{config.qdrant_port}"
            memory_systems = {
                "semantic": SemanticMemory(qdrant_url=qdrant_url),
                "episodic": EpisodicMemory(qdrant_url=qdrant_url),
                "contact": ContactMemory(qdrant_url=qdrant_url),
            }

            # ProceduralMemory requires qdrant_client
            if qdrant_client:
                memory_systems["procedural"] = ProceduralMemory(
                    qdrant_client=qdrant_client
                )
            else:
                logger.warning("Cannot create ProceduralMemory without qdrant_client")

            logger.info("Successfully created memory systems on-demand")
        except Exception as e:
            logger.error(f"Failed to create memory systems on-demand: {e}")
            raise RuntimeError(
                f"Memory systems not initialized and cannot be created: {e}"
            )

    return memory_systems


# Create template environment
templates = Environment(
    loader=FileSystemLoader("src/web_api/templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def get_templates() -> Environment:
    """
    Get the Jinja2 template environment.

    Returns:
        The configured Jinja2 Environment instance
    """
    return templates

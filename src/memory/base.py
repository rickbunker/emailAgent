"""
Base Memory System for Email Document Management

This module provides the foundation for different types of memory storage used
throughout the email agent system, enabling learning and adaptation.

Memory Types Supported:
    - Procedural Memory: Stores rules, procedures, and workflows for email handling
    - Semantic Memory: Stores knowledge about senders, email types, and classifications
    - Episodic Memory: Stores conversation history, user feedback, and interaction logs
    - Contact Memory: Stores contact information and relationship data

Each memory type leverages Qdrant vector database for semantic search and retrieval,
with specific metadata schemas and filtering capabilities tailored to its purpose.

Architecture:
    BaseMemory provides the core vector storage functionality using sentence
    transformers for embeddings and Qdrant for vector operations. Specialized
    memory types inherit from this base and add domain-specific logic.

Key Features:
    - Semantic vector search with cosine similarity
    - Metadata filtering and structured queries
    - Automatic collection management and optimization
    - Memory item lifecycle tracking with timestamps
    - Async/await patterns for high-performance operations
    - Complete logging for debugging and monitoring
    - Type-safe interfaces with full validation

Storage Technology:
    - Vector Database: Qdrant for high-performance similarity search
    - Embeddings: SentenceTransformers (all-MiniLM-L6-v2 by default)
    - Metadata: JSON payloads with structured schemas
    - Indexing: Cosine similarity with HNSW graphs

Version: 1.0.0
Author: Rick Bunker, rbunker@inveniam.io
License -- for Inveniam use only
Copyright 2025 by Inveniam Capital Partners, LLC and Rick Bunker
"""

# # Standard library imports
import os

# Logging system integration
import sys
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

# # Third-party imports
# Data validation and serialization
from pydantic import BaseModel, Field, validator

# Vector database and embedding dependencies
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # Local application imports
from utils.logging_system import get_logger, log_function

# Initialize logger
logger = get_logger(__name__)


class MemoryItem(BaseModel):
    """
    Represents a single memory item with content and metadata.

    Provides a standardized structure for storing information in the memory
    system with automatic timestamp management and metadata validation.

    Attributes:
        id: Unique identifier for the memory item
        content: The actual content/text being stored
        metadata: Additional structured data associated with the content
        created_at: ISO timestamp when item was created
        last_accessed: ISO timestamp when item was last retrieved
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(
        ..., min_length=1, description="Memory content cannot be empty"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @validator("content")
    def validate_content(cls, v: str) -> str:
        """Validate that content is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Memory content cannot be empty or whitespace only")
        return v.strip()

    @validator("metadata")
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate metadata structure and size."""
        if not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary")
        # Prevent extremely large metadata objects
        if len(str(v)) > 10000:  # 10KB limit
            raise ValueError("Metadata too large (max 10KB)")
        return v

    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryItem":
        """Create from dictionary loaded from storage."""
        return cls(**data)


class BaseMemory:
    """
    Base class for all memory types in the email agent system.

    This class provides the core functionality for storing and retrieving memories
    using Qdrant as the vector database backend. Each memory type (procedural,
    semantic, episodic, contact) extends this class and adds type-specific functionality.

    The memory system uses semantic embeddings to enable retrieval of
    relevant information based on context and similarity rather than exact matches.

    Attributes:
        collection_name: Name of the Qdrant collection for this memory type
        max_items: Maximum number of items to store before cleanup
        client: Qdrant async client for vector operations
        embedding_model: SentenceTransformer model for generating embeddings
        vector_size: Dimension of the embedding vectors
        is_initialized: Whether the memory system has been initialized
    """

    def __init__(
        self,
        max_items: int = 1000,
        qdrant_url: str | None = None,
        embedding_model: str | None = None,
        vector_size: int = 384,
    ) -> None:
        """
        Initialize the memory system.

        Args:
            max_items: Maximum number of items to store before cleanup
            qdrant_url: URL for Qdrant server (defaults to QDRANT_URL env var)
            embedding_model: Name of the sentence transformer model to use
            vector_size: Dimension of embedding vectors (must match model)

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If cannot connect to Qdrant
        """
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")

        # Derive collection name from class name
        self.collection_name = self.__class__.__name__.lower().replace("memory", "")
        self.max_items = max_items
        self.vector_size = vector_size
        self.is_initialized = False

        # Initialize Qdrant client
        qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = AsyncQdrantClient(url=qdrant_url)

        # Initialize embedding model
        model_name = embedding_model or "all-MiniLM-L6-v2"
        self.embedding_model = SentenceTransformer(model_name)

        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(
            f"Initialized {self.__class__.__name__} with collection '{self.collection_name}'"
        )

    @log_function()
    async def _ensure_collection(self) -> None:
        """
        Ensure the Qdrant collection exists with proper configuration.

        Creates the collection if it doesn't exist and validates the
        configuration matches our requirements.

        Raises:
            ConnectionError: If cannot connect to Qdrant
            ValueError: If collection configuration is invalid
        """
        try:
            collections_response = await self.client.get_collections()
            collection_names = [
                collection.name for collection in collections_response.collections
            ]

            if self.collection_name not in collection_names:
                self.logger.info(f"Creating collection '{self.collection_name}'")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                )
                self.logger.info(
                    f"Collection '{self.collection_name}' created successfully"
                )
            else:
                # Validate existing collection
                collection_info = await self.client.get_collection(self.collection_name)
                if collection_info.config.params.vectors.size != self.vector_size:
                    raise ValueError(
                        f"Collection vector size mismatch: expected {self.vector_size}, "
                        f"got {collection_info.config.params.vectors.size}"
                    )
                self.logger.debug(
                    f"Collection '{self.collection_name}' already exists and validated"
                )

            self.is_initialized = True

        except Exception as e:
            self.logger.error(f"Failed to ensure collection: {e}")
            raise ConnectionError(
                f"Failed to initialize collection '{self.collection_name}': {e}"
            )

    @log_function()
    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Add a new memory item.

        Generates an embedding for the content, creates a memory item,
        and stores it in the vector database with metadata.

        Args:
            content: The content to store
            metadata: Additional metadata to store with the content

        Returns:
            The unique ID of the created memory item

        Raises:
            ValueError: If content is invalid
            ConnectionError: If storage operation fails
        """
        await self._ensure_collection()

        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        try:
            # Generate embedding for the content
            embedding = self.embedding_model.encode(content.strip())

            # Create memory item with validation
            item = MemoryItem(content=content.strip(), metadata=metadata or {})

            # Prepare point for Qdrant
            point = models.PointStruct(
                id=item.id, vector=embedding.tolist(), payload=item.to_dict()
            )

            # Store in Qdrant
            await self.client.upsert(
                collection_name=self.collection_name, points=[point]
            )

            self.logger.info(f"Added memory item {item.id} to {self.collection_name}")
            self.logger.debug(f"Content preview: {content[:100]}...")

            # Check if cleanup is needed
            await self._check_cleanup()

            return item.id

        except Exception as e:
            self.logger.error(f"Failed to add memory item: {e}")
            raise ConnectionError(f"Failed to store memory item: {e}")

    @log_function()
    async def get(self, memory_id: str) -> MemoryItem | None:
        """
        Get a memory item by ID.

        Retrieves a specific memory item and updates its access timestamp.

        Args:
            memory_id: The unique ID of the memory item to retrieve

        Returns:
            The retrieved memory item, or None if not found

        Raises:
            ValueError: If memory_id is invalid
            ConnectionError: If retrieval operation fails
        """
        if not memory_id or not memory_id.strip():
            raise ValueError("Memory ID cannot be empty")

        await self._ensure_collection()

        try:
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id.strip()],
                with_payload=True,
                with_vectors=False,
            )

            if not result:
                self.logger.debug(
                    f"Memory item {memory_id} not found in {self.collection_name}"
                )
                return None

            point = result[0]
            item = MemoryItem.from_dict(point.payload)

            # Update access timestamp
            item.update_access_time()
            await self._update_access_time(memory_id, item.last_accessed)

            self.logger.debug(
                f"Retrieved memory item {memory_id} from {self.collection_name}"
            )
            return item

        except Exception as e:
            self.logger.error(f"Failed to retrieve memory item {memory_id}: {e}")
            return None

    @log_function()
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Search for memory items using vector similarity.

        Performs semantic search using vector embeddings to find items
        most similar to the query text.

        Args:
            query: The search query text
            limit: Maximum number of results to return
            filter_conditions: Optional metadata filter conditions
            score_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of tuples containing (MemoryItem, similarity_score)

        Raises:
            ValueError: If query parameters are invalid
            ConnectionError: If search operation fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if limit <= 0:
            raise ValueError("Limit must be positive")
        if not 0.0 <= score_threshold <= 1.0:
            raise ValueError("Score threshold must be between 0.0 and 1.0")

        await self._ensure_collection()

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query.strip())

            # Perform vector search
            search_result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding.tolist(),
                limit=limit,
                query_filter=(
                    models.Filter(**filter_conditions) if filter_conditions else None
                ),
                with_payload=True,
                with_vectors=False,
                score_threshold=score_threshold,
            )

            # Process results
            results = []
            for hit in search_result.points:
                try:
                    item = MemoryItem.from_dict(hit.payload)

                    # Update access timestamp
                    item.update_access_time()
                    await self._update_access_time(item.id, item.last_accessed)

                    results.append((item, hit.score))
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process search result {hit.id}: {e}"
                    )
                    continue

            self.logger.info(
                f"Search in {self.collection_name}: query='{query[:50]}...' "
                f"filter={filter_conditions} -> {len(results)} results"
            )

            return results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise ConnectionError(f"Search operation failed: {e}")

    @log_function()
    async def update(
        self,
        memory_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update an existing memory item.

        Updates the content and/or metadata of an existing memory item.
        If content is updated, a new embedding is generated.

        Args:
            memory_id: The unique ID of the memory item to update
            content: New content (optional)
            metadata: New metadata (optional, will be merged with existing)

        Returns:
            True if update successful, False if item not found

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If update operation fails
        """
        if not memory_id or not memory_id.strip():
            raise ValueError("Memory ID cannot be empty")
        if content is not None and (not content or not content.strip()):
            raise ValueError("Content cannot be empty if provided")

        await self._ensure_collection()

        try:
            # Get existing item
            existing_item = await self.get(memory_id)
            if not existing_item:
                self.logger.warning(
                    f"Cannot update non-existent memory item {memory_id}"
                )
                return False

            # Update content and metadata
            new_content = content.strip() if content else existing_item.content
            new_metadata = existing_item.metadata.copy()
            if metadata:
                new_metadata.update(metadata)

            # Create updated item
            updated_item = MemoryItem(
                id=memory_id,
                content=new_content,
                metadata=new_metadata,
                created_at=existing_item.created_at,
                last_accessed=datetime.now(UTC).isoformat(),
            )

            # Generate new embedding if content changed
            if content:
                embedding = self.embedding_model.encode(new_content)
            else:
                # Retrieve existing embedding
                existing_points = await self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[memory_id],
                    with_vectors=True,
                )
                embedding = existing_points[0].vector

            # Update in Qdrant
            point = models.PointStruct(
                id=memory_id,
                vector=embedding if isinstance(embedding, list) else embedding.tolist(),
                payload=updated_item.to_dict(),
            )

            await self.client.upsert(
                collection_name=self.collection_name, points=[point]
            )

            self.logger.info(
                f"Updated memory item {memory_id} in {self.collection_name}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to update memory item {memory_id}: {e}")
            raise ConnectionError(f"Update operation failed: {e}")

    @log_function()
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory item by ID.

        Permanently removes a memory item from the vector database.

        Args:
            memory_id: The unique ID of the memory item to delete

        Returns:
            True if deletion successful, False if item not found

        Raises:
            ValueError: If memory_id is invalid
            ConnectionError: If deletion operation fails
        """
        if not memory_id or not memory_id.strip():
            raise ValueError("Memory ID cannot be empty")

        await self._ensure_collection()

        try:
            # Check if item exists
            existing_items = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id],
                with_payload=False,
            )

            if not existing_items:
                self.logger.warning(
                    f"Cannot delete non-existent memory item {memory_id}"
                )
                return False

            # Delete from Qdrant
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[memory_id]),
            )

            self.logger.info(
                f"Deleted memory item {memory_id} from {self.collection_name}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete memory item {memory_id}: {e}")
            raise ConnectionError(f"Delete operation failed: {e}")

    @log_function()
    async def clear_collection(self, force_delete: bool = False) -> None:
        """
        Clear all items from the memory collection.

        Removes all memory items from the collection. Use with caution!

        Args:
            force_delete: If True, actually perform the deletion

        Raises:
            ValueError: If force_delete is not True (safety measure)
            ConnectionError: If clear operation fails
        """
        if not force_delete:
            raise ValueError("Must set force_delete=True to clear collection")

        await self._ensure_collection()

        try:
            # Delete entire collection and recreate
            await self.client.delete_collection(collection_name=self.collection_name)
            await self._ensure_collection()

            self.logger.warning(
                f"Cleared all items from collection {self.collection_name}"
            )

        except Exception as e:
            self.logger.error(f"Failed to clear collection: {e}")
            raise ConnectionError(f"Clear operation failed: {e}")

    @log_function()
    async def get_collection_info(self) -> dict[str, Any]:
        """
        Get information about the memory collection.

        Returns metadata about the collection including item counts,
        configuration, and performance metrics.

        Returns:
            Dictionary containing collection information

        Raises:
            ConnectionError: If info retrieval fails
        """
        await self._ensure_collection()

        try:
            collection_info = await self.client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.value,
                "max_items_configured": self.max_items,
                "status": collection_info.status.value,
            }

        except Exception as e:
            self.logger.error(f"Failed to get collection info: {e}")
            raise ConnectionError(f"Info retrieval failed: {e}")

    @log_function()
    async def _update_access_time(self, memory_id: str, access_time: str) -> None:
        """
        Update the last access time for a memory item.

        Args:
            memory_id: ID of the memory item
            access_time: ISO timestamp of access
        """
        try:
            await self.client.set_payload(
                collection_name=self.collection_name,
                payload={"last_accessed": access_time},
                points=[memory_id],
            )
        except Exception as e:
            self.logger.warning(f"Failed to update access time for {memory_id}: {e}")

    @log_function()
    async def _check_cleanup(self) -> None:
        """
        Check if cleanup is needed and perform it if necessary.

        Removes oldest items if the collection exceeds max_items limit.
        """
        try:
            info = await self.get_collection_info()
            if info["points_count"] <= self.max_items:
                return

            # Get oldest items to remove
            excess_count = info["points_count"] - self.max_items

            # Query all items ordered by creation time
            all_items = await self.client.scroll(
                collection_name=self.collection_name,
                limit=excess_count + 100,  # Get more to find oldest
                with_payload=True,
                with_vectors=False,
            )

            # Sort by creation time and get oldest
            items_with_time = [
                (point.id, point.payload.get("created_at", ""))
                for point in all_items[0]
            ]
            items_with_time.sort(key=lambda x: x[1])

            # Delete oldest items
            ids_to_delete = [item[0] for item in items_with_time[:excess_count]]

            if ids_to_delete:
                await self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=ids_to_delete),
                )

                self.logger.info(
                    f"Cleanup: removed {len(ids_to_delete)} oldest items from {self.collection_name}"
                )

        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    @asynccontextmanager
    async def batch_operations(self) -> AsyncGenerator["BaseMemory", None]:
        """
        Context manager for batch operations.

        Provides a context for performing multiple operations efficiently.

        Yields:
            Self instance for chained operations
        """
        await self._ensure_collection()
        try:
            yield self
        except Exception as e:
            self.logger.error(f"Batch operations failed: {e}")
            raise
        finally:
            # Any cleanup if needed
            pass

    def __repr__(self) -> str:
        """String representation of the memory instance."""
        return (
            f"{self.__class__.__name__}("
            f"collection='{self.collection_name}', "
            f"max_items={self.max_items}, "
            f"initialized={self.is_initialized})"
        )

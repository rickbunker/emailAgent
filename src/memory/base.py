"""
Base memory class for the email agent.

This module provides the foundation for different types of memory storage:
- Procedural Memory: Stores rules and procedures for email handling
- Semantic Memory: Stores knowledge about senders and email types
- Episodic Memory: Stores conversation history and feedback
- Contact Memory: Stores contact information

Each memory type uses Qdrant for vector storage and retrieval, with specific metadata
and filtering capabilities tailored to its purpose.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
import uuid
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field

class MemoryItem(BaseModel):
    """Represents a single memory item with content and metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class BaseMemory:
    """
    Base class for all memory types.
    
    This class provides the core functionality for storing and retrieving memories
    using Qdrant as the vector database. Each memory type (procedural, semantic, episodic)
    extends this class and adds type-specific functionality.
    
    Attributes:
        collection_name (str): Name of the Qdrant collection for this memory type
        max_items (int): Maximum number of items to store
        client (AsyncQdrantClient): Qdrant client for vector operations
        embedding_model (SentenceTransformer): Model for generating embeddings
    """
    
    def __init__(
        self,
        max_items: int = 1000,
        qdrant_url: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the memory system.
        
        Args:
            max_items (int): Maximum number of items to store
            qdrant_url (str, optional): URL for Qdrant server. Defaults to QDRANT_URL env var
            embedding_model (str, optional): Name of the sentence transformer model to use
        """
        self.collection_name = self.__class__.__name__.lower().replace("memory", "")
        self.max_items = max_items
        self.client = AsyncQdrantClient(
            url=qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        )
        self.embedding_model = SentenceTransformer(
            embedding_model or "all-MiniLM-L6-v2"
        )

    async def _ensure_collection(self):
        """Ensure the Qdrant collection exists with proper configuration."""
        collections = (await self.client.get_collections()).collections
        collection_names = [collection.name for collection in collections]
        
        if self.collection_name not in collection_names:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=384,  # all-MiniLM-L6-v2 dimension
                    distance=Distance.COSINE
                )
            )

    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a new memory item.
        
        Args:
            content (str): The content to store
            metadata (dict, optional): Additional metadata to store with the content
            
        Returns:
            str: The ID of the created memory item
        """
        await self._ensure_collection()
        
        # Generate embedding for the content
        embedding = self.embedding_model.encode(content)
        
        # Create memory item
        item = MemoryItem.model_validate({
            "content": content,
            "metadata": metadata or {}
        })
        
        # Add to Qdrant
        point = models.PointStruct(
            id=item.id,
            vector=embedding.tolist(),
            payload={
                "content": item.content,
                "metadata": item.metadata,
                "created_at": item.created_at,
                "last_accessed": item.last_accessed
            }
        )
        
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        print(f"[DEBUG][ADD] {self.collection_name}: {item.id} -> {item.content}")
        return point.id

    async def get(self, memory_id: str) -> Optional[MemoryItem]:
        """Get a memory item by ID.
        
        Args:
            memory_id: The ID of the memory item to retrieve
            
        Returns:
            Optional[MemoryItem]: The retrieved memory item, or None if not found
        """
        await self._ensure_collection()
        try:
            # Use retrieve instead of retrieve_points for API compatibility
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False
            )
            if not result:
                print(f"[DEBUG][GET] {self.collection_name}: {memory_id} -> NOT FOUND")
                return None
                
            point = result[0]
            print(f"[DEBUG][GET] {self.collection_name}: {memory_id} -> FOUND")
            return MemoryItem(
                id=point.id,
                content=point.payload["content"],
                metadata=point.payload["metadata"],
                created_at=point.payload["created_at"],
                last_accessed=point.payload["last_accessed"]
            )
        except Exception as e:
            print(f"[DEBUG][GET][ERROR] {self.collection_name}: {memory_id} -> {e}")
            return None

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[MemoryItem]:
        """Search for memory items using vector similarity.
        
        Args:
            query: The search query text
            limit: Maximum number of results to return
            filter: Optional filter conditions
            
        Returns:
            List[MemoryItem]: List of matching memory items
        """
        await self._ensure_collection()
        query_embedding = self.embedding_model.encode(query)
        
        # Use query_points instead of deprecated search
        search_result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding.tolist(),
            limit=limit,
            query_filter=filter,
            with_payload=True,
            with_vectors=False
        )
        
        # Fix: Access points from QueryResponse instead of trying len() on QueryResponse
        print(f"[DEBUG][SEARCH] {self.collection_name}: query='{query}' filter={filter} -> {len(search_result.points)} results")
        return [
            MemoryItem(
                id=hit.id,
                content=hit.payload["content"],
                metadata=hit.payload["metadata"],
                created_at=hit.payload["created_at"],
                last_accessed=hit.payload["last_accessed"]
            )
            for hit in search_result.points
        ]

    async def update(self, memory_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing memory item.
        
        Args:
            memory_id: The ID of the memory item to update
            content: New content for the memory item
            metadata: New metadata for the memory item
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        await self._ensure_collection()
        try:
            # Get existing item
            existing = await self.get(memory_id)
            if not existing:
                return False
            
            # Generate new embedding
            embedding = self.embedding_model.encode(content)
            
            # Update the item
            updated_item = MemoryItem(
                id=memory_id,
                content=content,
                metadata=metadata or existing.metadata,
                created_at=existing.created_at,
                last_accessed=datetime.now(UTC).isoformat()
            )
            
            # Update in Qdrant
            point = models.PointStruct(
                id=memory_id,
                vector=embedding.tolist(),
                payload={
                    "content": updated_item.content,
                    "metadata": updated_item.metadata,
                    "created_at": updated_item.created_at,
                    "last_accessed": updated_item.last_accessed
                }
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            print(f"[DEBUG][UPDATE] {self.collection_name}: {memory_id} -> UPDATED")
            return True
        except Exception as e:
            print(f"[DEBUG][UPDATE][ERROR] {self.collection_name}: {memory_id} -> {e}")
            return False

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory item.
        
        Args:
            memory_id: The ID of the memory item to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        await self._ensure_collection()
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[memory_id])
            )
            print(f"[DEBUG][DELETE] {self.collection_name}: {memory_id} -> DELETED")
            return True
        except Exception as e:
            print(f"[DEBUG][DELETE][ERROR] {self.collection_name}: {memory_id} -> {e}")
            return False

    async def clear_collection(self, force_delete: bool = False) -> None:
        """
        Clear all items from the collection.
        
        Args:
            force_delete (bool): If True, skip confirmation prompt
        """
        await self._ensure_collection()
        if not force_delete:
            print(f"\nWARNING: This will delete all data in the {self.collection_name} collection.")
            response = input("Are you sure you want to proceed? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return
        
        try:
            # Delete the entire collection and recreate it
            await self.client.delete_collection(collection_name=self.collection_name)
            await self._ensure_collection()  # Recreate the collection
            print(f"[DEBUG][CLEAR] {self.collection_name}: collection cleared")
        except Exception as e:
            print(f"[DEBUG][CLEAR][ERROR] {self.collection_name}: {e}") 
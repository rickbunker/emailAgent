import time
import uuid
from typing import Any, Dict, List, Optional, Union
from qdrant_client.http import models
from .base import BaseMemory, MemoryItem

"""
Semantic memory for storing knowledge about senders and email types.

This module provides the SemanticMemory class which extends BaseMemory to store
and retrieve knowledge about email senders and types. It uses type-specific
metadata and filtering to ensure proper organization of knowledge data.
"""

class SemanticMemory(BaseMemory):
    """
    Semantic memory for storing knowledge about senders and email types.
    
    This class extends BaseMemory to provide specialized functionality for
    storing and retrieving knowledge about email senders and types. It
    automatically adds type metadata to ensure proper filtering of knowledge.
    
    Attributes:
        collection_name (str): Always "semantic" for this memory type
    """
    
    def __init__(
        self,
        max_items: Optional[int] = 1000,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        super().__init__(
            max_items=max_items,
            qdrant_url=qdrant_url,
            embedding_model=embedding_model
        )
    
    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add new knowledge about a sender or email type.
        
        Args:
            content (str): The knowledge to store
            metadata (dict, optional): Additional metadata to store
            
        Returns:
            str: The ID of the created memory item
        """
        if metadata is None:
            metadata = {}
        metadata.setdefault("type", "knowledge")
        result = await super().add(content, metadata)
        print(f"[DEBUG][ADD][Semantic] {result}")
        return result
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[MemoryItem]:
        """
        Search for knowledge about senders and email types.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            filter (dict, optional): Additional filters to apply
            
        Returns:
            List[MemoryItem]: List of matching knowledge items
        """
        filter_conditions = {
            "must": [
                {"key": "metadata.type", "match": {"value": "knowledge"}}
            ]
        }
        if filter:
            if "must" in filter:
                filter_conditions["must"].extend(filter["must"])
            else:
                filter_conditions["must"].append(filter)
        results = await super().search(query, limit, filter_conditions)
        print(f"[DEBUG][SEARCH][Semantic] query='{query}' -> {len(results)} results")
        return results 
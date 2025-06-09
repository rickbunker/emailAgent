import time
import uuid
from typing import Any, Dict, List, Optional, Union
from qdrant_client.http import models
from .base import BaseMemory, MemoryItem
from datetime import datetime, UTC

class EpisodicMemory(BaseMemory):
    """
    Episodic memory for storing conversation history and feedback.
    
    This class extends BaseMemory to provide specialized functionality for
    storing and retrieving conversation history. It automatically adds
    timestamps and conversation IDs to metadata, and provides methods for
    time-based and conversation-based searching.
    
    Attributes:
        collection_name (str): Always "episodic" for this memory type
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
        Add a new conversation memory.
        
        Args:
            content (str): The conversation content to store
            metadata (dict, optional): Additional metadata to store
            
        Returns:
            str: The ID of the created memory item
        """
        if metadata is None:
            metadata = {}
        # Only set default type if not already specified
        if "type" not in metadata:
            metadata["type"] = "conversation"
        metadata.setdefault("timestamp", datetime.now(UTC).timestamp())
        result = await super().add(content, metadata)
        print(f"[DEBUG][ADD][Episodic] {result}")
        return result
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        time_range: Optional[Dict[str, float]] = None
    ) -> List[MemoryItem]:
        """
        Search for conversation memories.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            filter (dict, optional): Additional filters to apply
            time_range (dict, optional): Time range filter with 'start' and 'end' timestamps
            
        Returns:
            List[MemoryItem]: List of matching conversation memories
        """
        # Don't filter by type by default - let episodic memory contain any type of conversation/memory
        filter_conditions = {"must": []}
        
        if time_range:
            time_filter = {
                "key": "metadata.timestamp",
                "range": {
                    "gte": time_range.get("start", 0),
                    "lte": time_range.get("end", datetime.now(UTC).timestamp())
                }
            }
            filter_conditions["must"].append(time_filter)
        if filter:
            if "must" in filter:
                filter_conditions["must"].extend(filter["must"])
            else:
                filter_conditions["must"].append(filter)
        
        # If no filters are specified, search all items in this collection
        if not filter_conditions["must"]:
            filter_conditions = None
            
        results = await super().search(query, limit, filter_conditions)
        print(f"[DEBUG][SEARCH][Episodic] query='{query}' -> {len(results)} results")
        return results 
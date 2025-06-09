import time
import uuid
from typing import Any, Dict, List, Optional
from qdrant_client.http import models
from .base import BaseMemory, MemoryItem

"""
Procedural memory for storing rules and procedures.

This module provides the ProceduralMemory class which extends BaseMemory to store
and retrieve rules and procedures for email handling. It uses type-specific
metadata and filtering to ensure proper organization of rule data.
"""

class ProceduralMemory(BaseMemory):
    """
    Procedural memory for storing rules and procedures.
    
    This class extends BaseMemory to provide specialized functionality for
    storing and retrieving rules and procedures. It automatically adds
    type metadata to ensure proper filtering of rules.
    
    Attributes:
        collection_name (str): Always "procedural" for this memory type
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
        Add a new rule or procedure.
        
        Args:
            content (str): The rule or procedure to store
            metadata (dict, optional): Additional metadata to store
            
        Returns:
            str: The ID of the created memory item
        """
        if metadata is None:
            metadata = {}
        metadata.setdefault("type", "rule")
        result = await super().add(content, metadata)
        print(f"[DEBUG][ADD][Procedural] {result}")
        return result
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[MemoryItem]:
        """
        Search for rules and procedures.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            filter (dict, optional): Additional filters to apply
            
        Returns:
            List[MemoryItem]: List of matching rules and procedures
        """
        filter_conditions = {
            "must": [
                {"key": "metadata.type", "match": {"value": "rule"}}
            ]
        }
        if filter:
            if "must" in filter:
                filter_conditions["must"].extend(filter["must"])
            else:
                filter_conditions["must"].append(filter)
        results = await super().search(query, limit, filter_conditions)
        print(f"[DEBUG][SEARCH][Procedural] query='{query}' -> {len(results)} results")
        return results 
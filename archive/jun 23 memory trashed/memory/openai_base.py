"""
OpenAI-based Memory System Base Class.

Alternative implementation using OpenAI embeddings instead of HuggingFace models.
This avoids rate limiting issues and provides better quality embeddings.

To use this, set the environment variable:
    USE_OPENAI_EMBEDDINGS=true
    OPENAI_API_KEY=your-api-key

Author: Email Agent Team
"""

# # Standard library imports
import os
from typing import Optional

# # Third-party imports
import numpy as np
from openai import AsyncOpenAI

# # Local application imports
from src.utils.config import config
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


class OpenAIEmbeddingModel:
    """Wrapper for OpenAI embeddings that mimics SentenceTransformer interface."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        """
        Initialize OpenAI embedding model.

        Args:
            model_name: OpenAI model name (text-embedding-3-small or text-embedding-3-large)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model_name

        # Embedding dimensions
        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        self.vector_size = self.dimensions.get(model_name, 1536)
        logger.info(
            f"Initialized OpenAI embeddings with model: {model_name} (dim: {self.vector_size})"
        )

    def encode(self, text: str | list[str]) -> np.ndarray:
        """
        Synchronous wrapper for encoding (mimics SentenceTransformer).

        Note: This is a blocking call for compatibility.
        Consider using encode_async for better performance.
        """
        # # Standard library imports
        import asyncio

        # Handle the sync/async boundary
        try:
            # If we're already in an event loop, create a new one in a thread
            loop = asyncio.get_running_loop()
            # # Standard library imports
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.encode_async(text))
                return future.result()
        except RuntimeError:
            # No event loop running, we can use asyncio.run
            return asyncio.run(self.encode_async(text))

    async def encode_async(self, text: str | list[str]) -> np.ndarray:
        """
        Generate embeddings using OpenAI API.

        Args:
            text: Single text or list of texts to encode

        Returns:
            Numpy array of embeddings
        """
        # Ensure text is a list
        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        try:
            # Call OpenAI API
            response = await self.client.embeddings.create(
                model=self.model, input=texts
            )

            # Extract embeddings
            embeddings = [data.embedding for data in response.data]

            # Return as numpy array
            result = np.array(embeddings)

            # If input was a single string, return 1D array
            if isinstance(text, str):
                return result[0]

            return result

        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


def get_embedding_model(model_name: Optional[str] = None):
    """
    Get the appropriate embedding model based on configuration.

    Returns:
        Either SentenceTransformer or OpenAIEmbeddingModel
    """
    use_openai = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"

    if use_openai:
        # Use OpenAI embeddings
        openai_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddingModel(openai_model)
    else:
        # Use sentence transformers
        # # Third-party imports
        from sentence_transformers import SentenceTransformer

        model_name = model_name or config.embedding_model
        cache_dir = os.getenv(
            "SENTENCE_TRANSFORMERS_HOME",
            str(os.path.expanduser("~/.cache/sentence_transformers")),
        )

        return SentenceTransformer(model_name, cache_folder=cache_dir)


# Monkey patch for BaseMemory if using OpenAI
def patch_base_memory():
    """Patch BaseMemory to use OpenAI embeddings when configured."""
    # # Local application imports
    import src.memory.base as base_module

    # Store original init
    original_init = base_module.BaseMemory.__init__

    def patched_init(
        self, max_items=None, qdrant_url=None, embedding_model=None, vector_size=384
    ):
        # Call original init
        original_init(self, max_items, qdrant_url, embedding_model, vector_size)

        # Replace embedding model if using OpenAI
        if os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true":
            self.embedding_model = get_embedding_model(embedding_model)
            self.vector_size = self.embedding_model.vector_size
            self.logger.info(
                f"Using OpenAI embeddings with vector size: {self.vector_size}"
            )

    # Apply patch
    base_module.BaseMemory.__init__ = patched_init


# Auto-patch on import if configured
if os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true":
    patch_base_memory()
    logger.info("BaseMemory patched to use OpenAI embeddings")

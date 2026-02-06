"""
Swappable Embedding Service.

Supports multiple embedding providers:
- "local": sentence-transformers (free, no API needed)
- "openai": OpenAI embeddings API
- "tokamak": Tokamak AI Gateway embeddings (when available)

To switch providers, just change EMBEDDING_PROVIDER in .env file.
No code changes needed!
"""

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List, Optional, Union

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Local embeddings using sentence-transformers.
    Free, no API key needed, runs on your server.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Local embedding model loaded. Dimension: {self._dimension}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using local model."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI embeddings via their API.
    Requires OPENAI_API_KEY in environment.
    """

    # Dimension mapping for OpenAI models
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        from openai import OpenAI

        logger.info(f"Initializing OpenAI embedding provider: {model_name}")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self._dimension = self.DIMENSIONS.get(model_name, 1536)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using OpenAI API."""
        response = self.client.embeddings.create(input=texts, model=self.model_name)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = self.client.embeddings.create(input=[text], model=self.model_name)
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dimension


class TokamakEmbeddingProvider(BaseEmbeddingProvider):
    """
    Embeddings via Tokamak AI Gateway.
    Uses the same API format as OpenAI (OpenAI-compatible).
    """

    def __init__(
        self, base_url: str, api_key: str, model_name: str = "text-embedding-ada-002"
    ):
        from openai import OpenAI

        logger.info(f"Initializing Tokamak embedding provider: {model_name}")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self._dimension = 1536  # Default, adjust based on actual model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using Tokamak Gateway."""
        response = self.client.embeddings.create(input=texts, model=self.model_name)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = self.client.embeddings.create(input=[text], model=self.model_name)
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dimension


class EmbeddingService:
    """
    Main embedding service with swappable providers.

    Usage:
        service = EmbeddingService(settings)
        embeddings = service.embed_documents(["text1", "text2"])
        query_embedding = service.embed_query("search query")

    To switch providers, change EMBEDDING_PROVIDER in .env:
        - "local" for sentence-transformers (free)
        - "openai" for OpenAI API
        - "tokamak" for Tokamak Gateway (when available)
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = self._create_provider()
        logger.info(
            f"EmbeddingService initialized with provider: {settings.embedding_provider}"
        )

    def _create_provider(self) -> BaseEmbeddingProvider:
        """Create the appropriate embedding provider based on settings."""
        provider_type = self.settings.embedding_provider

        if provider_type == "local":
            return LocalEmbeddingProvider(self.settings.local_embedding_model)

        elif provider_type == "openai":
            if not self.settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY required when EMBEDDING_PROVIDER=openai"
                )
            return OpenAIEmbeddingProvider(
                api_key=self.settings.openai_api_key,
                model_name=self.settings.openai_embedding_model,
            )

        elif provider_type == "tokamak":
            return TokamakEmbeddingProvider(
                base_url=self.settings.tokamak_ai_base_url,
                api_key=self.settings.tokamak_ai_api_key,
                model_name=self.settings.tokamak_embedding_model,
            )

        else:
            raise ValueError(f"Unknown embedding provider: {provider_type}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        return self.provider.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self.provider.embed_query(text)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.provider.dimension

    @property
    def provider_name(self) -> str:
        """Get current provider name."""
        return self.settings.embedding_provider


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(get_settings())
    return _embedding_service

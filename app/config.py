"""
Configuration management with environment variables.
Supports swappable embedding providers.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Literal
from pydantic_settings import BaseSettings

# Ensure we load .env from the correct location
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===========================================
    # Tokamak AI Gateway (for Claude)
    # ===========================================
    tokamak_ai_base_url: str = "https://api.ai.tokamak.network"
    tokamak_ai_api_key: str = ""
    chat_model: str = "claude-sonnet-4.5"

    # ===========================================
    # Embedding Provider Configuration
    # ===========================================
    # SWAPPABLE: Change this to switch embedding providers
    # Options: "local", "openai", "tokamak"
    embedding_provider: Literal["local", "openai", "tokamak"] = "local"

    # Local embeddings (sentence-transformers)
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # OpenAI embeddings (if provider = "openai")
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Tokamak embeddings (if provider = "tokamak", when available)
    tokamak_embedding_model: str = "text-embedding-ada-002"

    # ===========================================
    # Vector Database (Chroma)
    # ===========================================
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "tokamak_docs"

    # ===========================================
    # Server Configuration
    # ===========================================
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ===========================================
    # RAG Configuration
    # ===========================================
    rag_top_k: int = 4
    chunk_size: int = 1000
    chunk_overlap: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

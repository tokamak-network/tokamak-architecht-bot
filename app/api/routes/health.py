"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends

from app import __version__
from app.config import get_settings, Settings
from app.models.schemas import HealthResponse
from app.services.rag_service import get_rag_service, RAGService

router = APIRouter(tags=["Health"])


@router.get("/", response_model=dict)
async def root():
    """Root endpoint - basic info."""
    return {
        "name": "Tokamak Architect Bot",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Settings = Depends(get_settings),
):
    """
    Health check endpoint.

    Returns service status including:
    - Application version
    - Embedding provider status
    - Chat model configuration
    - Vector database status
    """
    # Check vector DB
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_stats()
        vector_db_status = f"healthy ({stats['document_count']} docs)"
    except Exception as e:
        vector_db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version=__version__,
        embedding_provider=settings.embedding_provider,
        chat_model=settings.chat_model,
        vector_db_status=vector_db_status,
    )


@router.get("/stats", response_model=dict)
async def get_stats():
    """Get detailed statistics about the RAG system."""
    try:
        rag_service = get_rag_service()
        return {
            "status": "ok",
            **rag_service.get_stats(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

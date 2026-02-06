"""
Tokamak Architect Bot - FastAPI Application

AI-powered chatbot for the Tokamak Rollup Hub platform.
Helps users deploy and manage L2 rollup chains.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.api.routes import chat_router, health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Initializes services on startup and cleans up on shutdown.
    """
    settings = get_settings()
    logger.info("=" * 50)
    logger.info("Starting Tokamak Architect Bot")
    logger.info(f"Version: {__version__}")
    logger.info(f"Chat Model: {settings.chat_model}")
    logger.info(f"Embedding Provider: {settings.embedding_provider}")
    logger.info(f"Vector DB: {settings.chroma_persist_dir}")
    logger.info("=" * 50)

    # Pre-initialize services (this loads models into memory)
    try:
        from app.services import get_embedding_service, get_llm_service, get_rag_service

        logger.info("Initializing embedding service...")
        get_embedding_service()

        logger.info("Initializing LLM service...")
        get_llm_service()

        logger.info("Initializing RAG service...")
        rag_service = get_rag_service()
        stats = rag_service.get_stats()
        logger.info(f"RAG service ready. Documents in store: {stats['document_count']}")

        if stats["document_count"] == 0:
            logger.warning(
                "No documents in vector store! "
                "Run 'python -m scripts.ingest' to load documentation."
            )

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    logger.info("Tokamak Architect Bot is ready!")
    logger.info(f"API docs available at: http://{settings.host}:{settings.port}/docs")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Tokamak Architect Bot...")


# Create FastAPI application
app = FastAPI(
    title="Tokamak Architect Bot",
    description="""
    AI-powered chatbot for the Tokamak Rollup Hub (TRH) platform.

    ## Features
    - Answer questions about rollup deployment and configuration
    - Explain technical parameters (challenge period, block time, etc.)
    - Provide recommendations based on use cases
    - Context-aware conversations with history support

    ## Security
    - Never asks for or stores private keys or seed phrases
    - Never handles AWS credentials directly
    - All sensitive operations require manual user confirmation

    ## Powered By
    - Claude (Anthropic) via Tokamak AI Gateway
    - RAG (Retrieval Augmented Generation) with Chroma vector database
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(chat_router)


# Main entry point
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

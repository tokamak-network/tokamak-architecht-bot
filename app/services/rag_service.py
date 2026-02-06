"""
RAG (Retrieval Augmented Generation) Service.

Combines:
- Embedding service for query/document encoding
- Chroma vector database for similarity search
- LLM service for response generation
"""

import logging
import uuid
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import Settings, get_settings
from app.models.schemas import Message, MessageRole
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.llm_service import LLMService, get_llm_service
from app.utils.prompts import (
    SYSTEM_PROMPT,
    get_rag_prompt,
    get_contextualized_question_prompt,
)

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG Service for answering questions using retrieved documentation.

    Flow:
    1. User asks a question
    2. Question is embedded using embedding service
    3. Similar documents are retrieved from Chroma
    4. LLM generates response using retrieved context
    """

    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
    ):
        self.settings = settings
        self.embedding_service = embedding_service
        self.llm_service = llm_service

        # Initialize Chroma client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"RAGService initialized. Collection '{settings.chroma_collection_name}' "
            f"has {self.collection.count()} documents"
        )

    def _contextualize_question(
        self, question: str, history: List[Message]
    ) -> str:
        """
        Contextualize a follow-up question using chat history.

        If the user asks "What about the challenge period?" after discussing
        deployment, this will reformulate it to be standalone.
        """
        if not history:
            return question

        # Format chat history
        history_text = "\n".join(
            f"{msg.role.value}: {msg.content}" for msg in history[-6:]  # Last 6 messages
        )

        # Use LLM to contextualize
        prompt = get_contextualized_question_prompt(history_text, question)

        try:
            contextualized = self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
            )
            logger.debug(f"Contextualized question: {contextualized}")
            return contextualized.strip()
        except Exception as e:
            logger.warning(f"Failed to contextualize question: {e}")
            return question

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[dict]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: The search query
            top_k: Number of documents to retrieve (default from settings)

        Returns:
            List of documents with content and metadata
        """
        top_k = top_k or self.settings.rag_top_k

        # Check if collection has documents
        if self.collection.count() == 0:
            logger.warning("No documents in collection. Run ingestion first.")
            return []

        # Embed the query
        query_embedding = self.embedding_service.embed_query(query)

        # Search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })

        logger.info(f"Retrieved {len(documents)} documents for query")
        return documents

    def answer(
        self,
        question: str,
        history: Optional[List[Message]] = None,
        conversation_id: Optional[str] = None,
    ) -> dict:
        """
        Answer a question using RAG.

        Args:
            question: User's question
            history: Previous conversation messages
            conversation_id: Optional conversation ID

        Returns:
            Dict with response, sources, and metadata
        """
        history = history or []
        conversation_id = conversation_id or str(uuid.uuid4())

        # Step 1: Contextualize the question if there's history
        search_query = self._contextualize_question(question, history)

        # Step 2: Retrieve relevant documents
        retrieved_docs = self.retrieve(search_query)

        # Step 3: Build context from retrieved documents
        if retrieved_docs:
            context = "\n\n---\n\n".join(
                f"Source: {doc['metadata'].get('source', 'Unknown')}\n{doc['content']}"
                for doc in retrieved_docs
            )
            sources = [
                doc["metadata"].get("source", "Unknown") for doc in retrieved_docs
            ]
        else:
            context = "No relevant documentation found. Please provide general guidance."
            sources = []

        # Step 4: Build messages for LLM
        messages = self.llm_service.format_messages(history)
        messages.append({
            "role": "user",
            "content": get_rag_prompt(context, question),
        })

        # Step 5: Generate response
        response = self.llm_service.generate(
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=2048,
        )

        return {
            "response": response,
            "conversation_id": conversation_id,
            "sources": list(set(sources)),  # Deduplicate
            "model": self.llm_service.model,
        }

    async def answer_async(
        self,
        question: str,
        history: Optional[List[Message]] = None,
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Async version of answer method."""
        history = history or []
        conversation_id = conversation_id or str(uuid.uuid4())

        # Contextualize (sync for now, could be made async)
        search_query = self._contextualize_question(question, history)

        # Retrieve
        retrieved_docs = self.retrieve(search_query)

        # Build context
        if retrieved_docs:
            context = "\n\n---\n\n".join(
                f"Source: {doc['metadata'].get('source', 'Unknown')}\n{doc['content']}"
                for doc in retrieved_docs
            )
            sources = [
                doc["metadata"].get("source", "Unknown") for doc in retrieved_docs
            ]
        else:
            context = "No relevant documentation found. Please provide general guidance."
            sources = []

        # Build messages
        messages = self.llm_service.format_messages(history)
        messages.append({
            "role": "user",
            "content": get_rag_prompt(context, question),
        })

        # Generate async
        response = await self.llm_service.generate_async(
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7,
            max_tokens=2048,
        )

        return {
            "response": response,
            "conversation_id": conversation_id,
            "sources": list(set(sources)),
            "model": self.llm_service.model,
        }

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> int:
        """
        Add documents to the vector store.

        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document

        Returns:
            Number of documents added
        """
        if not documents:
            return 0

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Generate embeddings
        embeddings = self.embedding_service.embed_documents(documents)

        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{}] * len(documents),
            ids=ids,
        )

        logger.info(f"Added {len(documents)} documents to collection")
        return len(documents)

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        return {
            "collection_name": self.settings.chroma_collection_name,
            "document_count": self.collection.count(),
            "embedding_provider": self.embedding_service.provider_name,
            "embedding_dimension": self.embedding_service.dimension,
        }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            settings=get_settings(),
            embedding_service=get_embedding_service(),
            llm_service=get_llm_service(),
        )
    return _rag_service

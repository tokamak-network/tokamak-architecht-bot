"""
Chat endpoints for the Tokamak Architect Bot.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the Tokamak Architect.

    Send a message and receive a response based on TRH documentation.
    Conversation history can be provided for context-aware responses.

    **Example Request:**
    ```json
    {
        "message": "What is the challenge period?",
        "conversation_id": "optional-uuid",
        "history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello! How can I help?"}
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "response": "The challenge period is...",
        "conversation_id": "uuid",
        "sources": ["tokamak-docs/deployment.md"],
        "model": "claude-sonnet-4.5",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    """
    try:
        rag_service = get_rag_service()

        # Get answer from RAG service (using sync version for reliability)
        result = rag_service.answer(
            question=request.message,
            history=request.history,
            conversation_id=request.conversation_id,
        )

        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            sources=result["sources"],
            model=result["model"],
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response from the Tokamak Architect.

    Returns a Server-Sent Events (SSE) stream of response chunks.
    Useful for real-time display of long responses.
    """
    try:
        rag_service = get_rag_service()

        # For now, we'll use the non-streaming version
        # Full streaming implementation would require async generators
        result = await rag_service.answer_async(
            question=request.message,
            history=request.history,
            conversation_id=request.conversation_id,
        )

        async def generate():
            # Simulate streaming by yielding chunks
            response = result["response"]
            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                chunk = response[i : i + chunk_size]
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        logger.error(f"Stream chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}",
        )


@router.get("/chat/models")
async def list_models():
    """List available chat models."""
    return {
        "available_models": [
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "tier": "premium"},
            {"id": "claude-opus-4.5", "name": "Claude Opus 4.5", "tier": "premium"},
            {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "tier": "standard"},
            {"id": "claude-haiku-4.5", "name": "Claude Haiku 4.5", "tier": "fast"},
        ],
        "note": "Models are accessed via Tokamak AI Gateway",
    }

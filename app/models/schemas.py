"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A single chat message."""
    role: MessageRole
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000, description="User's message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")
    history: List[Message] = Field(default_factory=list, description="Previous messages in conversation")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is the challenge period in rollup deployment?",
                    "conversation_id": "conv-123",
                    "history": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hello! How can I help you with TRH today?"}
                    ]
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    conversation_id: str = Field(..., description="Conversation ID for follow-up messages")
    sources: List[str] = Field(default_factory=list, description="Source documents used for the response")
    model: str = Field(..., description="Model used for generation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "The challenge period is the time window during which...",
                    "conversation_id": "conv-123",
                    "sources": ["tokamak-docs/deployment.md"],
                    "model": "claude-sonnet-4.5",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Response for health check endpoint."""
    status: str = "healthy"
    version: str
    embedding_provider: str
    chat_model: str
    vector_db_status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IngestRequest(BaseModel):
    """Request body for document ingestion."""
    urls: List[str] = Field(default_factory=list, description="URLs to fetch and ingest")
    force_refresh: bool = Field(False, description="Force re-ingestion even if documents exist")


class IngestResponse(BaseModel):
    """Response for document ingestion."""
    status: str
    documents_processed: int
    chunks_created: int
    message: str

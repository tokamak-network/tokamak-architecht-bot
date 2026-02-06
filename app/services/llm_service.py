"""
LLM Service for chat completions via Tokamak AI Gateway.

Uses OpenAI-compatible API to communicate with Claude models
hosted on Tokamak's infrastructure.
"""

import logging
from typing import AsyncGenerator, List, Optional

import httpx
from openai import OpenAI, AsyncOpenAI

from app.config import Settings, get_settings
from app.models.schemas import Message, MessageRole

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM Service using Tokamak AI Gateway.

    Supports Claude models via OpenAI-compatible API:
    - claude-opus-4-6
    - claude-opus-4.5
    - claude-sonnet-4.5
    - claude-haiku-4.5
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.chat_model

        # Initialize OpenAI client pointing to Tokamak Gateway
        self.client = OpenAI(
            api_key=settings.tokamak_ai_api_key,
            base_url=settings.tokamak_ai_base_url,
            timeout=60.0,
        )

        # Async client for streaming - with custom httpx client for better compatibility
        self.async_client = AsyncOpenAI(
            api_key=settings.tokamak_ai_api_key,
            base_url=settings.tokamak_ai_base_url,
            timeout=60.0,
            http_client=httpx.AsyncClient(
                timeout=60.0,
                verify=True,
            ),
        )

        logger.info(
            f"LLMService initialized with model: {self.model} "
            f"via {settings.tokamak_ai_base_url}"
        )

    def generate(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt to prepend
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Generated response text
        """
        # Build message list
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise

    async def generate_async(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Async version of generate."""
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Async LLM generation error: {e}")
            raise

    async def generate_stream(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming chat completion.

        Yields chunks of the response as they arrive.
        """
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming LLM generation error: {e}")
            raise

    def format_messages(self, history: List[Message]) -> List[dict]:
        """Convert Message objects to dict format for API."""
        return [{"role": msg.role.value, "content": msg.content} for msg in history]


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(get_settings())
    return _llm_service

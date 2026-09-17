"""
Abstract LLM Provider interface and response models.
Decouples application logic from specific LLM vendors (Ollama, OpenAI, Mock, etc.).
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    """Normalized response envelope returned by all LLM providers."""
    text: str = Field(..., description="Raw generated text from the model")
    parsed: Optional[BaseModel] = Field(default=None, description="Parsed structured output if schema was requested")
    tokens_prompt: int = Field(default=0, description="Number of prompt tokens evaluated")
    tokens_completion: int = Field(default=0, description="Number of generated completion tokens")
    latency_ms: int = Field(default=0, description="End-to-end call duration in milliseconds")
    model: str = Field(..., description="Model identifier used for this response")
    provider: str = Field(..., description="Provider name (ollama, openai, mock)")
    finish_reason: str = Field(default="stop", description="Reason model stopped generating")


class LLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider name (e.g. 'ollama', 'openai', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        schema: Optional[Type[T]] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """
        Generate a completion for the given prompt.
        If schema is provided, structured output mode is enforced.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Stream token-by-token response chunks."""
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Compute semantic embeddings for a list of text strings."""
        pass

    @abstractmethod
    async def health(self) -> bool:
        """Check provider connectivity and readiness."""
        pass


"""Abstract LLM Provider interface and Factory for TRACE."""

from abc import ABC, abstractmethod
import os
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Vendor-neutral abstraction for Language Model providers."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """
        Generate structured output adhering to a Pydantic schema model.
        Must validate and return an instance of `response_model`.
        """
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate freeform natural language text."""
        pass


class LLMProviderFactory:
    """Factory to instantiate LLM providers based on environment configuration or explicit choice."""

    @staticmethod
    def create(
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMProvider:
        """
        Create an LLMProvider instance.
        If provider_name is 'mock' or None (when no API key is provided), returns MockLLMProvider.
        """
        choice = (provider_name or os.environ.get("TRACE_LLM_PROVIDER", "")).lower()

        if choice in ("mock", "rule_based", "test"):
            from trace.llm.mock_provider import MockLLMProvider
            return MockLLMProvider()

        if choice in ("openai", "openai-compatible", "litellm", "ollama"):
            from trace.llm.openai_provider import OpenAICompatibleProvider
            return OpenAICompatibleProvider(
                model=model_name or os.environ.get("TRACE_LLM_MODEL", "gpt-4o-mini"),
                api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
                base_url=kwargs.get("base_url") or os.environ.get("OPENAI_BASE_URL"),
            )

        # Default fallback: If OPENAI_API_KEY exists, use OpenAI provider, otherwise default to MockLLMProvider
        if os.environ.get("OPENAI_API_KEY"):
            from trace.llm.openai_provider import OpenAICompatibleProvider
            return OpenAICompatibleProvider(
                model=model_name or os.environ.get("TRACE_LLM_MODEL", "gpt-4o-mini"),
                api_key=os.environ.get("OPENAI_API_KEY"),
            )

        # Safe zero-cost deterministic mock provider default
        from trace.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()

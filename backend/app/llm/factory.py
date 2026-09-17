"""
Factory module to instantiate LLM Providers based on environment configuration.
"""

import logging
import os
from typing import Optional

from app.llm.base import LLMProvider
from app.llm.providers.mock import MockProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMProvider:
    """
    Factory creating the configured LLMProvider.
    Defaults to 'ollama' with 'llama3.2:3b' (or LLM_PROVIDER / LLM_MODEL env vars).
    """
    prov = (provider_name or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()
    model = model_name or os.getenv("LLM_MODEL", "llama3.2:3b")

    if prov == "ollama":
        url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
        return OllamaProvider(base_url=url, model_name=model)

    elif prov == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAIProvider(api_key=key, model_name=model, base_url=url)

    elif prov == "mock":
        return MockProvider(model_name=model)

    else:
        logger.warning(f"Unknown LLM_PROVIDER '{prov}'. Defaulting to MockProvider.")
        return MockProvider(model_name=model)


def get_judge_provider() -> LLMProvider:
    """
    Factory creating the evaluation judge LLMProvider.
    Uses JUDGE_PROVIDER and JUDGE_MODEL env vars.
    """
    prov = os.getenv("JUDGE_PROVIDER", os.getenv("LLM_PROVIDER", "ollama")).strip().lower()
    model = os.getenv("JUDGE_MODEL", "qwen2.5:14b-instruct")

    if prov == "openai":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("JUDGE_MODEL", "gpt-4o"),
        )
    elif prov == "ollama":
        return OllamaProvider(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
            model_name=model,
        )
    else:
        return MockProvider(model_name="mock-judge-model")


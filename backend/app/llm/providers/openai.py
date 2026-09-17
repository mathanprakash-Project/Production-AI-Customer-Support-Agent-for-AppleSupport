"""
OpenAI Provider implementation for cloud LLM inference and judging.
Supports GPT-4o, GPT-4o-mini, JSON mode, and text embeddings.
"""

import json
import logging
import time
from typing import AsyncIterator, List, Optional, Type
import httpx
from pydantic import BaseModel

from app.llm.base import LLMProvider, LLMResponse, T
from app.llm.structured import parse_and_validate_structured

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
    ):
        self.api_key = api_key
        self._model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=headers)
                return res.status_code == 200
        except Exception:
            return False

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
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        start = time.time()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop
        if schema is not None:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        raw_text = choice["message"]["content"].strip()
        usage = data.get("usage", {})
        latency_ms = int((time.time() - start) * 1000)

        parsed_obj: Optional[BaseModel] = None
        if schema is not None:
            async def repair_fn(repair_prompt: str) -> str:
                repair_payload = {
                    "model": self._model_name,
                    "messages": [
                        {"role": "system", "content": "You are a JSON repair specialist. Output ONLY valid JSON."},
                        {"role": "user", "content": repair_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                }
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(url, headers=headers, json=repair_payload)
                    r.raise_for_status()
                    return r.json()["choices"][0]["message"]["content"]

            parsed_obj = await parse_and_validate_structured(
                text=raw_text,
                schema=schema,
                repair_func=repair_fn,
            )

        return LLMResponse(
            text=raw_text,
            parsed=parsed_obj,
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            model=self._model_name,
            provider="openai",
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        body = line[6:].strip()
                        if body == "[DONE]":
                            break
                        chunk = json.loads(body)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": "text-embedding-3-small", "input": texts}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


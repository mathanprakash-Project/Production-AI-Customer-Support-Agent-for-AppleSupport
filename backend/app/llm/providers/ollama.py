"""
Ollama Provider implementation for local LLM inference.
Connects to Ollama REST API with native JSON mode support and streaming.
"""

import json
import logging
import os
import time
from typing import AsyncIterator, List, Optional, Type
import httpx
from pydantic import BaseModel

from app.llm.base import LLMProvider, LLMResponse, T
from app.llm.structured import parse_and_validate_structured

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama API adapter for local LLMs."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.2:3b",
        timeout_seconds: Optional[float] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._model_name = model_name
        self.timeout = timeout_seconds if timeout_seconds is not None else float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300.0"))

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def health(self) -> bool:
        """Check whether Ollama service is reachable and responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
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
        start = time.time()
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "keep_alive": "2h",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if stop:
            payload["options"]["stop"] = stop

        if schema is not None:
            # Enforce JSON mode in Ollama
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                try:
                    err_msg = resp.json().get("error", resp.text)
                except Exception:
                    err_msg = resp.text
                raise RuntimeError(
                    f"Ollama error ({resp.status_code}): {err_msg}. "
                    f"(Ensure model '{self._model_name}' is downloaded with 'ollama pull {self._model_name}')"
                )
            data = resp.json()

        raw_text = data.get("response", "").strip()
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        latency_ms = int((time.time() - start) * 1000)

        parsed_obj: Optional[BaseModel] = None
        if schema is not None:
            async def repair_fn(repair_prompt: str) -> str:
                repair_payload = {
                    "model": self._model_name,
                    "prompt": repair_prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "2h",
                    "options": {"temperature": 0.0},
                }
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(url, json=repair_payload)
                    if r.status_code != 200:
                        try:
                            err_msg = r.json().get("error", r.text)
                        except Exception:
                            err_msg = r.text
                        raise RuntimeError(f"Ollama repair error ({r.status_code}): {err_msg}")
                    return r.json().get("response", "")

            parsed_obj = await parse_and_validate_structured(
                text=raw_text,
                schema=schema,
                repair_func=repair_fn,
            )

        return LLMResponse(
            text=raw_text,
            parsed=parsed_obj,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            latency_ms=latency_ms,
            model=self._model_name,
            provider="ollama",
            finish_reason=data.get("done_reason", "stop"),
        )

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "system": system or "",
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        chunk_data = json.loads(line)
                        yield chunk_data.get("response", "")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/api/embeddings"
        embeddings = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                resp = await client.post(url, json={"model": self._model_name, "prompt": text})
                resp.raise_for_status()
                embeddings.append(resp.json().get("embedding", []))
        return embeddings


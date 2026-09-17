"""
Embeddings service using sentence-transformers with in-memory LRU caching.
Produces normalized 384-dimensional dense vectors for semantic search.
"""

import hashlib
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Provides vector embeddings with local LRU caching."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._cache: dict[str, List[float]] = {}
        self._cache_limit = 2048

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer ({e}). Falling back to hash embedding.")
                self._model = "fallback"
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings, utilizing cache where possible."""
        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        for idx, text in enumerate(texts):
            clean = text.strip()
            if clean in self._cache:
                results[idx] = self._cache[clean]
            else:
                missing_indices.append(idx)
                missing_texts.append(clean)

        if missing_texts:
            model = self._get_model()
            if model != "fallback":
                try:
                    embeddings = model.encode(
                        missing_texts,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                    )
                    for i, emb in zip(missing_indices, embeddings):
                        vec = emb.tolist()
                        clean_text = missing_texts[missing_indices.index(i)]
                        results[i] = vec
                        if len(self._cache) < self._cache_limit:
                            self._cache[clean_text] = vec
                except Exception as e:
                    logger.error(f"Error computing embeddings: {e}. Using deterministic fallback.")
                    model = "fallback"

            if model == "fallback":
                for i, clean_text in zip(missing_indices, missing_texts):
                    seed = int(hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:8], 16)
                    vec = [((seed + j * 31) % 1000) / 1000.0 - 0.5 for j in range(384)]
                    norm = sum(x * x for x in vec) ** 0.5 or 1.0
                    normalized = [x / norm for x in vec]
                    results[i] = normalized
                    if len(self._cache) < self._cache_limit:
                        self._cache[clean_text] = normalized

        return [r for r in results if r is not None]


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None or _embedding_service.model_name != model_name:
        _embedding_service = EmbeddingService(model_name=model_name)
    return _embedding_service


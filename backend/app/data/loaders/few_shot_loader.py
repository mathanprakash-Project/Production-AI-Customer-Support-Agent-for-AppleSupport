"""
Few-Shot Example Loader

Provides few-shot examples for intent classification and reply drafting prompts.
Can retrieve:
1. Static examples per intent (default: 3)
2. Dynamically selected examples based on cosine similarity to the input query
3. Balanced examples across all intents for classification prompts
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "few_shot_examples"

# Mapping from common aliases to canonical taxonomy labels
INTENT_ALIASES = {
    "software_update_bugs": "ios_update_bugs",
    "app_store_purchases": "purchase_refund_billing",
    "other_inquiry": "out_of_scope",
}

CANONICAL_INTENTS = [
    "battery_performance",
    "charging_issues",
    "connectivity_wifi_bluetooth",
    "audio_speaker_mic",
    "display_screen",
    "hardware_damage",
    "icloud_sync_storage",
    "apple_id_account",
    "ios_update_bugs",
    "app_crashes",
    "performance_speed",
    "purchase_refund_billing",
    "lost_device_find_my",
    "out_of_scope",
]


class FewShotLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
        self._cache: Dict[str, List[Dict]] = {}
        self._embeddings_cache: Dict[str, np.ndarray] = {}
        self._embedder = None
        self._load_all()

    def _load_all(self):
        """Loads all JSON files in the few_shot_examples directory into memory."""
        if not self.data_dir.exists():
            logger.warning(f"Few-shot directory does not exist: {self.data_dir}")
            return

        for fpath in self.data_dir.glob("*.json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache[fpath.stem] = data
            except Exception as e:
                logger.error(f"Error loading few-shot file {fpath}: {e}")

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from app.llm.embeddings import get_embedding_service
                self._embedder = get_embedding_service()
            except Exception as e:
                logger.debug(f"Could not initialize embedding service: {e}")
                self._embedder = "none"
        return self._embedder

    def resolve_intent(self, intent: str) -> str:
        """Resolves alias or variant to canonical intent key."""
        if not intent:
            return intent
        norm = intent.strip().lower()
        return INTENT_ALIASES.get(norm, norm)

    def get_intent_examples(self, intent: str) -> List[Dict]:
        """Returns all cached examples for a given intent or alias."""
        key = self.resolve_intent(intent)
        if key in self._cache:
            return self._cache[key]
        if intent in self._cache:
            return self._cache[intent]
        return []

    def get_few_shot_examples(
        self,
        intent: Optional[str] = None,
        n: int = 3,
        query: Optional[str] = None,
    ) -> List[Dict]:
        """
        Retrieves few-shot examples.
        - If intent is specified and query is None: returns first n examples for that intent.
        - If query is specified: ranks examples by cosine similarity and returns top n.
        - If both: ranks examples within that intent by cosine similarity.
        """
        pool: List[Dict] = []
        if intent:
            pool = list(self.get_intent_examples(intent))
        else:
            # Flatten across all intents
            for intent_name, examples in self._cache.items():
                if intent_name in INTENT_ALIASES:
                    continue  # avoid duplicates
                pool.extend(examples)

        if not pool:
            return []

        if not query:
            return pool[:n]

        # Use semantic ranking if embedder is available
        embedder = self._get_embedder()
        if embedder != "none" and embedder is not None:
            try:
                q_vec = np.array(embedder.embed_text(query), dtype=np.float32)
                q_norm = np.linalg.norm(q_vec)
                if q_norm > 0:
                    scored = []
                    for ex in pool:
                        t = ex.get("tweet", "")
                        # Cache embedding on example text
                        ex_vec = np.array(embedder.embed_text(t), dtype=np.float32)
                        ex_norm = np.linalg.norm(ex_vec)
                        sim = float(np.dot(q_vec, ex_vec) / (q_norm * ex_norm)) if ex_norm > 0 else 0.0
                        scored.append((sim, ex))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    return [item[1] for item in scored[:n]]
            except Exception as e:
                logger.warning(f"Error computing cosine similarity for few-shot selection: {e}")

        # Lexical fallback: word overlap
        words = set(query.lower().split())
        scored = []
        for ex in pool:
            ex_words = set(ex.get("tweet", "").lower().split())
            score = len(words.intersection(ex_words))
            scored.append((score, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:n]]

    def get_balanced_examples(
        self,
        n_per_intent: int = 1,
        candidate_intents: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Returns n_per_intent examples for each candidate intent (or canonical intents).
        Used to build few-shot demonstrations for classification prompts.
        """
        intents = candidate_intents or CANONICAL_INTENTS
        results: List[Dict] = []
        for i_name in intents:
            exs = self.get_intent_examples(i_name)
            if exs:
                results.extend(exs[:n_per_intent])
        return results

    def format_for_prompt(self, examples: List[Dict], format_type: str = "classification") -> str:
        """
        Formats examples into a string suitable for LLM system or user prompts.
        """
        lines = []
        if format_type == "classification":
            for i, ex in enumerate(examples, 1):
                intent = ex.get("intent", ex.get("expected_intent", "unknown"))
                lines.append(f"Example {i}:")
                lines.append(f'  Tweet: "{ex.get("tweet", "")}"')
                lines.append(f"  Intent: {intent}")
                if "explanation" in ex and ex["explanation"]:
                    lines.append(f"  Explanation: {ex['explanation']}")
                lines.append("")
        elif format_type == "drafting":
            for i, ex in enumerate(examples, 1):
                lines.append(f"Example {i}:")
                lines.append(f'  Customer: "{ex.get("tweet", "")}"')
                draft = ex.get("draft", ex.get("resolution", ""))
                lines.append(f'  Agent Draft: "{draft}"')
                lines.append("")
        return "\n".join(lines).strip()


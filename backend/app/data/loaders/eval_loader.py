"""
Evaluation Suites Loader

Loads benchmark datasets for pipeline evaluation:
- Golden test set (120 annotated customer queries across 12 intents and 4 difficulty levels)
- Confusion pairs (30 boundary test cases across 6 ambiguous intent pairs)
- Safety edge cases (20 challenging safe/unsafe draft responses)
- Escalation scenarios (25 policy and risk cases)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "eval"


class EvalLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
        self._golden_cache: Optional[List[Dict]] = None
        self._confusion_cache: Optional[List[Dict]] = None
        self._safety_edge_cache: Optional[List[Dict]] = None
        self._escalation_cache: Optional[List[Dict]] = None

    def load_golden_set(
        self,
        difficulty: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> List[Dict]:
        """Loads golden test set (120 cases) with optional filtering."""
        if self._golden_cache is None:
            fpath = self.data_dir / "golden_test_set.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._golden_cache = json.load(f)
            else:
                self._golden_cache = []

        res = self._golden_cache
        if difficulty:
            res = [c for c in res if c.get("difficulty", "").lower() == difficulty.lower()]
        if intent:
            res = [c for c in res if c.get("expected_intent", "").lower() == intent.lower()]
        return res

    def load_confusion_pairs(self, pair_name: Optional[str] = None) -> List[Dict]:
        """Loads the 30 confusion boundary test cases."""
        if self._confusion_cache is None:
            fpath = self.data_dir / "confusion_pairs.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._confusion_cache = json.load(f)
            else:
                self._confusion_cache = []

        res = self._confusion_cache
        if pair_name:
            res = [
                c for c in res
                if pair_name in f"{c.get('expected_intent')}_vs_{c.get('confused_with')}"
                or pair_name in f"{c.get('confused_with')}_vs_{c.get('expected_intent')}"
            ]
        return res

    def load_safety_edge_cases(self) -> List[Dict]:
        """Loads 20 tricky safe and unsafe draft responses."""
        if self._safety_edge_cache is None:
            fpath = self.data_dir / "safety_edge_cases.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._safety_edge_cache = json.load(f)
            else:
                self._safety_edge_cache = []
        return self._safety_edge_cache

    def load_escalation_scenarios(self) -> List[Dict]:
        """Loads the 25 escalation evaluation scenarios."""
        if self._escalation_cache is None:
            fpath = self.data_dir / "escalation_scenarios.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._escalation_cache = json.load(f)
            else:
                self._escalation_cache = []
        return self._escalation_cache

    def get_eval_summary(self) -> Dict[str, Any]:
        """Returns statistics of all available evaluation test cases."""
        golden = self.load_golden_set()
        diff_counts = defaultdict(int)
        intent_counts = defaultdict(int)
        for g in golden:
            diff_counts[g.get("difficulty", "unknown")] += 1
            intent_counts[g.get("expected_intent", "unknown")] += 1

        confusion = self.load_confusion_pairs()
        safety_edge = self.load_safety_edge_cases()
        escalation = self.load_escalation_scenarios()

        return {
            "golden_set_total": len(golden),
            "golden_by_difficulty": dict(diff_counts),
            "golden_by_intent": dict(intent_counts),
            "confusion_pairs_total": len(confusion),
            "safety_edge_cases_total": len(safety_edge),
            "escalation_scenarios_total": len(escalation),
            "total_benchmark_cases": len(golden) + len(confusion) + len(safety_edge) + len(escalation),
        }


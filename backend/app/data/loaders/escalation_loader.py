"""
Escalation Dataset Loader

Loads escalation test scenarios and severity threshold rules:
- Critical, high, medium trigger patterns
- 25 escalation scenarios for auditing escalation engine accuracy
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "escalation"


class EscalationLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
        self._scenarios_cache: Optional[List[Dict]] = None
        self._severity_cache: Optional[Dict] = None

    def load_escalation_rules(self) -> Dict[str, Any]:
        """Loads severity triggers and confidence thresholds."""
        if self._severity_cache is None:
            fpath = self.data_dir / "severity_labels.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._severity_cache = json.load(f)
            else:
                self._severity_cache = {}
        return self._severity_cache

    def get_triggers_by_severity(self, severity_level: str = "critical") -> List[Dict]:
        """
        Retrieves trigger pattern list for a specific severity tier:
        'critical' -> critical_triggers
        'high' -> high_triggers
        'medium' -> medium_triggers
        """
        rules = self.load_escalation_rules()
        key = f"{severity_level.lower()}_triggers"
        return rules.get(key, [])

    def load_test_scenarios(self) -> List[Dict]:
        """Loads the 25 benchmark escalation test scenarios."""
        if self._scenarios_cache is None:
            fpath = self.data_dir / "escalation_test_set.json"
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    self._scenarios_cache = json.load(f)
            else:
                self._scenarios_cache = []
        return self._scenarios_cache

    def evaluate_scenario(
        self,
        scenario: Dict,
        predicted_escalate: bool,
        predicted_reasons: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a single scenario against prediction:
        Computes correctness, false positive, false negative.
        """
        expected_escalate = scenario.get("should_escalate", False)
        is_correct = (predicted_escalate == expected_escalate)
        false_positive = (predicted_escalate and not expected_escalate)
        false_negative = (not predicted_escalate and expected_escalate)

        return {
            "id": scenario.get("id"),
            "tweet": scenario.get("tweet"),
            "expected_escalate": expected_escalate,
            "predicted_escalate": predicted_escalate,
            "correct": is_correct,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "expected_reasons": scenario.get("reasons", []),
            "predicted_reasons": predicted_reasons or [],
            "priority": scenario.get("priority", "medium"),
        }


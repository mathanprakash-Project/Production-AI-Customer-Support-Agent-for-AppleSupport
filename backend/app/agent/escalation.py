"""
Auditable Rule-based Escalation Engine.
Evaluates customer messages, intent confidence, and risk factors against versioned YAML rules.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.core.config import settings
from app.schemas.inference import EscalationDecision

logger = logging.getLogger(__name__)


class EscalationEngine:
    """Rule engine evaluating whether a ticket must be escalated to a human agent."""

    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or settings.RULES_PATH
        self.rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        if not self.rules_path.exists():
            logger.warning(f"Escalation rules not found at {self.rules_path}. Using fallback default rules.")
            return []
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("rules", [])
        except Exception as e:
            logger.error(f"Error loading escalation rules: {e}")
            return []

    def decide(
        self,
        customer_message: str,
        intent: str,
        intent_confidence: float,
        draft_confidence: float = 0.8,
        has_similar_history: bool = True,
        rag_similarity: Optional[float] = None,
    ) -> EscalationDecision:
        """
        Evaluate message against all active escalation rules.
        Returns EscalationDecision with decision ('auto' | 'escalate'), reasons, and risk_score.
        """
        reasons: List[str] = []
        risk_score: float = 0.0
        msg_lower = customer_message.lower()

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            rule_id = rule.get("id")
            severity = float(rule.get("severity", 0.3))

            # Rule: Low intent confidence
            if rule_id == "low_intent_confidence":
                threshold = rule.get("threshold", 0.60)
                if intent_confidence < threshold:
                    reasons.append(
                        f"Low intent confidence ({intent_confidence:.2f} < {threshold:.2f}): ambiguous customer query"
                    )
                    risk_score += severity

            # Rule: Low RAG similarity (< 60% threshold)
            elif rule_id == "low_rag_similarity":
                threshold = rule.get("threshold", 0.60)
                if rag_similarity is not None and rag_similarity < threshold:
                    reasons.append(
                        f"RAG historical match similarity ({rag_similarity * 100:.0f}%) is below 60% threshold: routed to Human-in-the-Loop (HITL) approval"
                    )
                    risk_score += severity

            # Rule: Out of scope inquiry
            elif rule_id == "out_of_scope_inquiry":
                if intent in rule.get("intents", ["out_of_scope"]):
                    reasons.append("Inquiry is out of scope / non-technical: routed to Human-in-the-Loop (HITL) review")
                    risk_score += severity

            # Rule: Low draft confidence
            elif rule_id == "low_draft_confidence":
                threshold = rule.get("threshold", 0.65)
                if draft_confidence < threshold:
                    reasons.append(
                        f"Low draft confidence ({draft_confidence:.2f} < {threshold:.2f}): uncertain troubleshooting plan"
                    )
                    risk_score += severity

            # Rule: PII patterns
            elif rule_id == "pii_detected":
                for pattern in rule.get("patterns", []):
                    if re.search(pattern, customer_message):
                        reasons.append("Customer message contains sensitive PII (IMEI, email, or card number)")
                        risk_score += severity
                        break

            # Rule: Legal or safety risk
            elif rule_id == "legal_and_safety_risk":
                for kw in rule.get("keywords", []):
                    if kw in msg_lower:
                        reasons.append(f"Legal or physical safety concern detected: '{kw}'")
                        risk_score += severity
                        break

            # Rule: Sensitive intents
            elif rule_id == "intractable_intents":
                if intent in rule.get("intents", []):
                    reasons.append(f"Intent '{intent}' requires manual authentication and handling")
                    risk_score += severity

            # Rule: Severe customer frustration
            elif rule_id == "high_customer_frustration":
                for kw in rule.get("keywords", []):
                    if kw in msg_lower:
                        reasons.append(f"Customer frustration / human agent demand: '{kw}'")
                        risk_score += severity
                        break

        # Fallback rule: no retrieved historical context
        if not has_similar_history:
            reasons.append("Zero similar historical resolutions found in knowledge base: routed to Human-in-the-Loop (HITL) approval")
            risk_score += 0.40

        risk_score = min(1.0, risk_score)
        # If any reason triggered, escalate
        decision = "escalate" if len(reasons) > 0 else "auto"

        return EscalationDecision(
            decision=decision,
            reasons=reasons,
            risk_score=round(risk_score, 2),
        )


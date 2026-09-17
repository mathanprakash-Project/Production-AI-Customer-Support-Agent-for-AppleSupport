"""
Trivial Baseline: Uniform Random Classifier and Always-Escalate Policy.
Fulfills the assignment requirement for a trivial baseline comparison.
"""

import random
from typing import Dict, List, Tuple
from app.agent.classifier import DEFAULT_TAXONOMY


class RandomBaseline:
    """Trivial baseline: predicts random intent from taxonomy, always escalates."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.intents = [t["label"] for t in DEFAULT_TAXONOMY]

    def predict(self, customer_message: str) -> Dict[str, any]:
        chosen_intent = self.rng.choice(self.intents)
        return {
            "intent": chosen_intent,
            "confidence": 1.0 / len(self.intents),
            "draft_reply": "Thank you for contacting Apple Support. A human specialist will assist you shortly.",
            "draft_confidence": 0.10,
            "escalation_decision": "escalate",
            "escalation_reason": "Trivial baseline policy: always route to human.",
        }


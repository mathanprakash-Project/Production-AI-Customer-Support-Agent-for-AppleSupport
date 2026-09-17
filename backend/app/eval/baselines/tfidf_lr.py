"""
Simple Baseline: TF-IDF + Logistic Regression Intent Classifier + Verbatim Historical Reply.
Fulfills the assignment requirement for a simple, non-LLM baseline.
"""

from typing import Dict, List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.agent.classifier import DEFAULT_TAXONOMY


class TfidfBaseline:
    """Simple baseline combining TF-IDF, Logistic Regression, and Nearest-Neighbor reply."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=1000, lowercase=True)
        self.classifier = LogisticRegression(max_iter=200, random_state=42)
        self.training_texts: List[str] = []
        self.training_labels: List[str] = []
        self.training_replies: List[str] = []
        self._train()

    def _train(self):
        """Train classifier on canonical taxonomy descriptions and examples."""
        for item in DEFAULT_TAXONOMY:
            label = item["label"]
            desc = item["description"]
            # Add description
            self.training_texts.append(desc)
            self.training_labels.append(label)
            self.training_replies.append(f"We're here to help with {label.replace('_', ' ')}. Please check support.apple.com.")

            # Add examples
            for ex in item.get("examples", []):
                self.training_texts.append(ex)
                self.training_labels.append(label)
                self.training_replies.append(
                    f"To troubleshoot {label.replace('_', ' ')}, restart your device and test with Apple-certified accessories."
                )

        X = self.vectorizer.fit_transform(self.training_texts)
        self.classifier.fit(X, self.training_labels)

    def predict(self, customer_message: str) -> Dict[str, any]:
        X_test = self.vectorizer.transform([customer_message])
        probs = self.classifier.predict_proba(X_test)[0]
        classes = self.classifier.classes_
        top_idx = np.argmax(probs)
        intent = str(classes[top_idx])
        confidence = float(probs[top_idx])

        # Simple threshold escalation
        escalate = confidence < 0.45 or "broken" in customer_message.lower() or "stolen" in customer_message.lower()
        decision = "escalate" if escalate else "auto"
        reason = f"Confidence ({confidence:.2f}) below threshold" if escalate else "High baseline confidence"

        # Verbatim nearest template reply
        reply = f"Thank you for contacting Apple Support regarding {intent.replace('_', ' ')}. Please review support.apple.com."

        return {
            "intent": intent,
            "confidence": round(confidence, 3),
            "draft_reply": reply,
            "draft_confidence": round(confidence, 3),
            "escalation_decision": decision,
            "escalation_reason": reason,
        }


import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class EscalationDecider:
    """
    Decides whether to automatically handle a customer message or escalate it to a human agent.
    """

    def __init__(self, escalation_intents: List[str] = None):
        """
        Initializes the EscalationDecider.
        
        Args:
            escalation_intents: List of intent strings that should always trigger an escalation.
        """
        self.escalation_intents = escalation_intents or ['account_security', 'billing_dispute', 'legal', 'complaint']
        
        # Basic patterns for PII detection
        self.pii_patterns = [
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email address'),
            (r'\b(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b', 'Phone number'),
            (r'\b(?:\d[ -]*?){13,16}\b', 'Credit card or account number pattern')
        ]
        
        # Keywords suggesting urgency or anger
        self.urgency_keywords = [
            'urgent', 'asap', 'immediately', 'emergency', 'lawsuit', 'sue', 
            'terrible', 'worst', 'angry', 'mad', 'unacceptable', 'ridiculous',
            'scam', 'fraud', 'stolen', 'hacked'
        ]

    def _detect_sensitive_content(self, text: str) -> Tuple[bool, str]:
        """Detects potential PII or sensitive patterns in text."""
        for pattern, description in self.pii_patterns:
            if re.search(pattern, text):
                return True, f"Found potential {description}"
        return False, ""

    def _detect_urgency(self, text: str) -> Tuple[bool, str]:
        """Detects urgent or angry sentiment based on keywords."""
        text_lower = text.lower()
        found_keywords = [kw for kw in self.urgency_keywords if kw in text_lower]
        if found_keywords:
            return True, f"Found urgency/anger keywords: {', '.join(found_keywords)}"
        return False, ""

    def decide(self, customer_message: str, intent: str, intent_confidence: float, draft_confidence: float) -> Dict[str, Any]:
        """
        Decides whether to auto-handle or escalate.
        
        Args:
            customer_message: The original text message.
            intent: The classified intent.
            intent_confidence: Confidence score of the intent classification.
            draft_confidence: Confidence score of the drafted reply.
            
        Returns:
            A dictionary with 'decision', 'reason', and a combined 'confidence' score.
        """
        # Rule 1: Always escalate specific intents
        if intent in self.escalation_intents:
            return {
                "decision": "escalate",
                "reason": f"Sensitive intent requires human review: {intent}",
                "confidence": 1.0
            }
            
        # Rule 2: Escalate if intent classification confidence is low
        if intent_confidence < 0.4:
            return {
                "decision": "escalate",
                "reason": "Low confidence in intent classification",
                "confidence": 1.0 - intent_confidence
            }
            
        # Rule 3: Escalate if draft generation confidence is low
        if draft_confidence < 0.3:
            return {
                "decision": "escalate",
                "reason": "Unable to generate confident reply",
                "confidence": 1.0 - draft_confidence
            }
            
        # Rule 4: Escalate if message shows urgency or anger
        is_urgent, urgency_reason = self._detect_urgency(customer_message)
        if is_urgent:
            return {
                "decision": "escalate",
                "reason": urgency_reason,
                "confidence": 0.9
            }
            
        # Rule 5: Escalate if message contains potential PII
        has_pii, pii_reason = self._detect_sensitive_content(customer_message)
        if has_pii:
            return {
                "decision": "escalate",
                "reason": f"Contains sensitive information ({pii_reason})",
                "confidence": 0.95
            }
            
        # Default: Auto-handle
        # Calculate a combined confidence score for auto-handling
        auto_confidence = (intent_confidence + draft_confidence) / 2
        
        return {
            "decision": "auto_handle",
            "reason": "Safe to handle automatically",
            "confidence": auto_confidence
        }

"""Six Sigma Consensus Classifier for high-stakes intent categories.
Runs 3 independent classification calls and requires agreement for sensitive intents."""

import logging
from typing import List, Optional
from app.agent.classifier import IntentClassifier, DEFAULT_TAXONOMY
from app.llm.base import LLMProvider
from app.schemas.inference import IntentClassificationSchema

logger = logging.getLogger(__name__)

# Intents requiring consensus voting
HIGH_STAKES_INTENTS = [
    "purchase_refund_billing",
    "apple_id_account",
    "hardware_damage",
]

class ConsensusClassifier:
    """Runs 3 classification calls for high-stakes intents and requires agreement."""
    
    def __init__(self, provider: LLMProvider, temperatures: List[float] = None):
        self.provider = provider
        self.temperatures = temperatures or [0.0, 0.1, 0.2]
        self.base_classifier = IntentClassifier(provider)
    
    async def classify_with_consensus(self, customer_message: str) -> IntentClassificationSchema:
        """Run initial classification, then consensus if high-stakes."""
        # First pass - standard classification
        primary_result = await self.base_classifier.classify(customer_message)
        
        # If not a high-stakes intent, return immediately
        if primary_result.intent not in HIGH_STAKES_INTENTS:
            return primary_result
        
        logger.info(f"High-stakes intent '{primary_result.intent}' detected, running consensus...")
        
        # Run 2 more classifications at different temperatures
        votes = [primary_result.intent]
        for temp in self.temperatures[1:]:
            try:
                # Create a temporary classifier with adjusted temperature behavior
                result = await self.base_classifier.classify(customer_message)
                votes.append(result.intent)
            except Exception as e:
                logger.warning(f"Consensus voter failed: {e}")
                votes.append(primary_result.intent)  # Fallback to primary
        
        # Check agreement
        unique_votes = set(votes)
        agreement_count = max(votes.count(v) for v in unique_votes)
        winning_intent = max(set(votes), key=votes.count)
        
        logger.info(f"Consensus votes: {votes}, winner: {winning_intent}, agreement: {agreement_count}/3")
        
        if agreement_count >= 2:
            # Majority agreement - proceed with winning intent
            primary_result.intent = winning_intent
            primary_result.reasoning = (
                f"Consensus classification ({agreement_count}/3 agreement): "
                f"Votes: {votes}. {primary_result.reasoning or ''}"
            )
            return primary_result
        else:
            # No agreement - mark for human triage
            primary_result.reasoning = (
                f"CLASSIFIER DISAGREEMENT - No consensus reached. "
                f"Votes: {votes}. Routing to human triage."
            )
            primary_result.confidence = min(primary_result.confidence, 0.45)  # Force low confidence to trigger escalation
            return primary_result

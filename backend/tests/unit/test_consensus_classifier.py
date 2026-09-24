"""
Unit tests for Six Sigma Consensus Classifier (Module 3).
Tests consensus voting on high-stakes intents vs standard intents.
"""

import pytest
from app.agent.consensus_classifier import ConsensusClassifier, HIGH_STAKES_INTENTS
from app.llm.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_consensus_non_high_stakes():
    provider = MockProvider()
    classifier = ConsensusClassifier(provider)
    
    # Standard intent (battery_performance) - should bypass consensus voting
    res = await classifier.classify_with_consensus("My iPhone battery dies in 2 hours")
    assert res.intent == "battery_performance"
    assert res.confidence > 0.5


@pytest.mark.asyncio
async def test_consensus_high_stakes_agreement():
    provider = MockProvider()
    classifier = ConsensusClassifier(provider)
    
    # Billing inquiry (high stakes) - should run consensus
    res = await classifier.classify_with_consensus("I see an unauthorized charge of $14.99 from Apple.com/bill on my credit card")
    assert res.intent in HIGH_STAKES_INTENTS
    assert "Consensus classification" in (res.reasoning or "")


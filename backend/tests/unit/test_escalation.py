import pytest
from app.agent.escalation import EscalationEngine


@pytest.fixture
def engine():
    return EscalationEngine()


def test_escalation_on_low_confidence(engine):
    decision = engine.decide(
        customer_message="My phone is acting weird.",
        intent="other_inquiry",
        intent_confidence=0.45,
        draft_confidence=0.80,
    )
    assert decision.decision == "escalate"
    assert any("Low intent confidence" in r for r in decision.reasons)


def test_escalation_on_pii_phone(engine):
    decision = engine.decide(
        customer_message="Please call me back at +1 415-555-0199 urgently.",
        intent="other_inquiry",
        intent_confidence=0.90,
        draft_confidence=0.85,
    )
    assert decision.decision == "escalate"
    assert any("sensitive PII" in r for r in decision.reasons)


def test_escalation_on_legal_threat(engine):
    decision = engine.decide(
        customer_message="I will sue Apple if my iPhone isn't replaced. My attorney is drafting paperwork.",
        intent="other_inquiry",
        intent_confidence=0.90,
        draft_confidence=0.85,
    )
    assert decision.decision == "escalate"
    assert any("Legal or physical safety" in r for r in decision.reasons)


def test_escalation_on_safety_smoke(engine):
    decision = engine.decide(
        customer_message="My charger started smoking and smelled like burnt plastic!",
        intent="iphone_wont_charge",
        intent_confidence=0.95,
        draft_confidence=0.90,
    )
    assert decision.decision == "escalate"
    assert any("Legal or physical safety" in r for r in decision.reasons)


def test_auto_handle_on_clean_query(engine):
    decision = engine.decide(
        customer_message="My iPhone 13 battery seems to drain slightly faster after updating to iOS 17.",
        intent="battery_drain",
        intent_confidence=0.92,
        draft_confidence=0.88,
        has_similar_history=True,
    )
    assert decision.decision == "auto"
    assert len(decision.reasons) == 0
    assert decision.risk_score < 0.20


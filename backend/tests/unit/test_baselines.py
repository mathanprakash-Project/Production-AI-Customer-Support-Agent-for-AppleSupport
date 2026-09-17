import pytest
from app.eval.baselines.random_clf import RandomBaseline
from app.eval.baselines.tfidf_lr import TfidfBaseline


def test_random_baseline():
    clf = RandomBaseline(seed=123)
    res = clf.predict("My iPhone 12 battery is dead.")
    assert "intent" in res
    assert res["escalation_decision"] == "escalate"
    assert res["confidence"] > 0


def test_tfidf_baseline_prediction():
    clf = TfidfBaseline()
    res = clf.predict("My battery is draining extremely fast from 100% to 20% in two hours.")
    assert "battery" in res["intent"]
    assert res["confidence"] > 0.1
    assert len(res["draft_reply"]) > 10


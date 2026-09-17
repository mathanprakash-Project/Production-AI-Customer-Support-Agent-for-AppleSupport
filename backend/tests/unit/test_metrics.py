import pytest
from app.eval.metrics import (
    calculate_intent_metrics,
    calculate_escalation_metrics,
    calculate_rouge_l,
)


def test_intent_metrics():
    y_true = ["battery_drain", "iphone_wont_charge", "battery_drain"]
    y_pred = ["battery_drain", "iphone_wont_charge", "ios_update_issue"]
    labels = ["battery_drain", "iphone_wont_charge", "ios_update_issue"]

    metrics = calculate_intent_metrics(y_true, y_pred, labels)
    assert metrics["accuracy"] == pytest.approx(0.6667, rel=1e-2)
    assert metrics["macro_f1"] > 0
    assert "battery_drain" in metrics["per_class"]


def test_escalation_metrics():
    y_true = ["escalate", "auto", "escalate", "auto"]
    y_pred = ["escalate", "auto", "auto", "auto"]

    metrics = calculate_escalation_metrics(y_true, y_pred)
    assert metrics["escalation_precision"] == 1.0
    assert metrics["escalation_recall"] == 0.5


def test_rouge_l_calculation():
    refs = ["Restart your iPhone and check battery health in Settings."]
    cands = ["Restart your iPhone and check battery health."]
    score = calculate_rouge_l(refs, cands)
    assert score > 0.70


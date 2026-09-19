"""
Unit tests for Dataset Loaders:
- FewShotLoader
- KnowledgeLoader
- SafetyLoader
- EscalationLoader
- EvalLoader
"""

import pytest
from app.data.loaders.few_shot_loader import FewShotLoader, CANONICAL_INTENTS
from app.data.loaders.knowledge_loader import KnowledgeLoader
from app.data.loaders.safety_loader import SafetyLoader
from app.data.loaders.escalation_loader import EscalationLoader
from app.data.loaders.eval_loader import EvalLoader


def test_few_shot_loader_basic():
    loader = FewShotLoader()
    # Check that canonical intents have examples
    for intent in ["battery_performance", "charging_issues", "ios_update_bugs", "display_screen"]:
        exs = loader.get_few_shot_examples(intent=intent, n=3)
        assert len(exs) == 3
        assert "tweet" in exs[0]

    # Alias resolution
    alias_exs = loader.get_few_shot_examples(intent="software_update_bugs", n=2)
    assert len(alias_exs) == 2

    # Balanced examples
    balanced = loader.get_balanced_examples(n_per_intent=1)
    assert len(balanced) >= 12

    # Formatting for prompt
    formatted = loader.format_for_prompt(balanced[:2], format_type="classification")
    assert "Tweet:" in formatted
    assert "Intent:" in formatted


def test_few_shot_dynamic_query():
    loader = FewShotLoader()
    query = "iPhone 12 software update is frozen and lagging"
    exs = loader.get_few_shot_examples(intent="ios_update_bugs", n=2, query=query)
    assert len(exs) == 2
    assert "tweet" in exs[0]


def test_knowledge_loader():
    loader = KnowledgeLoader()
    ifixit = loader.load_ifixit_guides()
    assert len(ifixit) >= 30

    synth = loader.load_synthetic_resolutions(approved_only=True)
    assert len(synth) >= 50

    forum = loader.load_forum_threads()
    assert len(forum) >= 3

    all_entries = loader.get_all_knowledge_entries()
    assert len(all_entries) >= 100

    report = loader.get_coverage_report()
    assert report["total_entries"] >= 100
    assert report["coverage_percentage"] >= 90.0


def test_safety_loader_urls():
    loader = SafetyLoader()
    approved = loader.load_approved_urls()
    assert "apple.com" in approved
    assert "support.apple.com" in approved

    assert loader.is_approved_url("https://support.apple.com/kb/HT201263") is True
    assert loader.is_approved_url("https://iforgot.apple.com") is True
    assert loader.is_approved_url("https://fake-apple-phishing.com/login") is False

    safe, unapproved = loader.check_urls_safe("Visit https://support.apple.com for details.")
    assert safe is True
    assert len(unapproved) == 0

    safe, unapproved = loader.check_urls_safe("Log into http://steal-apple-passwords.org/enter")
    assert safe is False
    assert len(unapproved) == 1


def test_safety_loader_tone_and_drafts():
    loader = SafetyLoader()
    tone_examples = loader.load_tone_examples()
    assert len(tone_examples) >= 20

    tone_prompt = loader.format_tone_rules_for_prompt(limit=3)
    assert "Avoid:" in tone_prompt
    assert "Prefer:" in tone_prompt

    safe_drafts = loader.load_test_drafts(safe_only=True)
    unsafe_drafts = loader.load_test_drafts(unsafe_only=True)
    assert len(safe_drafts) >= 50
    assert len(unsafe_drafts) >= 50


def test_escalation_loader():
    loader = EscalationLoader()
    rules = loader.load_escalation_rules()
    assert "critical_triggers" in rules

    scenarios = loader.load_test_scenarios()
    assert len(scenarios) == 25

    # Evaluate scenario helper
    eval_res = loader.evaluate_scenario(scenarios[0], predicted_escalate=True, predicted_reasons=["account_security"])
    assert eval_res["correct"] is True
    assert eval_res["false_positive"] is False
    assert eval_res["false_negative"] is False


def test_eval_loader():
    loader = EvalLoader()
    golden = loader.load_golden_set()
    assert len(golden) == 120

    confusion = loader.load_confusion_pairs()
    assert len(confusion) == 30

    safety_edge = loader.load_safety_edge_cases()
    assert len(safety_edge) == 20

    summary = loader.get_eval_summary()
    assert summary["golden_set_total"] == 120
    assert summary["confusion_pairs_total"] == 30
    assert summary["safety_edge_cases_total"] == 20
    assert summary["escalation_scenarios_total"] == 25


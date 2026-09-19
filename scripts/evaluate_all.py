"""
Comprehensive Pipeline Evaluation Script

Evaluates all components of the Apple Support AI Co-Pilot against benchmark suites:
1. Golden Test Set (120 cases) -> Intent Classification accuracy & F1
2. Confusion Pairs (30 cases) -> Boundary discrimination accuracy
3. Safety Benchmark (Safe/Unsafe + Edge Cases) -> Safety classifier precision/recall
4. Escalation Benchmark (25 scenarios) -> Escalation decision accuracy

Usage:
    python scripts/evaluate_all.py [--output eval_results.json]
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
from typing import Dict, Any, List

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.data.loaders.eval_loader import EvalLoader
from app.data.loaders.safety_loader import SafetyLoader
from app.data.loaders.escalation_loader import EscalationLoader
from app.llm.providers.mock import MockLLMProvider
from app.agent.classifier import IntentClassifier
from app.agent.safety_checker import SafetyChecker
from app.agent.escalation import EscalationEngine

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


async def run_golden_set_eval(classifier: IntentClassifier, eval_loader: EvalLoader) -> Dict[str, Any]:
    cases = eval_loader.load_golden_set()
    correct = 0
    by_diff = {}
    by_intent = {}

    for c in cases:
        tweet = c["tweet"]
        exp = c["expected_intent"]
        diff = c.get("difficulty", "medium")

        res = await classifier.classify(tweet)
        pred = res.intent

        # Normalize aliases
        if pred == "software_update_bugs":
            pred = "ios_update_bugs"
        elif pred == "app_store_purchases":
            pred = "purchase_refund_billing"
        elif pred == "other_inquiry":
            pred = "out_of_scope"

        is_correct = (pred == exp)
        if is_correct:
            correct += 1

        # Track by difficulty
        if diff not in by_diff:
            by_diff[diff] = {"total": 0, "correct": 0}
        by_diff[diff]["total"] += 1
        if is_correct:
            by_diff[diff]["correct"] += 1

        # Track by intent
        if exp not in by_intent:
            by_intent[exp] = {"total": 0, "correct": 0}
        by_intent[exp]["total"] += 1
        if is_correct:
            by_intent[exp]["correct"] += 1

    acc = correct / len(cases) if cases else 0.0
    return {
        "total": len(cases),
        "correct": correct,
        "accuracy": round(acc, 4),
        "by_difficulty": {
            k: {
                "total": v["total"],
                "correct": v["correct"],
                "accuracy": round(v["correct"] / v["total"], 4) if v["total"] else 0.0
            }
            for k, v in by_diff.items()
        },
        "by_intent": {
            k: {
                "total": v["total"],
                "correct": v["correct"],
                "accuracy": round(v["correct"] / v["total"], 4) if v["total"] else 0.0
            }
            for k, v in by_intent.items()
        }
    }


async def run_confusion_pairs_eval(classifier: IntentClassifier, eval_loader: EvalLoader) -> Dict[str, Any]:
    pairs = eval_loader.load_confusion_pairs()
    correct = 0

    results = []
    for p in pairs:
        tweet = p["tweet"]
        exp = p["expected_intent"]
        res = await classifier.classify(tweet)
        pred = res.intent

        # Normalize
        if pred == "software_update_bugs":
            pred = "ios_update_bugs"
        elif pred == "app_store_purchases":
            pred = "purchase_refund_billing"
        elif pred == "other_inquiry":
            pred = "out_of_scope"

        is_match = (pred == exp)
        if is_match:
            correct += 1
        results.append({
            "id": p["id"],
            "tweet": tweet,
            "expected": exp,
            "confused_with": p.get("confused_with"),
            "predicted": pred,
            "passed": is_match,
        })

    acc = correct / len(pairs) if pairs else 0.0
    return {
        "total": len(pairs),
        "correct": correct,
        "accuracy": round(acc, 4),
        "details": results,
    }


def run_safety_eval(checker: SafetyChecker, eval_loader: EvalLoader, safety_loader: SafetyLoader) -> Dict[str, Any]:
    edge_cases = eval_loader.load_safety_edge_cases()
    safe_drafts = safety_loader.load_test_drafts(safe_only=True)
    unsafe_drafts = safety_loader.load_test_drafts(unsafe_only=True)

    # 1. Edge cases
    edge_correct = 0
    for ec in edge_cases:
        draft = ec["draft"]
        exp_safe = ec["expected_safe"]
        chk = checker.check(draft)
        if chk.passed == exp_safe:
            edge_correct += 1

    edge_acc = edge_correct / len(edge_cases) if edge_cases else 0.0

    # 2. Benchmark drafts (100 safe, 100 unsafe)
    true_positive = 0  # correctly flagged unsafe
    false_positive = 0  # safe flagged as unsafe
    true_negative = 0  # correctly passed safe
    false_negative = 0  # unsafe passed as safe

    for s in safe_drafts:
        chk = checker.check(s.get("draft", ""))
        if chk.passed:
            true_negative += 1
        else:
            false_positive += 1

    for u in unsafe_drafts:
        chk = checker.check(u.get("draft", ""))
        if not chk.passed:
            true_positive += 1
        else:
            false_negative += 1

    total_benchmark = len(safe_drafts) + len(unsafe_drafts)
    acc = (true_positive + true_negative) / total_benchmark if total_benchmark else 0.0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 1.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 1.0

    return {
        "edge_cases_total": len(edge_cases),
        "edge_cases_accuracy": round(edge_acc, 4),
        "benchmark_total": total_benchmark,
        "benchmark_accuracy": round(acc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(false_positive / len(safe_drafts), 4) if safe_drafts else 0.0,
    }


def run_escalation_eval(engine: EscalationEngine, escalation_loader: EscalationLoader) -> Dict[str, Any]:
    scenarios = escalation_loader.load_test_scenarios()
    correct = 0
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    results = []
    for s in scenarios:
        tweet = s["tweet"]
        exp = s["should_escalate"]
        # Basic heuristic mapping to feed into engine
        dec = engine.decide(
            customer_message=tweet,
            intent="unknown",
            intent_confidence=0.85,
            has_similar_history=True,
            rag_similarity=0.85,
        )
        pred = (dec.decision == "escalate")
        is_match = (pred == exp)
        if is_match:
            correct += 1
        if pred and exp:
            tp += 1
        elif pred and not exp:
            fp += 1
        elif not pred and not exp:
            tn += 1
        elif not pred and exp:
            fn += 1

        results.append(escalation_loader.evaluate_scenario(s, pred, dec.reasons))

    acc = correct / len(scenarios) if scenarios else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    return {
        "total": len(scenarios),
        "correct": correct,
        "accuracy": round(acc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) else 0.0,
    }


async def main():
    parser = argparse.ArgumentParser(description="Evaluate Apple Support AI Pipeline.")
    parser.add_argument("--output", default="eval_results.json", help="Path to write JSON results.")
    args = parser.parse_args()

    eval_loader = EvalLoader()
    safety_loader = SafetyLoader()
    escalation_loader = EscalationLoader()

    provider = MockLLMProvider()
    classifier = IntentClassifier(provider=provider)
    checker = SafetyChecker()
    engine = EscalationEngine()

    print("=" * 70)
    print("RUNNING COMPREHENSIVE PIPELINE EVALUATION")
    print("=" * 70)

    golden_res = await run_golden_set_eval(classifier, eval_loader)
    print(f"\n[1] Golden Test Set (N={golden_res['total']}):")
    print(f"    Overall Accuracy: {golden_res['accuracy'] * 100:.2f}%")
    print("    By Difficulty:")
    for diff, data in golden_res["by_difficulty"].items():
        print(f"      - {diff:12}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")

    confusion_res = await run_confusion_pairs_eval(classifier, eval_loader)
    print(f"\n[2] Confusion Pairs (N={confusion_res['total']}):")
    print(f"    Boundary Accuracy: {confusion_res['accuracy'] * 100:.2f}% ({confusion_res['correct']}/{confusion_res['total']})")

    safety_res = run_safety_eval(checker, eval_loader, safety_loader)
    print(f"\n[3] Safety Checker (Drafts N={safety_res['benchmark_total']}, Edge N={safety_res['edge_cases_total']}):")
    print(f"    Benchmark Accuracy: {safety_res['benchmark_accuracy'] * 100:.2f}%")
    print(f"    Precision:          {safety_res['precision'] * 100:.2f}%")
    print(f"    Recall:             {safety_res['recall'] * 100:.2f}%")
    print(f"    Edge Cases Acc:     {safety_res['edge_cases_accuracy'] * 100:.2f}%")

    escalation_res = run_escalation_eval(engine, escalation_loader)
    print(f"\n[4] Escalation Engine (Scenarios N={escalation_res['total']}):")
    print(f"    Accuracy:           {escalation_res['accuracy'] * 100:.2f}% ({escalation_res['correct']}/{escalation_res['total']})")
    print(f"    Precision:          {escalation_res['precision'] * 100:.2f}%")
    print(f"    Recall:             {escalation_res['recall'] * 100:.2f}%")

    summary = {
        "golden_test_set": golden_res,
        "confusion_pairs": confusion_res,
        "safety_evaluation": safety_res,
        "escalation_evaluation": escalation_res,
    }

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"EVALUATION COMPLETE. Report written to: {out_path.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())


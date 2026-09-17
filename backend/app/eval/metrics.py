"""
Evaluation Metrics calculation module.
Computes Macro-F1, per-class metrics, confusion matrices, ROUGE-L lexical overlap,
escalation precision/recall/F1, and latency percentiles.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

try:
    from rouge_score import rouge_scorer
    ROUGE_AVAILABLE = True
except ImportError:
    ROUGE_AVAILABLE = False


def calculate_intent_metrics(
    y_true: List[str],
    y_pred: List[str],
    labels: List[str],
) -> Dict[str, Any]:
    """Calculate accuracy, macro/micro F1, per-class F1, and confusion matrix."""
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    micro_f1 = float(f1_score(y_true, y_pred, labels=labels, average="micro", zero_division=0))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )

    per_class = {}
    for idx, label in enumerate(labels):
        per_class[label] = {
            "precision": round(float(precision[idx]), 3),
            "recall": round(float(recall[idx]), 3),
            "f1": round(float(f1[idx]), 3),
            "support": int(support[idx]),
        }

    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_f1": round(micro_f1, 4),
        "per_class": per_class,
        "labels": labels,
        "confusion_matrix": cm,
    }


def calculate_escalation_metrics(
    y_true_esc: List[str],
    y_pred_esc: List[str],
) -> Dict[str, float]:
    """Compute precision, recall, and F1 for escalation decisions."""
    # Target 'escalate' as positive class
    p, r, f1, _ = precision_recall_fscore_support(
        y_true_esc, y_pred_esc, pos_label="escalate", average="binary", zero_division=0
    )
    acc = accuracy_score(y_true_esc, y_pred_esc)
    return {
        "escalation_accuracy": round(float(acc), 4),
        "escalation_precision": round(float(p), 4),
        "escalation_recall": round(float(r), 4),
        "escalation_f1": round(float(f1), 4),
    }


def calculate_rouge_l(references: List[str], candidates: List[str]) -> float:
    """Computes mean ROUGE-L F1 score between candidate replies and references."""
    if not candidates or not references:
        return 0.0

    if ROUGE_AVAILABLE:
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        scores = []
        for ref, cand in zip(references, candidates):
            score = scorer.score(ref, cand)["rougeL"].fmeasure
            scores.append(score)
        return round(float(np.mean(scores)), 4)

    # Simple LCS word overlap fallback if package is absent
    overlap_scores = []
    for ref, cand in zip(references, candidates):
        ref_words = set(ref.lower().split())
        cand_words = set(cand.lower().split())
        if not ref_words or not cand_words:
            overlap_scores.append(0.0)
            continue
        common = ref_words.intersection(cand_words)
        p = len(common) / len(cand_words)
        r = len(common) / len(ref_words)
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        overlap_scores.append(f1)
    return round(float(np.mean(overlap_scores)), 4)


def calculate_latency_percentiles(latencies_ms: List[int]) -> Dict[str, float]:
    """Compute p50 and p95 latency percentiles in milliseconds."""
    if not latencies_ms:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0}
    arr = np.array(latencies_ms)
    return {
        "p50": round(float(np.percentile(arr, 50)), 1),
        "p95": round(float(np.percentile(arr, 95)), 1),
        "mean": round(float(np.mean(arr)), 1),
    }


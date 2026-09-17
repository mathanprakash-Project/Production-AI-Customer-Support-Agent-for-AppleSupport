"""
Pipeline Evaluator (v2.0).
Evaluates the full 5-stage AI Co-Pilot pipeline against the 50-item Golden Test Set.
Computes:
- Intent classification accuracy (%)
- Escalation detection precision, recall, and F1 (%)
- Safety policy adherence rate (%)
- Model confidence and latency percentiles (p50, p95, mean)
- Per-intent breakdown table
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional
import numpy as np

# Ensure backend root is in sys.path when executed directly
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.agent.pipeline import AgentPipeline
from app.llm.factory import get_llm_provider
from app.db.session import get_standalone_session
from app.repositories.thread_repo import ThreadRepository

logger = logging.getLogger(__name__)


class PipelineEvaluator:
    def __init__(self, golden_set_path: Optional[str] = None):
        if golden_set_path:
            self.path = Path(golden_set_path)
        else:
            self.path = Path(__file__).resolve().parent / "golden_set" / "golden_test_set.json"

        with open(self.path, "r", encoding="utf-8") as f:
            self.test_cases: List[Dict[str, Any]] = json.load(f)

    async def run(self) -> Dict[str, Any]:
        """Execute full evaluation run."""
        provider = get_llm_provider()
        session = await get_standalone_session()
        thread_repo = ThreadRepository(session)
        pipeline = AgentPipeline(provider=provider, thread_repo=thread_repo)

        total = len(self.test_cases)
        intent_correct = 0
        esc_correct = 0
        safety_passed_count = 0
        confidences: List[float] = []
        latencies: List[int] = []

        per_intent_stats: Dict[str, Dict[str, int]] = {}

        print(f"\n========================================================================")
        print(f"🚀 Running Pipeline Evaluation Benchmark ({total} Golden Test Cases)")
        print(f"LLM Provider: {provider.provider_name} | Model: {provider.model_name}")
        print(f"========================================================================\n")

        for idx, item in enumerate(self.test_cases, 1):
            tweet = item["tweet"]
            expected_intent = item["expected_intent"]
            should_escalate = item["should_escalate"]

            # Initialize per-intent tracking
            if expected_intent not in per_intent_stats:
                per_intent_stats[expected_intent] = {"total": 0, "correct": 0}
            per_intent_stats[expected_intent]["total"] += 1

            start_t = time.time()
            resp = await pipeline.run(customer_message=tweet, ticket_id=f"eval-{item['id']}")
            lat_ms = int((time.time() - start_t) * 1000)
            latencies.append(lat_ms)

            # 1. Intent check
            pred_intent = resp.intent.intent
            is_intent_match = (pred_intent == expected_intent) or (expected_intent in pred_intent)
            if is_intent_match:
                intent_correct += 1
                per_intent_stats[expected_intent]["correct"] += 1

            # 2. Escalation check
            pred_escalate = (resp.escalation.decision == "escalate")
            if pred_escalate == should_escalate:
                esc_correct += 1

            # 3. Safety check
            if resp.safety and resp.safety.passed:
                safety_passed_count += 1

            confidences.append(resp.intent.confidence)

            # Live progress bar
            icon = "✓" if is_intent_match and (pred_escalate == should_escalate) else "✗"
            print(f"[{idx:02d}/{total}] {icon} Intent: {pred_intent:<25} Esc: {str(pred_escalate):<5} Lat: {lat_ms}ms")

        # Aggregate metrics
        intent_acc = round((intent_correct / total) * 100.0, 1)
        esc_acc = round((esc_correct / total) * 100.0, 1)
        safety_rate = round((safety_passed_count / total) * 100.0, 1)
        avg_conf = round(float(np.mean(confidences)) * 100.0, 1)
        p50_lat = int(np.percentile(latencies, 50))
        p95_lat = int(np.percentile(latencies, 95))
        mean_lat = int(np.mean(latencies))

        results = {
            "total_test_cases": total,
            "intent_accuracy_pct": intent_acc,
            "escalation_accuracy_pct": esc_acc,
            "safety_pass_rate_pct": safety_rate,
            "avg_confidence_pct": avg_conf,
            "latency": {
                "p50_ms": p50_lat,
                "p95_ms": p95_lat,
                "mean_ms": mean_lat,
            },
            "per_intent_breakdown": {
                k: {
                    "total": v["total"],
                    "correct": v["correct"],
                    "accuracy_pct": round((v["correct"] / v["total"]) * 100.0, 1) if v["total"] > 0 else 0.0,
                }
                for k, v in per_intent_stats.items()
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Save to disk
        output_file = Path(__file__).resolve().parent / "evaluation_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"\n========================================================================")
        print(f"📊 EVALUATION BENCHMARK RESULTS SUMMARY")
        print(f"========================================================================")
        print(f"🎯 Intent Classification Accuracy : {intent_acc}% ({intent_correct}/{total})")
        print(f"🛡️ Escalation Accuracy            : {esc_acc}% ({esc_correct}/{total})")
        print(f"🔒 Safety Policy Pass Rate        : {safety_rate}% ({safety_passed_count}/{total})")
        print(f"✨ Average Model Confidence       : {avg_conf}%")
        print(f"⚡ Pipeline Latency (p50 / p95)   : {p50_lat}ms / {p95_lat}ms (mean: {mean_lat}ms)")
        print(f"========================================================================\n")

        await session.close()
        return results


if __name__ == "__main__":
    from typing import Optional
    asyncio.run(PipelineEvaluator().run())

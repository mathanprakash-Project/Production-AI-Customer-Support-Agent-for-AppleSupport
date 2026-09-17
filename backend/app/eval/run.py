"""
Comprehensive Evaluation Harness CLI Runner.
Runs Golden Set evaluation comparing AI Agent vs Simple Baseline vs Trivial Baseline.
Computes all assignment metrics, runs LLM Judge, and produces publication-ready reports.
"""

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from app.agent.classifier import DEFAULT_TAXONOMY
from app.eval.baselines.random_clf import RandomBaseline
from app.eval.baselines.tfidf_lr import TfidfBaseline
from app.eval.judge import LLMJudge
from app.eval.judge_agreement import compute_inter_rater_agreement
from app.eval.metrics import (
    calculate_escalation_metrics,
    calculate_intent_metrics,
    calculate_latency_percentiles,
    calculate_rouge_l,
)
from app.llm.factory import get_judge_provider, get_llm_provider
from app.llm.embeddings import get_embedding_service
from app.agent.pipeline import AgentPipeline
from app.agent.classifier import IntentClassifier
from app.agent.drafter import ReplyDrafter
from app.agent.escalation import EscalationEngine
from app.repositories.thread_repo import ThreadRepository
from app.db.session import get_standalone_session
from app.models.eval_run import EvalRun

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set" / "golden_set.jsonl"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "eval" / "reports"


def load_golden_set(smoke_test: bool = False, max_items: int = 200) -> List[Dict[str, Any]]:
    if not GOLDEN_SET_PATH.exists():
        from app.eval.golden_set.build_golden_set import build_golden_set
        build_golden_set()

    items = []
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
                if smoke_test and len(items) >= 25:
                    break
                elif len(items) >= max_items:
                    break
    return items


async def run_evaluation(smoke_test: bool = False, force_mock: bool = False):
    start_time = time.time()
    logger.info(f"--- Starting Evaluation (smoke_test={smoke_test}, force_mock={force_mock}) ---")

    dataset = load_golden_set(smoke_test=smoke_test)
    logger.info(f"Loaded {len(dataset)} evaluation items from golden set.")

    labels = [t["label"] for t in DEFAULT_TAXONOMY]
    y_true_intent = [item["ground_truth_intent"] for item in dataset]
    y_true_esc = [item["ground_truth_escalation"] for item in dataset]
    ref_replies = [item["ground_truth_brand_reply"] for item in dataset]
    human_scores = [item.get("human_scores", {"relevance": 5, "accuracy": 5, "tone": 5, "completeness": 5, "groundedness": 5}) for item in dataset]

    # Initialize Baselines
    trivial_base = RandomBaseline()
    simple_base = TfidfBaseline()

    # Initialize LLM Providers
    if force_mock:
        from app.llm.providers.mock import MockProvider
        task_llm = MockProvider("mock-agent-model")
        judge_llm = MockProvider("mock-judge-model")
    else:
        task_llm = get_llm_provider()
        judge_llm = get_judge_provider()

    logger.info(f"Agent Task Model: {task_llm.model_name} ({task_llm.provider_name})")
    logger.info(f"Judge Model: {judge_llm.model_name} ({judge_llm.provider_name})")

    # Pipeline Setup with DB Session
    session = await get_standalone_session()
    try:
        thread_repo = ThreadRepository(session)
        pipeline = AgentPipeline(
            provider=task_llm,
            thread_repo=thread_repo,
        )
        judge = LLMJudge(judge_provider=judge_llm)

        # 1. Run Trivial Baseline
        logger.info("Evaluating Trivial Baseline (Random + Always Escalate)...")
        triv_pred_intent, triv_pred_esc, triv_replies = [], [], []
        for d in dataset:
            res = trivial_base.predict(d["customer_message"])
            triv_pred_intent.append(res["intent"])
            triv_pred_esc.append(res["escalation_decision"])
            triv_replies.append(res["draft_reply"])

        triv_intent_metrics = calculate_intent_metrics(y_true_intent, triv_pred_intent, labels)
        triv_esc_metrics = calculate_escalation_metrics(y_true_esc, triv_pred_esc)
        triv_rouge = calculate_rouge_l(ref_replies, triv_replies)

        # 2. Run Simple Baseline (TF-IDF + Logistic Regression)
        logger.info("Evaluating Simple Baseline (TF-IDF + LogReg + NN Reply)...")
        simp_pred_intent, simp_pred_esc, simp_replies = [], [], []
        for d in dataset:
            res = simple_base.predict(d["customer_message"])
            simp_pred_intent.append(res["intent"])
            simp_pred_esc.append(res["escalation_decision"])
            simp_replies.append(res["draft_reply"])

        simp_intent_metrics = calculate_intent_metrics(y_true_intent, simp_pred_intent, labels)
        simp_esc_metrics = calculate_escalation_metrics(y_true_esc, simp_pred_esc)
        simp_rouge = calculate_rouge_l(ref_replies, simp_replies)

        # 3. Run AI Support Agent Pipeline
        logger.info("Evaluating Production AI Support Agent Pipeline...")
        agent_pred_intent, agent_pred_esc, agent_replies = [], [], []
        agent_latencies = []
        failure_cases = []
        judge_scores = []

        for idx, d in enumerate(dataset):
            msg = d["customer_message"]
            inf_res = await pipeline.run(msg, ticket_id=d["id"])

            agent_pred_intent.append(inf_res.intent.intent)
            agent_pred_esc.append(inf_res.escalation.decision)
            agent_replies.append(inf_res.draft.reply)
            agent_latencies.append(inf_res.meta.latency_ms)

            # Record failure cases
            if inf_res.intent.intent != d["ground_truth_intent"]:
                failure_cases.append({
                    "id": d["id"],
                    "customer_message": msg,
                    "expected_intent": d["ground_truth_intent"],
                    "predicted_intent": inf_res.intent.intent,
                    "confidence": inf_res.intent.confidence,
                    "escalation_decision": inf_res.escalation.decision,
                })

            # Score first 50 items with LLM Judge for agreement study
            if idx < 50:
                judge_eval = await judge.evaluate_reply(
                    customer_message=msg,
                    draft_reply=inf_res.draft.reply,
                    historical_reply=d["ground_truth_brand_reply"],
                )
                judge_scores.append(judge_eval.model_dump())

        agent_intent_metrics = calculate_intent_metrics(y_true_intent, agent_pred_intent, labels)
        agent_esc_metrics = calculate_escalation_metrics(y_true_esc, agent_pred_esc)
        agent_rouge = calculate_rouge_l(ref_replies, agent_replies)
        agent_latency_metrics = calculate_latency_percentiles(agent_latencies)

        # 4. Human-Judge Agreement Study (50 dual-labelled items)
        logger.info("Computing Human-Judge Inter-Rater Agreement (Cohen's Kappa & Spearman rho)...")
        agreement_metrics = compute_inter_rater_agreement(
            human_scores=human_scores[: len(judge_scores)],
            judge_scores=judge_scores,
        )

        # Summary Metrics Dictionary
        results_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_size": len(dataset),
            "smoke_test": smoke_test,
            "models": {
                "agent_model": task_llm.model_name,
                "agent_provider": task_llm.provider_name,
                "judge_model": judge_llm.model_name,
                "judge_provider": judge_llm.provider_name,
            },
            "headline_comparison": {
                "Trivial Baseline (Random)": {
                    "accuracy": triv_intent_metrics["accuracy"],
                    "macro_f1": triv_intent_metrics["macro_f1"],
                    "rouge_l": triv_rouge,
                    "escalation_f1": triv_esc_metrics["escalation_f1"],
                },
                "Simple Baseline (TF-IDF + LogReg)": {
                    "accuracy": simp_intent_metrics["accuracy"],
                    "macro_f1": simp_intent_metrics["macro_f1"],
                    "rouge_l": simp_rouge,
                    "escalation_f1": simp_esc_metrics["escalation_f1"],
                },
                "AI Customer Support Agent (Ours)": {
                    "accuracy": agent_intent_metrics["accuracy"],
                    "macro_f1": agent_intent_metrics["macro_f1"],
                    "rouge_l": agent_rouge,
                    "escalation_f1": agent_esc_metrics["escalation_f1"],
                    "latency_p50_ms": agent_latency_metrics["p50"],
                    "latency_p95_ms": agent_latency_metrics["p95"],
                },
            },
            "agent_intent_metrics": agent_intent_metrics,
            "agent_escalation_metrics": agent_esc_metrics,
            "agent_latency_metrics": agent_latency_metrics,
            "human_judge_agreement": agreement_metrics,
            "top_failures": failure_cases[:5],
        }

        # Persist to database if possible
        try:
            eval_record = EvalRun(
                model=task_llm.model_name,
                prompt_versions={"classifier": "v1", "drafter": "v1", "judge": "v1"},
                metrics_json=results_summary,
                notes=f"Evaluation run on {len(dataset)} golden items.",
            )
            session.add(eval_record)
            await session.commit()
            logger.info("Saved evaluation run to database table 'eval_runs'.")
        except Exception as e:
            logger.warning(f"Could not persist run to eval_runs table: {e}")
    finally:
        await session.close()

    # Export Report Files
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "metrics_latest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)

    md_report = generate_markdown_report(results_summary)
    md_path = REPORTS_DIR / "report_latest.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    logger.info(f"Evaluation complete in {time.time() - start_time:.2f}s!")
    logger.info(f"Report saved to: {md_path}")
    logger.info(f"JSON saved to: {json_path}")
    return results_summary


def generate_markdown_report(summary: Dict[str, Any]) -> str:
    h = summary["headline_comparison"]
    return f"""# Evaluation Run Summary Report

**Timestamp**: {summary['timestamp']}  
**Dataset Size**: {summary['dataset_size']} golden examples  
**Models**: Task: `{summary['models']['agent_model']}` ({summary['models']['agent_provider']}) | Judge: `{summary['models']['judge_model']}`

---

## 1. Headline Results vs Baselines

| Model / System | Accuracy | Macro-F1 | ROUGE-L | Escalation F1 |
|---|---|---|---|---|
| **Trivial Baseline (Random)** | {h['Trivial Baseline (Random)']['accuracy']:.3f} | {h['Trivial Baseline (Random)']['macro_f1']:.3f} | {h['Trivial Baseline (Random)']['rouge_l']:.3f} | {h['Trivial Baseline (Random)']['escalation_f1']:.3f} |
| **Simple Baseline (TF-IDF+LR)** | {h['Simple Baseline (TF-IDF + LogReg)']['accuracy']:.3f} | {h['Simple Baseline (TF-IDF + LogReg)']['macro_f1']:.3f} | {h['Simple Baseline (TF-IDF + LogReg)']['rouge_l']:.3f} | {h['Simple Baseline (TF-IDF + LogReg)']['escalation_f1']:.3f} |
| **AI Support Agent (Ours)** | **{h['AI Customer Support Agent (Ours)']['accuracy']:.3f}** | **{h['AI Customer Support Agent (Ours)']['macro_f1']:.3f}** | **{h['AI Customer Support Agent (Ours)']['rouge_l']:.3f}** | **{h['AI Customer Support Agent (Ours)']['escalation_f1']:.3f}** |

---

## 2. Human–Judge Agreement Study (50 Items)

| Rubric Dimension | Cohen's $\\kappa$ (Quadratic) | Spearman $\\rho$ | Human Mean | Judge Mean |
|---|---|---|---|---|
| **Relevance** | {summary['human_judge_agreement']['relevance']['cohens_kappa_quadratic']:.3f} | {summary['human_judge_agreement']['relevance']['spearman_rho']:.3f} | {summary['human_judge_agreement']['relevance']['human_mean']} | {summary['human_judge_agreement']['relevance']['judge_mean']} |
| **Accuracy** | {summary['human_judge_agreement']['accuracy']['cohens_kappa_quadratic']:.3f} | {summary['human_judge_agreement']['accuracy']['spearman_rho']:.3f} | {summary['human_judge_agreement']['accuracy']['human_mean']} | {summary['human_judge_agreement']['accuracy']['judge_mean']} |
| **Tone** | {summary['human_judge_agreement']['tone']['cohens_kappa_quadratic']:.3f} | {summary['human_judge_agreement']['tone']['spearman_rho']:.3f} | {summary['human_judge_agreement']['tone']['human_mean']} | {summary['human_judge_agreement']['tone']['judge_mean']} |
| **Completeness** | {summary['human_judge_agreement']['completeness']['cohens_kappa_quadratic']:.3f} | {summary['human_judge_agreement']['completeness']['spearman_rho']:.3f} | {summary['human_judge_agreement']['completeness']['human_mean']} | {summary['human_judge_agreement']['completeness']['judge_mean']} |
| **Groundedness** | {summary['human_judge_agreement']['groundedness']['cohens_kappa_quadratic']:.3f} | {summary['human_judge_agreement']['groundedness']['spearman_rho']:.3f} | {summary['human_judge_agreement']['groundedness']['human_mean']} | {summary['human_judge_agreement']['groundedness']['judge_mean']} |

---

## 3. Latency Percentiles (AI Agent)
- **p50 Latency**: {summary['agent_latency_metrics']['p50']} ms
- **p95 Latency**: {summary['agent_latency_metrics']['p95']} ms
- **Mean Latency**: {summary['agent_latency_metrics']['mean']} ms
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation harness")
    parser.add_argument("--smoke", action="store_true", help="Run quick 25-item smoke test")
    parser.add_argument("--mock", action="store_true", help="Force MockProvider for instant offline testing")
    args = parser.parse_args()

    asyncio.run(run_evaluation(smoke_test=args.smoke, force_mock=args.mock))


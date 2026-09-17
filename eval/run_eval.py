import argparse
import json
import logging
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

# Setup import paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from eval.metrics import IntentMetrics, ReplyMetrics, EscalationMetrics
from eval.llm_judge import LLMJudge

try:
    import config
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_full_evaluation(golden_set_path: str, agent_pipeline, baselines: dict = None, output_dir: str = None) -> dict:
    """Run full evaluation pipeline."""
    if not output_dir:
        output_dir = os.path.dirname(golden_set_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Load golden set
    golden_set = []
    with open(golden_set_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                golden_set.append(json.loads(line))
                
    logger.info(f"Loaded {len(golden_set)} examples from golden set.")
    
    # Run Agent Pipeline
    logger.info("Running agent pipeline...")
    agent_results = []
    for ex in golden_set:
        msg = ex['customer_message']
        try:
            # Assuming agent_pipeline is a callable or object with .process() returning a dict
            if hasattr(agent_pipeline, 'process'):
            # Use process_message (AgentPipeline) or fall back to callable
            if hasattr(agent_pipeline, 'process_message'):
                out = agent_pipeline.process_message(msg)
            elif hasattr(agent_pipeline, 'process'):
                out = agent_pipeline.process(msg)
            else:
                out = agent_pipeline(msg)
                
            ex_copy = ex.copy()
            ex_copy.update({
                "pred_intent": out.get("intent", "unknown"),
                "draft_reply": out.get("draft_reply", ""),
                "pred_escalation": out.get("escalation_decision", False)
            })
            agent_results.append(ex_copy)
        except Exception as e:
            logger.error(f"Agent pipeline failed on example {ex.get('id')}: {e}")
            
    # Collect True Labels
    gold_intents = [ex.get('gold_intent', 'unknown') for ex in agent_results]
    gold_escalations = [str(ex.get('gold_escalation_decision', False)).lower() == 'true' for ex in agent_results]
    gold_replies = [ex.get('historical_brand_reply', '') for ex in agent_results]
    
    # Collect Predictions
    pred_intents = [ex.get('pred_intent', 'unknown') for ex in agent_results]
    pred_escalations = [str(ex.get('pred_escalation', False)).lower() == 'true' for ex in agent_results]
    pred_replies = [ex.get('draft_reply', '') for ex in agent_results]
    
    # Metrics
    intent_metrics = IntentMetrics.compute(gold_intents, pred_intents)
    escalation_metrics = EscalationMetrics.compute(gold_escalations, pred_escalations)
    reply_metrics = ReplyMetrics.compute(gold_replies, pred_replies)
    
    # LLM Judge
    judge = LLMJudge()
    judged_results = judge.judge_batch(agent_results)
    
    avg_judge_scores = {
        dim: sum(r['judge_results']['scores'][dim] for r in judged_results) / len(judged_results)
        for dim in ['relevance', 'accuracy', 'tone', 'completeness', 'groundedness']
    }
    
    # Save Results
    results_summary = {
        "intent_metrics": intent_metrics,
        "escalation_metrics": escalation_metrics,
        "reply_metrics": reply_metrics,
        "avg_llm_judge_scores": avg_judge_scores
    }
    
    with open(os.path.join(output_dir, 'evaluation_summary.json'), 'w') as f:
        json.dump(results_summary, f, indent=2)
        
    with open(os.path.join(output_dir, 'detailed_results.jsonl'), 'w') as f:
        for r in judged_results:
            f.write(json.dumps(r) + '\n')
            
    # Plots
    try:
        cm = IntentMetrics.confusion_matrix(gold_intents, pred_intents)
        IntentMetrics.plot_confusion_matrix(cm, os.path.join(output_dir, 'intent_confusion_matrix.png'))
    except Exception as e:
        logger.warning(f"Could not plot confusion matrix: {e}")
        
    # Print Table
    print("\n" + "="*40)
    print("EVALUATION RESULTS SUMMARY")
    print("="*40)
    print("\n[Intent Classification]")
    for k, v in intent_metrics.items():
        print(f"{k.ljust(20)}: {v:.4f}")
        
    print("\n[Escalation Decision]")
    for k, v in escalation_metrics.items():
        print(f"{k.ljust(20)}: {v:.4f}")
        
    print("\n[Reply Generation (Lexical)]")
    for k, v in reply_metrics.items():
        print(f"{k.ljust(20)}: {v:.4f}")
        
    print("\n[LLM Judge Scores (1-5)]")
    for k, v in avg_judge_scores.items():
        print(f"{k.ljust(20)}: {v:.2f}")
    print("="*40 + "\n")
    
    return results_summary

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run full evaluation")
    parser.add_argument('--golden-set', type=str, required=True, help="Path to golden set JSONL")
    parser.add_argument('--output-dir', type=str, required=True, help="Directory to save results")
    
    args = parser.parse_args()
    
    # Dummy agent pipeline for CLI execution
    class DummyPipeline:
        def process(self, msg):
            return {
                "intent": "general_inquiry",
                "draft_reply": "Thank you for contacting us. We will look into this.",
                "escalation_decision": False
            }
            
    run_full_evaluation(args.golden_set, DummyPipeline(), output_dir=args.output_dir)

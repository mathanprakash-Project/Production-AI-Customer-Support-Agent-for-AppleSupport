import json
import logging
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)

def compute_agreement(human_scores: list[dict], llm_scores: list[dict]) -> dict:
    """Compute agreement metrics between human and LLM judges."""
    if len(human_scores) != len(llm_scores):
        raise ValueError("Mismatched list lengths between human and LLM scores.")
        
    dimensions = ['relevance', 'accuracy', 'tone', 'completeness', 'groundedness']
    metrics = {}
    
    for dim in dimensions:
        h_vals = []
        l_vals = []
        for h, l in zip(human_scores, llm_scores):
            # Extract scores safely
            h_score = h.get('scores', {}).get(dim, 0)
            l_score = l.get('scores', {}).get(dim, 0)
            
            if h_score is not None and l_score is not None and h_score > 0 and l_score > 0:
                h_vals.append(h_score)
                l_vals.append(l_score)
                
        if not h_vals:
            continue
            
        # Metrics
        kappa = cohen_kappa_score(h_vals, l_vals, weights='linear')
        spearman, _ = spearmanr(h_vals, l_vals)
        mae = np.mean(np.abs(np.array(h_vals) - np.array(l_vals)))
        
        # Agreement within 1 point
        within_1 = sum(1 for h, l in zip(h_vals, l_vals) if abs(h - l) <= 1) / len(h_vals)
        
        metrics[dim] = {
            "cohens_kappa": kappa if not np.isnan(kappa) else 0,
            "spearman_rho": spearman if not np.isnan(spearman) else 0,
            "mean_absolute_error": mae,
            "agreement_within_1_pct": within_1
        }
        
    # Generate report
    report = "Judge Agreement Report\n" + "="*22 + "\n"
    for dim, res in metrics.items():
        report += f"{dim.capitalize()}:\n"
        report += f"  Kappa: {res['cohens_kappa']:.3f}\n"
        report += f"  Spearman: {res['spearman_rho']:.3f}\n"
        report += f"  MAE: {res['mean_absolute_error']:.3f}\n"
        report += f"  Agreement (±1): {res['agreement_within_1_pct']:.1%}\n\n"
        
    logger.info(f"\n{report}")
    return {"metrics": metrics, "report": report}

def create_human_scoring_template(examples: list[dict], output_path: str):
    """Create a JSONL file for humans to fill out scores."""
    template = []
    for ex in examples:
        item = {
            "id": ex.get("id"),
            "customer_message": ex.get("customer_message"),
            "draft_reply": ex.get("draft_reply"),
            "scores": {
                "relevance": None,
                "accuracy": None,
                "tone": None,
                "completeness": None,
                "groundedness": None
            },
            "notes": ""
        }
        template.append(item)
        
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write instructions header
        f.write(json.dumps({"_instructions": "Fill 'scores' with integers 1-5 for each dimension."}) + '\n')
        for item in template:
            f.write(json.dumps(item) + '\n')
            
    logger.info(f"Human scoring template saved to {output_path}")

def load_human_scores(path: str) -> list[dict]:
    """Load human scores from JSONL."""
    scores = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if "_instructions" not in data:
                scores.append(data)
    return scores

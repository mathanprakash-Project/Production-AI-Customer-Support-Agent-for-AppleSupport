import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
try:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from rouge_score import rouge_scorer
    from bert_score import score as bert_score
except ImportError:
    pass # Handle graceful fallback or require these dependencies in requirements.txt

logger = logging.getLogger(__name__)

class IntentMetrics:
    @staticmethod
    def compute(gold_intents: list[str], pred_intents: list[str]) -> dict:
        """Compute intent classification metrics."""
        return {
            "accuracy": accuracy_score(gold_intents, pred_intents),
            "macro_f1": f1_score(gold_intents, pred_intents, average='macro', zero_division=0),
            "weighted_f1": f1_score(gold_intents, pred_intents, average='weighted', zero_division=0),
            "precision_macro": precision_score(gold_intents, pred_intents, average='macro', zero_division=0),
            "recall_macro": recall_score(gold_intents, pred_intents, average='macro', zero_division=0)
        }
        
    @staticmethod
    def confusion_matrix(gold: list[str], pred: list[str]) -> pd.DataFrame:
        """Generate a labeled confusion matrix."""
        labels = sorted(list(set(gold) | set(pred)))
        cm = confusion_matrix(gold, pred, labels=labels)
        return pd.DataFrame(cm, index=labels, columns=labels)
        
    @staticmethod
    def plot_confusion_matrix(cm: pd.DataFrame, output_path: str):
        """Save a plot of the confusion matrix."""
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Intent Classification Confusion Matrix')
        plt.ylabel('True Intent')
        plt.xlabel('Predicted Intent')
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

class ReplyMetrics:
    @staticmethod
    def compute(references: list[str], hypotheses: list[str]) -> dict:
        """Compute text generation metrics for draft replies."""
        if not references or not hypotheses or len(references) != len(hypotheses):
            return {}
            
        metrics = {"bleu": 0.0, "rouge_l": 0.0, "bert_f1": 0.0}
        
        # BLEU
        smoothie = SmoothingFunction().method4
        bleu_scores = []
        for ref, hyp in zip(references, hypotheses):
            ref_safe = str(ref) if ref else ""
            hyp_safe = str(hyp) if hyp else ""
            if not ref_safe and not hyp_safe:
                bleu_scores.append(1.0)
            elif not ref_safe or not hyp_safe:
                bleu_scores.append(0.0)
            else:
                bleu_scores.append(sentence_bleu([ref_safe.split()], hyp_safe.split(), smoothing_function=smoothie))
        metrics['bleu'] = sum(bleu_scores) / len(bleu_scores) if bleu_scores else 0.0
        
        # ROUGE
        try:
            scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
            rouge_scores = []
            for ref, hyp in zip(references, hypotheses):
                ref_safe = str(ref) if ref else ""
                hyp_safe = str(hyp) if hyp else ""
                if not ref_safe and not hyp_safe:
                    rouge_scores.append(1.0)
                elif not ref_safe or not hyp_safe:
                    rouge_scores.append(0.0)
                else:
                    rouge_scores.append(scorer.score(ref_safe, hyp_safe)['rougeL'].fmeasure)
            metrics['rouge_l'] = sum(rouge_scores) / len(rouge_scores) if rouge_scores else 0.0
        except Exception as e:
            logger.warning(f"Failed to compute ROUGE: {e}")
            
        # BERTScore
        try:
            safe_refs = [str(r) if r else "empty" for r in references]
            safe_hyps = [str(h) if h else "empty" for h in hypotheses]
            P, R, F1 = bert_score(safe_hyps, safe_refs, lang="en", rescale_with_baseline=True)
            metrics['bert_precision'] = P.mean().item()
            metrics['bert_recall'] = R.mean().item()
            metrics['bert_f1'] = F1.mean().item()
        except Exception as e:
            logger.warning(f"Failed to compute BERTScore: {e}")
            
        return metrics

class EscalationMetrics:
    @staticmethod
    def compute(gold: list[bool], pred: list[bool]) -> dict:
        """Compute escalation decision metrics."""
        gold_str = [str(g) for g in gold]
        pred_str = [str(p) for p in pred]
        
        return {
            "accuracy": accuracy_score(gold_str, pred_str),
            "precision": precision_score(gold_str, pred_str, pos_label="True", zero_division=0),
            "recall": recall_score(gold_str, pred_str, pos_label="True", zero_division=0),
            "f1": f1_score(gold_str, pred_str, pos_label="True", zero_division=0)
        }

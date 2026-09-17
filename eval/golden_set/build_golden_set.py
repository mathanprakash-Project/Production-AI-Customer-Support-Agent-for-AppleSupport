import argparse
import json
import logging
import random
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    import config
except ImportError:
    logger.warning("config.py not found. Using defaults.")

def build_golden_set(threads: list[dict], classifier, n: int = 200, output_path: str = None) -> list[dict]:
    """
    Build a golden set for evaluation using stratified sampling, including hard examples and edge cases.
    
    Args:
        threads (list[dict]): List of conversation threads.
        classifier: The intent classifier instance.
        n (int): Total number of samples in the golden set.
        output_path (str, optional): Path to save the golden set as JSONL.
        
    Returns:
        list[dict]: The constructed golden set.
    """
    logger.info(f"Building golden set of size {n} from {len(threads)} threads.")
    
    # 1. Run classifier on all first_customer_messages
    logger.info("Running classifier on initial messages...")
    processed_threads = []
    for thread in threads:
        first_message = thread.get('customer_message', '')
        if not first_message:
            continue
            
        prediction = classifier.predict(first_message)
        intent = prediction.get('intent', 'unknown')
        confidence = prediction.get('confidence', 0.0)
        
        processed_threads.append({
            'thread': thread,
            'first_message': first_message,
            'predicted_intent': intent,
            'confidence': confidence
        })
        
    # Group by intent
    intent_groups = {}
    for pt in processed_threads:
        intent = pt['predicted_intent']
        if intent not in intent_groups:
            intent_groups[intent] = []
        intent_groups[intent].append(pt)
        
    golden_set = []
    
    # 3. Target 20% hard examples (confidence < 0.5)
    hard_target = int(n * 0.20)
    hard_candidates = [pt for pt in processed_threads if pt['confidence'] < 0.5]
    hard_samples = random.sample(hard_candidates, min(hard_target, len(hard_candidates)))
    for s in hard_samples:
        s['stratum'] = 'hard'
    golden_set.extend(hard_samples)
    logger.info(f"Selected {len(hard_samples)} hard examples.")
    
    # 4. Include edge cases (very short < 5 words, very long > 100 words, special chars)
    edge_target = int(n * 0.10)
    edge_candidates = []
    for pt in processed_threads:
        if pt in hard_samples:
            continue
        msg = pt['first_message']
        words = msg.split()
        if len(words) < 5 or len(words) > 100 or any(c in msg for c in ['@', '#', '$', '%', '^', '&', '*']):
            edge_candidates.append(pt)
            
    edge_samples = random.sample(edge_candidates, min(edge_target, len(edge_candidates)))
    for s in edge_samples:
        s['stratum'] = 'edge_case'
    golden_set.extend(edge_samples)
    logger.info(f"Selected {len(edge_samples)} edge cases.")
    
    # 2. Stratified sample for the remaining
    remaining_n = n - len(golden_set)
    sampled_so_far = set(id(pt) for pt in golden_set)
    
    if remaining_n > 0:
        # Calculate proportional targets
        total_remaining_candidates = len([pt for pt in processed_threads if id(pt) not in sampled_so_far])
        
        proportional_samples = []
        for intent, group in intent_groups.items():
            available = [pt for pt in group if id(pt) not in sampled_so_far]
            if not available:
                continue
                
            # Minimum 10 per intent or proportional, whichever is larger (if possible)
            proportion = len(group) / max(1, len(processed_threads))
            target = max(10, int(remaining_n * proportion))
            
            sampled = random.sample(available, min(target, len(available)))
            for s in sampled:
                s['stratum'] = 'proportional'
            proportional_samples.extend(sampled)
            
        # If we overshot or undershot, adjust (simple random sample for simplicity here)
        if len(proportional_samples) > remaining_n:
            proportional_samples = random.sample(proportional_samples, remaining_n)
            
        golden_set.extend(proportional_samples)
        logger.info(f"Selected {len(proportional_samples)} proportional samples.")
    
    # Format output
    formatted_golden_set = []
    for i, item in enumerate(golden_set):
        thread = item['thread']
        formatted_golden_set.append({
            "id": f"gs_{i:03d}",
            "customer_message": item['first_message'],
            "thread_id": thread.get('thread_id', f"tid_{i}"),
            "predicted_intent": item['predicted_intent'],
            "classifier_confidence": item['confidence'],
            "gold_intent": "",
            "gold_reply_quality_notes": "",
            "gold_escalation_decision": "",
            "gold_escalation_reason": "",
            "sampling_stratum": item['stratum'],
            "historical_brand_reply": thread.get('historical_reply', ''),
            "labelling_notes": ""
        })
        
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in formatted_golden_set:
                f.write(json.dumps(item) + '\n')
        logger.info(f"Golden set saved to {output_path}")
        
    return formatted_golden_set

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build Golden Set for Evaluation")
    parser.add_argument('--threads-path', type=str, required=True, help="Path to input threads JSONL")
    parser.add_argument('--output-path', type=str, required=True, help="Path to save golden set JSONL")
    parser.add_argument('--n', type=int, default=200, help="Total number of samples")
    
    args = parser.parse_args()
    
    # Dummy classifier for CLI execution without full agent pipeline
    class DummyClassifier:
        def predict(self, text):
            intents = ['billing', 'technical_support', 'account_access', 'feature_request', 'complaint']
            return {
                'intent': random.choice(intents),
                'confidence': random.random()
            }
            
    # Load threads
    threads = []
    try:
        with open(args.threads_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    threads.append(json.loads(line))
        logger.info(f"Loaded {len(threads)} threads from {args.threads_path}")
    except Exception as e:
        logger.error(f"Failed to load threads: {e}")
        sys.exit(1)
        
    build_golden_set(threads, DummyClassifier(), args.n, args.output_path)

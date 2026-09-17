import json
import logging
from typing import List, Dict, Tuple, Any

from datasets import load_dataset
from sklearn.metrics import accuracy_score, classification_report
import openai
from openai import OpenAI

from config import OPENAI_API_KEY, MODEL_NAME
from intent.classifier import IntentClassifier

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

def load_banking77() -> Tuple[List[str], List[str]]:
    """
    Load Banking77 dataset from HuggingFace.
    Returns (texts, labels).
    """
    logger.info("Loading Banking77 dataset from HuggingFace.")
    dataset = load_dataset("banking77")
    
    texts = dataset['test']['text']
    
    # Map label IDs to string labels
    label_names = dataset['test'].features['label'].names
    labels = [label_names[lbl] for lbl in dataset['test']['label']]
    
    return texts, labels

def map_to_taxonomy(banking77_labels: List[str], taxonomy: Dict[str, Any]) -> Dict[str, str]:
    """
    Map Banking77's 77 intents to our custom taxonomy using LLM.
    """
    logger.info("Mapping Banking77 labels to custom taxonomy.")
    unique_banking_labels = list(set(banking77_labels))
    
    taxonomy_names = list(taxonomy.keys())
    
    prompt = (
        f"We have the following target taxonomy intents:\n{taxonomy_names}\n\n"
        f"And we have the following Banking77 labels:\n{unique_banking_labels}\n\n"
        "Map each Banking77 label to the most appropriate target taxonomy intent. "
        "Return a JSON object where the keys are the Banking77 labels and the values "
        "are the target taxonomy intents."
    )
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a customer support intent mapping system."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.0
    )
    
    mapping = json.loads(response.choices[0].message.content)
    return mapping

def evaluate_on_banking77(classifier: IntentClassifier, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Run classifier on Banking77 test set.
    """
    texts, labels = load_banking77()
    
    logger.info(f"Evaluating on {len(texts)} Banking77 test samples.")
    
    # Map original labels to taxonomy
    true_labels = [mapping.get(lbl, lbl) for lbl in labels]
    
    predictions = classifier.classify_batch(texts)
    pred_labels = [p['intent'] for p in predictions]
    
    accuracy = accuracy_score(true_labels, pred_labels)
    report = classification_report(true_labels, pred_labels, output_dict=True, zero_division=0)
    
    logger.info(f"Accuracy: {accuracy:.4f}")
    
    return {
        "accuracy": accuracy,
        "classification_report": report
    }

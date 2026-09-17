import json
import logging
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

import openai
from openai import OpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from config import OPENAI_API_KEY, MODEL_NAME

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

class IntentClassifier(ABC):
    @abstractmethod
    def classify(self, message: str) -> Dict[str, Any]:
        """Classify a single message. Return dict with 'intent' and 'confidence'."""
        pass
    
    @abstractmethod  
    def classify_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        """Classify a batch of messages."""
        pass


class LLMClassifier(IntentClassifier):
    def __init__(self, taxonomy: Dict[str, Any], model: str = MODEL_NAME):
        self.taxonomy = taxonomy
        self.model = model
        self.cache = {}
        
        # Build prompt context
        self.taxonomy_context = "Available Intents:\n"
        self.intents_list = list(taxonomy.keys())
        for intent, details in taxonomy.items():
            self.taxonomy_context += f"- {intent}: {details.get('description', '')}\n"
            examples = details.get('examples', [])
            if examples:
                self.taxonomy_context += f"  Examples: {', '.join(examples[:2])}\n"
                
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(openai.RateLimitError)
    )
    def _call_llm(self, message: str) -> Dict[str, Any]:
        prompt = (
            f"Classify the following customer support message into one of the provided intents.\n\n"
            f"{self.taxonomy_context}\n"
            f"Message: \"{message}\"\n\n"
            "Return a JSON object with two keys: 'intent' (string, matching one of the available intents) "
            "and 'confidence' (float between 0 and 1 indicating your confidence in the classification)."
        )
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a customer support classification system."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        try:
            res = json.loads(response.choices[0].message.content)
            # Basic validation
            if res.get('intent') not in self.taxonomy:
                res['intent'] = "Unknown" if "Unknown" in self.taxonomy else (self.intents_list[0] if self.intents_list else "Unknown")
            if not isinstance(res.get('confidence'), (int, float)):
                res['confidence'] = 0.5
            return {"intent": res['intent'], "confidence": float(res['confidence'])}
        except json.JSONDecodeError:
            return {"intent": self.intents_list[0] if self.intents_list else "Unknown", "confidence": 0.0}

    def classify(self, message: str) -> Dict[str, Any]:
        if message in self.cache:
            return self.cache[message]
            
        result = self._call_llm(message)
        self.cache[message] = result
        return result

    def classify_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        return [self.classify(msg) for msg in messages]


class RandomClassifier(IntentClassifier):
    def __init__(self, intents: List[str]):
        self.intents = intents
        
    def classify(self, message: str) -> Dict[str, Any]:
        return {
            "intent": random.choice(self.intents) if self.intents else "Unknown",
            "confidence": 1.0 / len(self.intents) if self.intents else 0.0
        }
        
    def classify_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        return [self.classify(msg) for msg in messages]


class TFIDFClassifier(IntentClassifier):
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.model = LogisticRegression(max_iter=1000)
        self.is_fitted = False
        self.classes_ = []
        
    def fit(self, messages: List[str], labels: List[str]):
        logger.info(f"Fitting TFIDFClassifier on {len(messages)} samples.")
        X = self.vectorizer.fit_transform(messages)
        self.model.fit(X, labels)
        self.classes_ = self.model.classes_.tolist()
        self.is_fitted = True
        
    def classify(self, message: str) -> Dict[str, Any]:
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before calling classify().")
            
        X = self.vectorizer.transform([message])
        probs = self.model.predict_proba(X)[0]
        
        max_prob_idx = probs.argmax()
        return {
            "intent": self.classes_[max_prob_idx],
            "confidence": float(probs[max_prob_idx])
        }
        
    def classify_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before calling classify_batch().")
            
        X = self.vectorizer.transform(messages)
        probs_all = self.model.predict_proba(X)
        
        results = []
        for probs in probs_all:
            max_prob_idx = probs.argmax()
            results.append({
                "intent": self.classes_[max_prob_idx],
                "confidence": float(probs[max_prob_idx])
            })
            
        return results

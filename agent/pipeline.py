import json
import logging
import time
import os
from typing import List, Dict, Any
from tqdm import tqdm

from config import PROCESSED_DIR, TOP_K_RETRIEVAL
from agent.retriever import ThreadRetriever
from agent.drafter import ReplyDrafter
from agent.escalation import EscalationDecider
from intent.classifier import IntentClassifier
from intent.classifier import LLMClassifier
from intent.discover import load_taxonomy

logger = logging.getLogger(__name__)

class AgentPipeline:
    """
    Orchestrates the full AI agent pipeline: classification, retrieval, drafting, and escalation.
    """

    def __init__(self, threads_path: str = None):
        """
        Initializes the agent pipeline and its components.
        
        Args:
            threads_path: Path to the threads JSONL file for retrieval.
        """
        default_path = os.path.join(PROCESSED_DIR, "threads.jsonl")
        self.threads_path = threads_path or default_path
        
        logger.info("Initializing Agent Pipeline components...")
        
        # Load threads
        self.threads = self._load_threads(self.threads_path)
        
        # Initialize components
        self.classifier = IntentClassifier()
        taxonomy = load_taxonomy()
        self.classifier = LLMClassifier(taxonomy=taxonomy)
        self.retriever = ThreadRetriever(self.threads)
        self.drafter = ReplyDrafter()
        self.escalator = EscalationDecider()
        
        logger.info("Pipeline initialization complete.")

    def _load_threads(self, path: str) -> List[Dict[str, Any]]:
        """Loads threads from a JSONL file."""
        threads = []
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        threads.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            logger.info(f"Loaded {len(threads)} threads from {path}")
        else:
            logger.warning(f"Threads file not found at {path}. Retriever will be empty.")
        return threads

    def process_message(self, customer_message: str) -> Dict[str, Any]:
        """
        Processes a single customer message through the full pipeline.
        
        Args:
            customer_message: The text of the customer message.
            
        Returns:
            A dictionary containing the full processing results.
        """
        start_time = time.time()
        
        # 1. Classify intent
        classification = self.classifier.classify(customer_message)
        intent = classification.get("intent", "unknown")
        intent_confidence = classification.get("confidence", 0.0)
        
        # 2. Retrieve similar threads
        similar_threads = self.retriever.retrieve(customer_message, top_k=TOP_K_RETRIEVAL)
        
        # 3. Draft reply
        draft_result = self.drafter.draft_reply(
            customer_message=customer_message,
            intent=intent,
            similar_threads=similar_threads
        )
        
        # 4. Decide escalation
        escalation_result = self.escalator.decide(
            customer_message=customer_message,
            intent=intent,
            intent_confidence=intent_confidence,
            draft_confidence=draft_result.get("confidence", 0.0)
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "customer_message": customer_message,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "similar_threads_count": len(similar_threads),
            "draft_reply": draft_result.get("reply", ""),
            "draft_confidence": draft_result.get("confidence", 0.0),
            "escalation_decision": escalation_result.get("decision", "escalate"),
            "escalation_reason": escalation_result.get("reason", ""),
            "processing_time_ms": processing_time_ms
        }

    def process_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        """
        Processes a batch of messages.
        
        Args:
            messages: List of customer messages.
            
        Returns:
            List of processing results.
        """
        results = []
        for msg in tqdm(messages, desc="Processing messages"):
            results.append(self.process_message(msg))
        return results

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Initializing Agent Pipeline for Demo...")
    pipeline = AgentPipeline()
    
    print("\n" + "="*50)
    print("Agent Pipeline Demo mode")
    print("Enter a customer message (or 'quit' to exit):")
    print("="*50 + "\n")
    
    while True:
        try:
            msg = input("\nCustomer > ")
            if msg.strip().lower() in ['quit', 'exit', 'q']:
                break
            if not msg.strip():
                continue
                
            print("\nProcessing...")
            result = pipeline.process_message(msg)
            
            print(f"\n--- Agent Response ({result['processing_time_ms']}ms) ---")
            print(f"Intent: {result['intent']} (confidence: {result['intent_confidence']:.2f})")
            print(f"Similar Threads Found: {result['similar_threads_count']}")
            print(f"Action: {result['escalation_decision'].upper()} - {result['escalation_reason']}")
            
            if result['escalation_decision'] == 'auto_handle':
                print(f"Reply Draft (confidence: {result['draft_confidence']:.2f}):")
                print(f"  {result['draft_reply']}")
            else:
                print(f"Reply Draft (Hidden due to escalation):")
                print(f"  {result['draft_reply']}")
                
        except (KeyboardInterrupt, EOFError):
            break

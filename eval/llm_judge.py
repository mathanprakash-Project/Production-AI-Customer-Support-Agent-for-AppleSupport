import json
import logging
import os
import sys
from tqdm import tqdm
from openai import OpenAI
from pydantic import BaseModel, Field

# Add parent directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import config
except ImportError:
    config = type('Config', (), {'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'), 'JUDGE_MODEL': 'gpt-4o'})()

logger = logging.getLogger(__name__)

class JudgeScore(BaseModel):
    relevance: int = Field(..., description="1-5 score: Does the reply address the customer's actual issue?")
    accuracy: int = Field(..., description="1-5 score: Is the information factually correct / consistent with brand patterns?")
    tone: int = Field(..., description="1-5 score: Does it match the brand's historical communication style?")
    completeness: int = Field(..., description="1-5 score: Does it provide actionable next steps?")
    groundedness: int = Field(..., description="1-5 score: Is it grounded in retrieved historical data (not hallucinated)?")
    reasoning: dict = Field(..., description="String explanations for each dimension score")

class LLMJudge:
    def __init__(self, model: str = None):
        self.model = model or getattr(config, 'JUDGE_MODEL', 'gpt-4o')
        self.client = OpenAI(api_key=getattr(config, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY')))
        
    def judge_reply(self, customer_message: str, intent: str, draft_reply: str, historical_reply: str = None) -> dict:
        """Score a draft reply using an LLM as a judge."""
        
        system_prompt = """You are an expert customer support QA evaluator for AppleSupport.
Evaluate the draft reply based on the customer's message, intent, and historical brand reply (if provided).
Score on a scale of 1-5 for 5 dimensions:
1. Relevance (1=completely ignores issue, 5=directly addresses core issue)
2. Accuracy (1=factually wrong/hallucinates, 5=factually correct/consistent)
3. Tone (1=unprofessional/mismatched, 5=perfectly matches AppleSupport style)
4. Completeness (1=no next steps, 5=clear, actionable resolution/next steps)
5. Groundedness (1=makes up unverified policies, 5=strictly grounded in facts/historical patterns)

Provide brief reasoning for each score."""

        user_prompt = f"""
Customer Message: {customer_message}
Identified Intent: {intent}
Historical Brand Reply (Reference): {historical_reply or 'None provided'}

Draft Reply to Evaluate:
{draft_reply}
"""
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=JudgeScore,
                temperature=0.0
            )
            
            result = response.choices[0].message.parsed
            scores = {
                "relevance": result.relevance,
                "accuracy": result.accuracy,
                "tone": result.tone,
                "completeness": result.completeness,
                "groundedness": result.groundedness
            }
            
            overall = sum(scores.values()) / 5.0
            
            return {
                "scores": scores,
                "overall_score": overall,
                "reasoning": result.reasoning
            }
        except Exception as e:
            logger.error(f"Error in LLM Judge: {e}")
            return {
                "scores": {"relevance": 0, "accuracy": 0, "tone": 0, "completeness": 0, "groundedness": 0},
                "overall_score": 0.0,
                "reasoning": {"error": str(e)}
            }
            
    def judge_batch(self, examples: list[dict]) -> list[dict]:
        """Run the judge over a batch of examples."""
        results = []
        for ex in tqdm(examples, desc="Judging replies"):
            judgment = self.judge_reply(
                customer_message=ex.get('customer_message', ''),
                intent=ex.get('predicted_intent', ''),
                draft_reply=ex.get('draft_reply', ''),
                historical_reply=ex.get('historical_brand_reply', '')
            )
            
            combined = {**ex, "judge_results": judgment}
            results.append(combined)
            
        return results

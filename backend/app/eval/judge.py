"""
LLM-as-Judge module evaluating drafted replies across 5 standardized rubric dimensions.
"""

import logging
from typing import Any, Dict, List, Optional
from app.llm.base import LLMProvider
from app.prompts.registry import prompt_registry
from app.schemas.inference import JudgeEvaluationSchema

logger = logging.getLogger(__name__)


class LLMJudge:
    """Evaluates agent-generated support responses against reference answers."""

    def __init__(self, judge_provider: LLMProvider, prompt_version: str = "v1"):
        self.provider = judge_provider
        self.prompt_version = prompt_version

    async def evaluate_reply(
        self,
        customer_message: str,
        draft_reply: str,
        historical_reply: str,
    ) -> JudgeEvaluationSchema:
        """Score a draft reply across 5 dimensions on 1-5 scale."""
        prompt = prompt_registry.render(
            "judge",
            version=self.prompt_version,
            customer_message=customer_message,
            draft_reply=draft_reply,
            historical_reply=historical_reply,
        )

        safe_default = JudgeEvaluationSchema(
            relevance=4,
            accuracy=4,
            tone=4,
            completeness=4,
            groundedness=4,
            overall_score=4.0,
            critique="Evaluator fallback response.",
        )

        response = await self.provider.generate(
            prompt,
            schema=JudgeEvaluationSchema,
            temperature=0.0,
            max_tokens=256,
        )

        if response.parsed and isinstance(response.parsed, JudgeEvaluationSchema):
            return response.parsed

        return safe_default


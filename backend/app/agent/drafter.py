"""
RAG-grounded Reply Drafter using historical brand resolutions.
"""

import logging
from typing import List, Optional, Tuple
from app.llm.base import LLMProvider
from app.prompts.registry import prompt_registry
from app.schemas.inference import DraftReplySchema, RetrievedThreadItem

logger = logging.getLogger(__name__)


class ReplyDrafter:
    """Drafts empathetic, grounded responses using retrieved historical context."""

    def __init__(
        self,
        provider: LLMProvider,
        prompt_version: str = "v1",
    ):
        self.provider = provider
        self.prompt_version = prompt_version

    async def draft(
        self,
        customer_message: str,
        intent: str,
        retrieved_threads: List[RetrievedThreadItem],
    ) -> Tuple[DraftReplySchema, int, int, int]:
        """
        Generates draft reply.
        Returns (DraftReplySchema, latency_ms, tokens_prompt, tokens_completion).
        """
        # Fast polite deflection for non-Apple / out-of-scope inquiries
        lower_msg = customer_message.lower()
        non_apple_terms = [
            "s20", "s21", "s22", "s23", "s24", "galaxy", "samsung",
            "pixel", "android", "playstation", "ps4", "ps5", "xbox", "nintendo",
            "dell", "lenovo", "thinkpad", "surface pro", "hp laptop", "windows 10", "windows 11"
        ]
        if any(term in lower_msg for term in non_apple_terms):
            out_of_scope_draft = DraftReplySchema(
                reply="Thanks for reaching out to @AppleSupport! We only provide technical support for Apple hardware and software. For assistance with your device, please reach out to the manufacturer's official customer care team.",
                confidence=0.98,
                grounded_thread_ids=[],
                reasoning="Detected out-of-scope / non-Apple device inquiry. Provided polite manufacturer deflection.",
            )
            return (out_of_scope_draft, 1, 0, 0)

        prompt = prompt_registry.render(
            "drafter",
            version=self.prompt_version,
            customer_message=customer_message,
            intent=intent,
            retrieved_threads=retrieved_threads,
        )

        safe_default = DraftReplySchema(
            reply="Thanks for contacting @AppleSupport! We are here to help. Could you share your device model and iOS version so we can assist further?",
            confidence=0.60,
            grounded_thread_ids=[],
            reasoning="Safe default fallback response.",
        )

        response = await self.provider.generate(
            prompt,
            schema=DraftReplySchema,
            temperature=0.3,
            max_tokens=350,
        )

        draft_result = response.parsed if isinstance(response.parsed, DraftReplySchema) else safe_default

        return (
            draft_result,
            response.latency_ms,
            response.tokens_prompt,
            response.tokens_completion,
        )


"""
Agent Pipeline Orchestrator (v2.0).
Coordinates 5 stages sequentially:
  Stage 1: Intent Classifier (LLM structured)
  Stage 2: Escalation Engine (Deterministic policy & PII check)
  Stage 3: RAG Retriever (Knowledge base with helpfulness weighting)
  Stage 4: Response Drafter (LLM few-shot synthesis)
  Stage 5: Safety Checker (URL validation, promise blocking, tone)
"""

import logging
import time
from typing import Optional
from app.agent.classifier import IntentClassifier
from app.agent.drafter import ReplyDrafter
from app.agent.escalation import EscalationEngine
from app.agent.retriever import SemanticRetriever
from app.agent.safety_checker import SafetyChecker
from app.llm.base import LLMProvider
from app.repositories.thread_repo import ThreadRepository
from app.schemas.inference import (
    DraftReplySchema,
    EscalationDecision,
    InferenceMeta,
    InferenceResponse,
    SafetyResultSchema,
)

logger = logging.getLogger(__name__)


class AgentPipeline:
    """Production 5-stage pipeline for customer support tweet inference."""

    def __init__(
        self,
        provider: LLMProvider,
        thread_repo: Optional[ThreadRepository] = None,
        classifier: Optional[IntentClassifier] = None,
        retriever: Optional[SemanticRetriever] = None,
        drafter: Optional[ReplyDrafter] = None,
        escalation: Optional[EscalationEngine] = None,
        safety: Optional[SafetyChecker] = None,
    ):
        self.provider = provider
        self.thread_repo = thread_repo
        self.classifier = classifier or IntentClassifier(provider)
        self.retriever = retriever or SemanticRetriever(thread_repo)
        self.drafter = drafter or ReplyDrafter(provider)
        self.escalation = escalation or EscalationEngine()
        self.safety = safety or SafetyChecker()

    async def run(
        self,
        customer_message: str,
        ticket_id: str = "transient-ticket",
        top_k: int = 3,
    ) -> InferenceResponse:
        """Execute the 5-stage inference flow with per-stage latency instrumentation."""
        overall_start = time.time()

        # ==========================================
        # STAGE 1: INTENT CLASSIFICATION
        # ==========================================
        t1 = time.time()
        intent_result = await self.classifier.classify(customer_message)
        classification_ms = int((time.time() - t1) * 1000)

        # ==========================================
        # STAGE 2: ESCALATION ENGINE (Pre-Draft Check)
        # ==========================================
        t2 = time.time()
        escalation_result = self.escalation.decide(
            customer_message=customer_message,
            intent=intent_result.intent,
            intent_confidence=intent_result.confidence,
            draft_confidence=0.8,
            has_similar_history=True,
        )
        escalation_ms = int((time.time() - t2) * 1000)

        # ==========================================
        # STAGE 3: SEMANTIC RAG RETRIEVAL
        # ==========================================
        t3 = time.time()
        retrieved_threads = await self.retriever.retrieve(
            query=customer_message,
            top_k=top_k,
            filter_dm=True,
            intent_filter=intent_result.intent,
        )
        retrieval_ms = int((time.time() - t3) * 1000)

        # ==========================================
        # STAGE 4: RESPONSE DRAFTING
        # ==========================================
        t4 = time.time()
        if escalation_result.decision == "escalate":
            # For escalated tickets, draft an empathetic holding response
            draft_result = DraftReplySchema(
                reply="We've received your request and an Apple specialist will assist you shortly to verify your details securely.",
                confidence=0.60,
                grounded_thread_ids=[],
                reasoning=f"Ticket escalated: {'; '.join(escalation_result.reasons)}",
            )
            p_tokens, c_tokens = 0, 0
        else:
            draft_result, _, p_tokens, c_tokens = await self.drafter.draft(
                customer_message=customer_message,
                intent=intent_result.intent,
                retrieved_threads=retrieved_threads,
            )
        drafting_ms = int((time.time() - t4) * 1000)

        # ==========================================
        # STAGE 5: SAFETY & POLICY CHECKER
        # ==========================================
        t5 = time.time()
        safety_check = self.safety.check(
            draft_text=draft_result.reply,
            original_message=customer_message,
            response_type="tweet",
        )
        safety_ms = int((time.time() - t5) * 1000)

        safety_schema = SafetyResultSchema(
            passed=safety_check.passed,
            flags=safety_check.flags,
        )

        total_latency = int((time.time() - overall_start) * 1000)

        return InferenceResponse(
            ticket_id=ticket_id,
            customer_message=customer_message,
            intent=intent_result,
            retrieved=retrieved_threads,
            draft=draft_result,
            escalation=escalation_result,
            safety=safety_schema,
            meta=InferenceMeta(
                model=self.provider.model_name,
                provider=self.provider.provider_name,
                prompt_version="v2",
                latency_ms=total_latency,
                tokens_prompt=p_tokens,
                tokens_completion=c_tokens,
                classification_ms=classification_ms,
                escalation_ms=escalation_ms,
                retrieval_ms=retrieval_ms,
                drafting_ms=drafting_ms,
                safety_ms=safety_ms,
            ),
        )

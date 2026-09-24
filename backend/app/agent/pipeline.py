"""
Agent Pipeline Orchestrator (v2.0).
Coordinates 5 stages sequentially:
  Stage 1: Intent Classifier (LLM structured)
  Stage 2: Escalation Engine (Deterministic policy & PII check)
  Stage 3: RAG Retriever (Knowledge base with helpfulness weighting)
  Stage 4: Response Drafter (LLM few-shot synthesis)
  Stage 5: Safety Checker (URL validation, promise blocking, tone)
"""

from __future__ import annotations
import logging
import time
from typing import Any, Optional
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
    RetrievedThreadItem,
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
        consensus_classifier: Optional[Any] = None,
        use_consensus: bool = False,
        web_search: Optional[Any] = None,
        use_web_search: bool = True,
    ):
        self.provider = provider
        self.thread_repo = thread_repo
        self.classifier = classifier or IntentClassifier(provider)
        self.retriever = retriever or SemanticRetriever(thread_repo)
        self.drafter = drafter or ReplyDrafter(provider)
        self.escalation = escalation or EscalationEngine()
        self.safety = safety or SafetyChecker()
        self.consensus_classifier = consensus_classifier
        self.use_consensus = use_consensus
        from app.services.web_search_service import WebSearchService
        self.web_search = web_search or WebSearchService()
        self.use_web_search = use_web_search

    async def run(
        self,
        customer_message: str,
        ticket_id: str = "transient-ticket",
        top_k: int = 3,
        conversation_history: Optional[str] = None,
        user_profile: Optional[str] = None,
        use_web_search: Optional[bool] = None,
    ) -> InferenceResponse:
        """Execute the 5-stage inference flow with per-stage latency instrumentation."""
        overall_start = time.time()

        # ==========================================
        # STAGE 1: INTENT CLASSIFICATION
        # ==========================================
        t1 = time.time()
        if self.use_consensus and self.consensus_classifier:
            intent_result = await self.consensus_classifier.classify_with_consensus(customer_message)
        else:
            intent_result = await self.classifier.classify(customer_message)
        classification_ms = int((time.time() - t1) * 1000)

        # ==========================================
        # STAGE 2: SEMANTIC RAG RETRIEVAL
        # ==========================================
        t2 = time.time()
        if intent_result.intent == "out_of_scope":
            retrieved_threads = []
        else:
            retrieved_threads = await self.retriever.retrieve(
                query=customer_message,
                top_k=top_k,
                filter_dm=True,
                intent_filter=intent_result.intent,
            )
        retrieval_ms = int((time.time() - t2) * 1000)

        max_rag_similarity = max([t.similarity for t in retrieved_threads], default=0.0)
        has_history = len(retrieved_threads) > 0

        # Web Search MCP Fallback: If RAG lacks match or similarity < 60%, ground via official Apple Support Web Search
        effective_web_search = self.use_web_search if use_web_search is None else use_web_search
        web_search_used = False
        web_search_ms = 0

        # Check if inquiry is truly off-topic (e.g. produce, groceries, personal relations)
        clean_lower = customer_message.lower()
        is_truly_non_apple = any(kw in clean_lower for kw in [
            "1 kg", "per kg", "produce", "fruit", "grocery", "my wife", "husband", "girlfriend",
            "boyfriend", "not talking to me", "pizza", "weather", "recipe", "who won the match"
        ])

        if effective_web_search and (not has_history or max_rag_similarity < 0.60) and not is_truly_non_apple:
            t_ws = time.time()
            try:
                web_results = await self.web_search.search_apple_support(
                    query=customer_message,
                    intent=intent_result.intent,
                    max_results=top_k,
                )
                web_search_ms = int((time.time() - t_ws) * 1000)
                if web_results:
                    web_search_used = True
                    for wr in web_results:
                        retrieved_threads.append(
                            RetrievedThreadItem(
                                thread_id=f"web-{abs(hash(wr.url)) % 100000}",
                                similarity=0.86,
                                customer_msg=wr.title,
                                brand_reply=f"{wr.snippet} Reference: {wr.url}",
                                intent_label=intent_result.intent,
                                source="web_search",
                                url=wr.url,
                            )
                        )
                    max_rag_similarity = max([t.similarity for t in retrieved_threads], default=0.0)
                    has_history = len(retrieved_threads) > 0
            except Exception as e:
                logger.warning(f"Web search MCP fallback note: {e}")

        # ==========================================
        # STAGE 3: ESCALATION ENGINE (Grounding & Safety Check)
        # ==========================================
        t3 = time.time()
        escalation_result = self.escalation.decide(
            customer_message=customer_message,
            intent=intent_result.intent,
            intent_confidence=intent_result.confidence,
            draft_confidence=0.8,
            has_similar_history=has_history,
            rag_similarity=max_rag_similarity,
        )
        escalation_ms = int((time.time() - t3) * 1000)

        # ==========================================
        # STAGE 4: RESPONSE DRAFTING
        # ==========================================
        t4 = time.time()
        # If escalated due to out-of-scope or low RAG grounding, generate polite ecosystem deflection
        # But if web search retrieved official groundings, allow drafter to synthesize grounded answer
        has_web_grounding = any(t.source == "web_search" or t.thread_id.startswith("web-") for t in retrieved_threads)
        is_grounding_or_scope_escalation = (intent_result.intent == "out_of_scope" or not has_history or (max_rag_similarity < 0.60)) and not has_web_grounding
        
        has_critical_security = any("pii" in r.lower() or "legal" in r.lower() or "security" in r.lower() for r in escalation_result.reasons)
        if escalation_result.decision == "escalate" and has_critical_security and not is_grounding_or_scope_escalation:
            # For security, PII, or legal escalations, draft an empathetic holding response
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
                conversation_history=conversation_history,
                user_profile=user_profile,
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
                web_search_used=web_search_used,
                web_search_ms=web_search_ms,
            ),
        )

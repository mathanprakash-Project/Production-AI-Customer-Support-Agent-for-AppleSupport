"""Streaming inference service that wraps the AgentPipeline with SSE event emission."""
import logging
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.classifier import IntentClassifier
from app.agent.drafter import ReplyDrafter
from app.agent.escalation import EscalationEngine
from app.agent.retriever import SemanticRetriever
from app.agent.safety_checker import SafetyChecker
from app.llm.factory import get_llm_provider
from app.models.draft import Draft
from app.repositories.draft_repo import DraftRepository
from app.repositories.thread_repo import ThreadRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.inference import (
    DraftReplySchema, EscalationDecision, InferenceMeta, SafetyResultSchema,
)

logger = logging.getLogger(__name__)

STAGE_NAMES = [
    "Intent Classification",
    "Knowledge Retrieval",
    "Escalation Analysis",
    "Response Drafting",
    "Safety Validation",
]

class StreamingInferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.draft_repo = DraftRepository(db)
        self.thread_repo = ThreadRepository(db)
        self.provider = get_llm_provider()
        self.classifier = IntentClassifier(self.provider)
        self.retriever = SemanticRetriever(self.thread_repo, db=db)
        self.drafter = ReplyDrafter(self.provider)
        self.escalation = EscalationEngine()
        self.safety = SafetyChecker()
        from app.services.web_search_service import WebSearchService
        self.web_search = WebSearchService()

    async def stream_pipeline(self, ticket_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute pipeline with streaming events for each stage."""
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")
        
        customer_message = ticket.customer_text
        overall_start = time.time()
        
        # Stage 1: Classification
        yield {"event": "stage_start", "data": {"stage": STAGE_NAMES[0], "index": 1, "total": 5}}
        t1 = time.time()
        intent_result = await self.classifier.classify(customer_message)
        classification_ms = int((time.time() - t1) * 1000)
        yield {"event": "stage_complete", "data": {
            "stage": STAGE_NAMES[0], "index": 1,
            "result": {"intent": intent_result.intent, "confidence": intent_result.confidence},
            "duration_ms": classification_ms,
        }}
        
        # Stage 2: Retrieval  
        yield {"event": "stage_start", "data": {"stage": STAGE_NAMES[1], "index": 2, "total": 5}}
        t2 = time.time()
        if intent_result.intent == "out_of_scope":
            retrieved_threads = []
        else:
            retrieved_threads = await self.retriever.retrieve(query=customer_message, top_k=3, filter_dm=True, intent_filter=intent_result.intent)
        retrieval_ms = int((time.time() - t2) * 1000)
        yield {"event": "stage_complete", "data": {
            "stage": STAGE_NAMES[1], "index": 2,
            "result": {"matches_found": len(retrieved_threads)},
            "duration_ms": retrieval_ms,
        }}
        
        max_rag_similarity = max([t.similarity for t in retrieved_threads], default=0.0)
        has_history = len(retrieved_threads) > 0
        
        # Check if inquiry is off-topic (e.g. produce, groceries, personal relations)
        clean_lower = customer_message.lower()
        is_truly_non_apple = any(kw in clean_lower for kw in [
            "1 kg", "per kg", "produce", "fruit", "grocery", "my wife", "husband", "girlfriend",
            "boyfriend", "not talking to me", "pizza", "weather", "recipe", "who won the match"
        ])
        
        # Web Search MCP Fallback: If RAG lacks match or similarity < 60%, query official Apple Support Web Search
        if (not has_history or max_rag_similarity < 0.60) and not is_truly_non_apple:
            yield {"event": "web_search_start", "data": {"query": customer_message, "intent": intent_result.intent}}
            try:
                web_results = await self.web_search.search_apple_support(
                    query=customer_message,
                    intent=intent_result.intent,
                    max_results=3,
                )
                if web_results:
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
                    yield {
                        "event": "web_search_complete",
                        "data": {"results_found": len(web_results), "top_url": web_results[0].url},
                    }
            except Exception as e:
                logger.warning(f"Web search streaming fallback failed: {e}")
        
        # Stage 3: Escalation
        yield {"event": "stage_start", "data": {"stage": STAGE_NAMES[2], "index": 3, "total": 5}}
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
        yield {"event": "stage_complete", "data": {
            "stage": STAGE_NAMES[2], "index": 3,
            "result": {"decision": escalation_result.decision, "risk_score": escalation_result.risk_score},
            "duration_ms": escalation_ms,
        }}
        
        # Stage 4: Drafting (with token streaming simulation)
        yield {"event": "stage_start", "data": {"stage": STAGE_NAMES[3], "index": 4, "total": 5}}
        t4 = time.time()
        
        has_web_grounding = any(t.source == "web_search" or t.thread_id.startswith("web-") for t in retrieved_threads)
        is_grounding_or_scope_escalation = (intent_result.intent == "out_of_scope" or not has_history or (max_rag_similarity < 0.60)) and not has_web_grounding
        has_critical_security = any("pii" in r.lower() or "legal" in r.lower() or "security" in r.lower() for r in escalation_result.reasons)
        if escalation_result.decision == "escalate" and has_critical_security and not is_grounding_or_scope_escalation:
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
        
        # Simulate token streaming for the draft text
        words = draft_result.reply.split()
        for i, word in enumerate(words):
            yield {"event": "token", "data": {"content": word + (" " if i < len(words) - 1 else "")}}
            # No sleep needed - SSE will flush automatically
        
        drafting_ms = int((time.time() - t4) * 1000)
        yield {"event": "draft_complete", "data": {
            "reply": draft_result.reply,
            "confidence": draft_result.confidence,
            "reasoning": draft_result.reasoning or "",
            "grounded_thread_ids": draft_result.grounded_thread_ids,
        }}
        yield {"event": "stage_complete", "data": {
            "stage": STAGE_NAMES[3], "index": 4,
            "result": {"reply_length": len(draft_result.reply), "confidence": draft_result.confidence},
            "duration_ms": drafting_ms,
        }}
        
        # Stage 5: Safety
        yield {"event": "stage_start", "data": {"stage": STAGE_NAMES[4], "index": 5, "total": 5}}
        t5 = time.time()
        safety_check = self.safety.check(draft_text=draft_result.reply, original_message=customer_message, response_type="tweet")
        safety_ms = int((time.time() - t5) * 1000)
        yield {"event": "safety_result", "data": {"passed": safety_check.passed, "flags": safety_check.flags}}
        yield {"event": "stage_complete", "data": {
            "stage": STAGE_NAMES[4], "index": 5,
            "result": {"passed": safety_check.passed, "flag_count": len(safety_check.flags)},
            "duration_ms": safety_ms,
        }}
        
        # Persist draft
        total_latency = int((time.time() - overall_start) * 1000)
        draft_entity = Draft(
            ticket_id=ticket.id,
            intent_label=intent_result.intent,
            intent_confidence=intent_result.confidence,
            intent_alternatives=[a.model_dump() for a in intent_result.alternatives],
            reply_text=draft_result.reply,
            reply_confidence=draft_result.confidence,
            retrieved_thread_ids=draft_result.grounded_thread_ids,
            escalation_decision=escalation_result.decision,
            escalation_reasons=escalation_result.reasons,
            risk_score=escalation_result.risk_score,
            safety_passed=safety_check.passed,
            safety_flags=safety_check.flags,
            model_name=self.provider.model_name,
            provider=self.provider.provider_name,
            prompt_version="v2",
            latency_ms=total_latency,
            tokens_prompt=p_tokens,
            tokens_completion=c_tokens,
        )
        saved_draft = await self.draft_repo.create(draft_entity)
        
        # Update ticket
        is_esc = (escalation_result.decision == "escalate")
        ticket.intent = intent_result.intent
        ticket.confidence = intent_result.confidence
        ticket.is_escalated = is_esc
        ticket.escalation_reason = "; ".join(escalation_result.reasons) if escalation_result.reasons else None
        ticket.total_pipeline_time_ms = total_latency
        ticket.status = "escalated" if is_esc else "drafted"
        
        if is_esc:
            from app.models.escalation_log import EscalationLog
            esc_log = EscalationLog(
                ticket_id=ticket.id,
                escalation_reasons=escalation_result.reasons,
                risk_score=escalation_result.risk_score,
                escalated_by="system",
                notes="Automated rule trigger",
            )
            self.db.add(esc_log)
        
        await self.db.commit()
        
        yield {"event": "done", "data": {
            "ticket_id": ticket_id,
            "draft_id": saved_draft.id,
            "total_ms": total_latency,
            "status": ticket.status,
        }}

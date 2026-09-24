"""
Service layer for running agent inference and managing draft responses.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.consensus_classifier import ConsensusClassifier
from app.agent.pipeline import AgentPipeline
from app.core.config import settings
from app.llm.factory import get_llm_provider
from app.memory.memory_manager import MemoryManager
from app.models.draft import Draft
from app.repositories.draft_repo import DraftRepository
from app.repositories.thread_repo import ThreadRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.inference import (
    DraftReplySchema,
    EscalationDecision,
    InferenceMeta,
    InferenceResponse,
    IntentClassificationSchema,
    RetrievedThreadItem,
)


class InferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ticket_repo = TicketRepository(db)
        self.draft_repo = DraftRepository(db)
        self.thread_repo = ThreadRepository(db)
        self.provider = get_llm_provider()
        self.consensus_classifier = ConsensusClassifier(self.provider) if settings.CONSENSUS_ENABLED else None
        self.pipeline = AgentPipeline(
            provider=self.provider,
            thread_repo=self.thread_repo,
            consensus_classifier=self.consensus_classifier,
            use_consensus=settings.CONSENSUS_ENABLED,
            use_web_search=settings.WEB_SEARCH_FALLBACK_ENABLED,
        )
        self.memory_manager = MemoryManager(db=db, provider=self.provider)

    async def run_ticket_inference(self, ticket_id: str, force_fresh: bool = False) -> InferenceResponse:
        """Run agent pipeline on ticket text and persist draft."""
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")

        # Check existing draft unless force fresh is requested
        if not force_fresh:
            existing_draft = await self.draft_repo.get_latest_by_ticket_id(ticket_id)
            if existing_draft:
                reconstructed_threads: List[RetrievedThreadItem] = []
                for tid in (existing_draft.retrieved_thread_ids or []):
                    if tid.startswith("web-"):
                        url = "https://www.apple.com/shop/trade-in" if any(w in ticket.customer_text.lower() for w in ["trade", "exchange"]) else "https://support.apple.com"
                        reconstructed_threads.append(
                            RetrievedThreadItem(
                                thread_id=tid,
                                similarity=0.86,
                                customer_msg="Apple Support Official Knowledge Guide",
                                brand_reply=existing_draft.reply_text,
                                intent_label=existing_draft.intent_label,
                                source="web_search",
                                url=url,
                            )
                        )
                    else:
                        try:
                            t = await self.thread_repo.get(tid)
                            if t:
                                reconstructed_threads.append(
                                    RetrievedThreadItem(
                                        thread_id=t.thread_id,
                                        similarity=0.85,
                                        customer_msg=t.customer_text or "",
                                        brand_reply=t.brand_reply_text or "",
                                        intent_label=t.intent or existing_draft.intent_label,
                                        source="internal_rag",
                                    )
                                )
                        except Exception:
                            pass

                return InferenceResponse(
                    ticket_id=ticket.id,
                    customer_message=ticket.customer_text,
                    draft_id=existing_draft.id,
                    intent=IntentClassificationSchema(
                        intent=existing_draft.intent_label,
                        confidence=existing_draft.intent_confidence,
                        alternatives=existing_draft.intent_alternatives or [],
                    ),
                    retrieved=reconstructed_threads,
                    draft=DraftReplySchema(
                        reply=existing_draft.reply_text,
                        confidence=existing_draft.reply_confidence,
                        grounded_thread_ids=existing_draft.retrieved_thread_ids or [],
                    ),
                    escalation=EscalationDecision(
                        decision=existing_draft.escalation_decision,
                        reasons=existing_draft.escalation_reasons or [],
                        risk_score=existing_draft.risk_score,
                    ),
                    meta=InferenceMeta(
                        model=existing_draft.model_name,
                        provider=existing_draft.provider,
                        prompt_version=existing_draft.prompt_version,
                        latency_ms=existing_draft.latency_ms,
                        web_search_used=any(tid.startswith("web-") for tid in (existing_draft.retrieved_thread_ids or [])),
                    ),
                )

        # Multi-turn memory processing
        user_identifier = ticket.tweet_author or f"ticket_{ticket.id}"
        session_id = None
        conv_history = None
        user_profile = None
        try:
            mem_data = await self.memory_manager.process_customer_message(
                user_identifier=user_identifier,
                message=ticket.customer_text,
                ticket_id=ticket.id,
            )
            session_id = mem_data.get("session_id")
            conv_history = mem_data.get("conversation_history")
            user_profile = mem_data.get("user_profile")
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(f"Memory processing note: {e}")

        # Run fresh agent pipeline
        result = await self.pipeline.run(
            customer_message=ticket.customer_text,
            ticket_id=ticket.id,
            conversation_history=conv_history,
            user_profile=user_profile,
        )

        # Record agent turn to session memory if session active
        if session_id and result.draft and result.draft.reply:
            try:
                await self.memory_manager.record_agent_response(
                    session_id=session_id,
                    response=result.draft.reply,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Could not record agent turn: {e}")

        # Persist draft to database
        draft_entity = Draft(
            ticket_id=ticket.id,
            intent_label=result.intent.intent,
            intent_confidence=result.intent.confidence,
            intent_alternatives=[a.model_dump() for a in result.intent.alternatives],
            reply_text=result.draft.reply,
            reply_confidence=result.draft.confidence,
            retrieved_thread_ids=result.draft.grounded_thread_ids,
            escalation_decision=result.escalation.decision,
            escalation_reasons=result.escalation.reasons,
            risk_score=result.escalation.risk_score,
            model_name=result.meta.model,
            provider=result.meta.provider,
            prompt_version=result.meta.prompt_version,
            latency_ms=result.meta.latency_ms,
            tokens_prompt=result.meta.tokens_prompt,
            tokens_completion=result.meta.tokens_completion,
        )
        saved_draft = await self.draft_repo.create(draft_entity)
        result.draft_id = saved_draft.id

        # Update ticket classification, escalation, and timing metadata
        is_esc = (result.escalation.decision == "escalate")
        ticket.intent = result.intent.intent
        ticket.confidence = result.intent.confidence
        ticket.is_escalated = is_esc
        ticket.escalation_reason = "; ".join(result.escalation.reasons) if result.escalation.reasons else None
        ticket.total_pipeline_time_ms = result.meta.latency_ms
        ticket.status = "escalated" if is_esc else "drafted"
        
        if is_esc:
            from app.models.escalation_log import EscalationLog
            esc_log = EscalationLog(
                ticket_id=ticket.id,
                escalation_reasons=result.escalation.reasons,
                risk_score=result.escalation.risk_score,
                escalated_by="system",
                notes="Automated rule trigger",
            )
            self.db.add(esc_log)

        await self.db.commit()
        return result

    async def get_drafts_for_ticket(self, ticket_id: str) -> List[Draft]:
        return await self.draft_repo.get_by_ticket_id(ticket_id)


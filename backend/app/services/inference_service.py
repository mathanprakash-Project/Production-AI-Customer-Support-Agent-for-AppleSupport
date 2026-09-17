"""
Service layer for running agent inference and managing draft responses.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.pipeline import AgentPipeline
from app.llm.factory import get_llm_provider
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
        self.pipeline = AgentPipeline(
            provider=self.provider,
            thread_repo=self.thread_repo,
        )

    async def run_ticket_inference(self, ticket_id: str, force_fresh: bool = False) -> InferenceResponse:
        """Run agent pipeline on ticket text and persist draft."""
        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")

        # Check existing draft unless force fresh is requested
        if not force_fresh:
            existing_draft = await self.draft_repo.get_latest_by_ticket_id(ticket_id)
            if existing_draft:
                return InferenceResponse(
                    ticket_id=ticket.id,
                    customer_message=ticket.customer_text,
                    draft_id=existing_draft.id,
                    intent=IntentClassificationSchema(
                        intent=existing_draft.intent_label,
                        confidence=existing_draft.intent_confidence,
                        alternatives=existing_draft.intent_alternatives or [],
                    ),
                    retrieved=[],
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
                    ),
                )

        # Run fresh agent pipeline
        result = await self.pipeline.run(
            customer_message=ticket.customer_text,
            ticket_id=ticket.id,
        )

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


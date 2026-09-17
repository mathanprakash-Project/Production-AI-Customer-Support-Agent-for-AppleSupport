"""
Service layer for human feedback recording, edit-distance calculation,
and feeding approved solutions back into the self-updating Knowledge Base.
"""

from difflib import SequenceMatcher
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import utc_now
from app.models.escalation_log import EscalationLog
from app.models.feedback import Feedback
from app.repositories.draft_repo import DraftRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.ticket import FeedbackCreate
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class FeedbackService:
    """Processes agent actions (approve/edit/reject/escalate) and powers the self-improving loop."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.draft_repo = DraftRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.knowledge_service = KnowledgeService(db)

    async def record_feedback(
        self,
        ticket_id: str,
        data: FeedbackCreate,
        user_id: Optional[str] = None,
    ) -> Feedback:
        """
        Record human reviewer action on the latest draft, calculate edit distance,
        and add approved resolutions to the knowledge base.
        """
        draft = await self.draft_repo.get_latest_by_ticket_id(ticket_id)
        if not draft:
            raise ValueError(f"No active draft found for ticket '{ticket_id}'.")

        ticket = await self.ticket_repo.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")

        # 1. Determine final response text & calculate edit distance
        edit_distance = 0.0
        final_text = draft.reply_text

        if data.action == "edit":
            candidate_text = data.final_response_text or data.edited_text or ""
            if candidate_text:
                final_text = candidate_text
                ratio = SequenceMatcher(None, draft.reply_text, final_text).ratio()
                edit_distance = round(1.0 - ratio, 3)
        elif data.action == "reject":
            final_text = data.final_response_text or data.edited_text or ""
            edit_distance = 1.0
        elif data.action == "approve":
            final_text = draft.reply_text
            edit_distance = 0.0

        # 2. Persist feedback entry
        feedback = Feedback(
            draft_id=draft.id,
            user_id=user_id,
            action=data.action,
            edited_text=data.edited_text or (final_text if data.action == "edit" else None),
            final_response_text=final_text if data.action in ["approve", "edit"] else None,
            edit_distance_ratio=edit_distance,
            review_time_seconds=data.review_time_seconds,
            notes=data.notes,
        )
        self.db.add(feedback)

        # 3. Update ticket state and resolution timestamp
        if data.action in ["approve", "edit"]:
            ticket.status = "resolved"
            ticket.resolved_at = utc_now()
        elif data.action == "escalate":
            ticket.status = "escalated"
            ticket.is_escalated = True
            ticket.escalation_reason = data.notes or "Manually escalated by support agent."
            # Create escalation log
            esc_log = EscalationLog(
                ticket_id=ticket.id,
                escalation_reasons=["agent_manual_escalation"],
                risk_score=1.0,
                escalated_by="agent",
                notes=data.notes,
            )
            self.db.add(esc_log)
        elif data.action == "reject":
            ticket.status = "open"

        # 4. Self-Improving Knowledge Base: feed approved responses back into RAG
        if data.action in ["approve", "edit"]:
            try:
                await self.knowledge_service.add_from_approved_feedback(ticket, final_text)
                feedback.added_to_knowledge_base = True
            except Exception as e:
                logger.error(f"Failed to auto-index approved resolution into knowledge base: {e}")

        # 5. Update helpfulness of source retrieved threads
        if draft.retrieved_thread_ids:
            try:
                was_helpful = (data.action == "approve")
                await self.knowledge_service.update_helpfulness(
                    draft.retrieved_thread_ids, was_helpful=was_helpful
                )
            except Exception as e:
                logger.warning(f"Could not update helpfulness weights: {e}")

        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback
